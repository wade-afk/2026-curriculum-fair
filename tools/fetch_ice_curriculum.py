# -*- coding: utf-8 -*-
"""
인천 교육과정편성표 작성시스템(ice-curriculum.kr)에서
"재학생의 3개년 교육과정 편성표" 엑셀을 학교별로 한 번에 내려받고 schools.json 초안을 만듭니다.

사용법 (저장소 루트에서):
    pip install requests beautifulsoup4
    python tools/fetch_ice_curriculum.py                 # 2026학년도, 전체 학교
    python tools/fetch_ice_curriculum.py --year 2026 --limit 3   # 3개만 시험
    python tools/fetch_ice_curriculum.py --only 효성,신송         # 학교명에 포함된 것만

결과:
    schools/<id>.xlsx            학교별 엑셀 (학교당 최신 1건)
    schools.json                 기존 항목은 그대로 두고, 새 학교를 추가 (지역=인천, 구·군은 tools/districts.csv 참고)
    tools/ice_download_log.csv   내려받은 목록 (학교명, id, 게시번호, 수정일, 파일)

주의:
  - 교육청 서버에 부담을 주지 않도록 요청 사이에 쉬어 갑니다(--delay, 기본 1.5초). 한 번 받아 저장소에 올려 쓰세요.
  - 구·군은 이 사이트에 없습니다. tools/districts.csv(학교명,구·군)에 적어 두면 반영되고, 없으면 "미분류"로 들어갑니다.
"""
import argparse, csv, json, os, re, sys, time
from urllib.parse import urljoin

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:          # sync_school_list.py 가 id 규칙만 가져다 쓸 때는 없어도 됨
    requests = BeautifulSoup = None

BASE = "https://ice-curriculum.kr"
LIST = BASE + "/hs/school/curriculum/list"
HEADERS = {"User-Agent": "Mozilla/5.0 (curriculum-fair downloader; contact: site operator)"}

# ---------------- 한글 → 로마자 (id 생성용, 국어의 로마자 표기법 단순판) ----------------
CHO = ["g","kk","n","d","tt","r","m","b","pp","s","ss","","j","jj","ch","k","t","p","h"]
JUNG = ["a","ae","ya","yae","eo","e","yeo","ye","o","wa","wae","oe","yo","u","wo","we","wi","yu","eu","ui","i"]
JONG = ["","k","k","k","n","n","n","t","l","k","m","p","l","l","p","l","m","p","p","t","t","ng","t","t","k","t","p","t"]
def romanize(s):
    out = []
    for ch in s:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3:
            i = o - 0xAC00
            out.append(CHO[i // 588] + JUNG[(i % 588) // 28] + JONG[i % 28])
        elif ch.isascii() and ch.isalnum():
            out.append(ch.lower())
    return "".join(out)

def make_id(name, used):
    core = re.sub(r"^인천", "", name)
    core = re.sub(r"고등학교$", "", core)          # 예: 인천효성고등학교 → 효성, 명신여자고등학교 → 명신여자
    base = re.sub(r"[^a-z0-9]", "", romanize(core)) or "school"
    cand, n = base, 2
    while cand in used:
        cand = f"{base}{n}"; n += 1
    used.add(cand)
    return cand

def short_name(name):
    s = re.sub(r"^인천", "", name)
    s = re.sub(r"고등학교$", "고", s)
    return s

# ---------------- 목록 수집 ----------------
def fetch_list(session, year, delay):
    rows, page = [], 0
    while True:
        params = {"fSelectionGroup": "", "fYear": year, "fSchoolName": "", "page": page}
        r = session.get(LIST, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        found = 0
        for tr in soup.select("table tr"):
            a = tr.select_one('a[href*="/school/curriculum/excel/"]')
            if not a:
                continue
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            m = re.search(r"/excel/(\d+)", a["href"])
            if not m or len(tds) < 5:
                continue
            post_id = m.group(1)
            # 열: 입학년도 | 학교 | 학과 | 제목 | 첨부 | 수정일
            rows.append({
                "year": tds[0], "school": tds[1], "dept": tds[2] if len(tds) > 2 else "",
                "title": tds[3] if len(tds) > 3 else "", "updated": tds[-1], "post_id": post_id,
                "excel_url": urljoin(BASE, a["href"]),
            })
            found += 1
        print(f"  목록 {page+1}쪽: {found}건")
        if found == 0:
            break
        # 다음 쪽이 있는지: 'page=N+1' 링크가 있으면 계속
        if not soup.select_one(f'a[href*="page={page+1}"]'):
            break
        page += 1
        time.sleep(delay)
    return rows

def pick_latest_per_school(rows, year):
    best = {}
    for r in rows:
        if year and not r["title"].startswith(f"{year}학년도"):
            continue
        key = r["school"].strip()
        # 일반 학과를 우선, 그다음 최신 수정일
        rank = (1 if r["dept"].strip() in ("일반", "") else 0, r["updated"])
        if key not in best or rank > best[key]["_rank"]:
            r["_rank"] = rank
            best[key] = r
    return best

# ---------------- 다운로드 ----------------
def download(session, url, path, delay):
    r = session.get(url, headers=HEADERS, timeout=60)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "")
    if not r.content.startswith(b"PK"):
        raise RuntimeError(f"엑셀이 아닌 응답(로그인 필요?) Content-Type={ctype}")
    with open(path, "wb") as f:
        f.write(r.content)
    time.sleep(delay)
    return len(r.content)

# ---------------- schools.json 갱신 ----------------
def load_districts(path):
    d = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8-sig") as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0].strip() and not row[0].startswith("#"):
                    d[row[0].strip()] = row[1].strip()
    return d

def update_schools_json(path, new_schools, districts, version):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            j = json.load(f)
    else:
        j = {"version": "", "operatorUrl": "", "note": "", "regions": [{"name": "인천", "districts": []}]}
    region = next((r for r in j["regions"] if r["name"] == "인천"), None)
    if not region:
        region = {"name": "인천", "districts": []}; j["regions"].append(region)
    existing_names = {s["name"]: s for r in j["regions"] for d in r["districts"] for s in d["schools"]}
    existing_ids = {s["id"] for r in j["regions"] for d in r["districts"] for s in d["schools"]}
    added, updated = 0, 0
    for s in new_schools:
        if s["name"] in existing_names:           # 이미 있는 학교: 파일 경로·수정일 갱신
            existing_names[s["name"]]["file"] = s["file"]
            existing_names[s["name"]]["updated"] = s["updated"]
            existing_names[s["name"]].pop("pending", None)   # 편성표를 받았으니 '준비 중' 해제
            updated += 1
            # districts.csv의 구·군과 다르면(미분류 포함) 그쪽으로 이동
            dist_name = districts.get(s["name"])
            if dist_name:
                for d in region["districts"]:
                    if d["name"] != dist_name and existing_names[s["name"]] in d["schools"]:
                        d["schools"].remove(existing_names[s["name"]])
                        tgt = next((x for x in region["districts"] if x["name"] == dist_name), None)
                        if not tgt:
                            tgt = {"name": dist_name, "schools": []}; region["districts"].append(tgt)
                        tgt["schools"].append(existing_names[s["name"]])
            continue
        dist_name = districts.get(s["name"], "미분류")
        dist = next((d for d in region["districts"] if d["name"] == dist_name), None)
        if not dist:
            dist = {"name": dist_name, "schools": []}; region["districts"].append(dist)
        dist["schools"].append({"id": s["id"], "name": s["name"], "short": s["short"], "file": s["file"], "updated": s["updated"]})
        added += 1
    # 구·군 이름순, 학교 이름순 정렬 ('미분류'는 맨 뒤)
    region["districts"] = [d for d in region["districts"] if d["schools"]]
    region["districts"].sort(key=lambda d: (d["name"] == "미분류", d["name"]))
    for d in region["districts"]:
        d["schools"].sort(key=lambda s: s["name"])
    j["version"] = version
    with open(path, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, indent=2)
    return added, updated, existing_ids

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", default="2026")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--limit", type=int, default=0, help="시험용: 앞에서 N개 학교만")
    ap.add_argument("--only", default="", help="학교명에 이 글자가 포함된 것만 (쉼표로 여러 개)")
    ap.add_argument("--out", default="schools")
    ap.add_argument("--json", default="schools.json")
    ap.add_argument("--districts", default="tools/districts.csv")
    ap.add_argument("--no-download", action="store_true", help="목록만 만들고 파일은 받지 않음")
    a = ap.parse_args()
    if requests is None:
        sys.exit("먼저 실행:  pip install requests beautifulsoup4")

    os.makedirs(a.out, exist_ok=True)
    s = requests.Session()
    print(f"▶ {a.year}학년도 목록 수집 중…")
    rows = fetch_list(s, a.year, a.delay)
    best = pick_latest_per_school(rows, a.year)
    names = sorted(best)
    if a.only:
        keys = [k.strip() for k in a.only.split(",") if k.strip()]
        names = [n for n in names if any(k in n for k in keys)]
    if a.limit:
        names = names[:a.limit]
    print(f"▶ 대상 학교 {len(names)}개 (전체 게시물 {len(rows)}건)")

    # 기존 id 재사용
    used = set()
    existing = {}
    if os.path.exists(a.json):
        with open(a.json, encoding="utf-8") as f:
            for r in json.load(f)["regions"]:
                for d in r["districts"]:
                    for sc in d["schools"]:
                        existing[sc["name"]] = sc["id"]; used.add(sc["id"])

    log_path = os.path.join("tools", "ice_download_log.csv")
    os.makedirs("tools", exist_ok=True)
    results, failed = [], []
    with open(log_path, "w", encoding="utf-8-sig", newline="") as lf:
        w = csv.writer(lf); w.writerow(["학교명", "id", "게시번호", "학과", "수정일", "파일", "크기(bytes)", "결과"])
        for i, name in enumerate(names, 1):
            r = best[name]
            sid = existing.get(name) or make_id(name, used)
            fname = f"{sid}.xlsx"; path = os.path.join(a.out, fname)
            status, size = "skip", ""
            if not a.no_download:
                try:
                    size = download(s, r["excel_url"], path, a.delay)
                    status = "ok"
                except Exception as e:
                    status = f"실패: {e}"; failed.append((name, str(e)))
            print(f"  [{i}/{len(names)}] {name} → {fname} ({r['updated']}) {status}")
            w.writerow([name, sid, r["post_id"], r["dept"], r["updated"], f"{a.out}/{fname}", size, status])
            if status in ("ok", "skip"):
                results.append({"id": sid, "name": name, "short": short_name(name), "file": f"{a.out}/{fname}", "updated": r["updated"]})

    districts = load_districts(a.districts)
    version = time.strftime("%Y-%m-%d") + "-ice"
    added, updated, _ = update_schools_json(a.json, results, districts, version)
    unknown = [r["name"] for r in results if r["name"] not in districts]

    print("\n▶ 완료")
    print(f"   내려받음 {len(results) - len([1 for r in results if a.no_download])}개, 실패 {len(failed)}개")
    print(f"   schools.json: 새 학교 {added}개 추가, 기존 {updated}개 갱신 (version={version})")
    if unknown:
        print(f"   구·군 미분류 {len(unknown)}개 → {a.districts} 에 '학교명,구·군' 으로 적고 다시 실행하면 반영됩니다.")
        print("   예) " + ", ".join(unknown[:8]) + (" …" if len(unknown) > 8 else ""))
    if failed:
        print("   실패 목록:"); [print(f"   - {n}: {e}") for n, e in failed]
    print(f"   기록: {log_path}")

if __name__ == "__main__":
    main()
