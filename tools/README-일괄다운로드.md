# 학교 목록 최신화 · 교육과정편성표 일괄 다운로드

tools 폴더에는 두 가지 도구가 있습니다.

| 도구 | 하는 일 |
|---|---|
| `sync_school_list.py` | 교육청 「학교 현황」 엑셀(고등학교 시트)로 **학교 목록과 구·군**을 최신화 |
| `fetch_ice_curriculum.py` | 인천 교육과정편성표 작성시스템(ice-curriculum.kr)에서 **학교별 편성표 엑셀**을 내려받기 |

## 준비 (한 번)
1. 파이썬 3 설치 (python.org)
2. 명령 프롬프트에서:  `pip install openpyxl requests beautifulsoup4`

## 1. 학교 목록·구·군 최신화 (매년 4월 학교 현황이 나오면)
```
python tools/sync_school_list.py "2026_4_1_자_학교_현황(최종).xlsx"
```
- `tools/districts.csv` 를 공식 현황으로 다시 만듭니다 (전체 고등학교, 계열·설립·남녀 포함).
- `schools.json` 의 모든 학교를 공식 구·군으로 옮깁니다. 기존 학교 id·파일은 그대로입니다.
- 편성표 엑셀이 없는 학교도 목록에 넣고 사이트에 **"편성표 준비 중"** 으로 표시합니다.
- `tools/missing_curriculum.csv` 에 편성표가 아직 없는 학교를 적어 둡니다.
- 구·군 기준은 기본이 **개편 후 행정구역(2026.7.1. 시행: 제물포구·영종구·서해구·검단구)** 입니다.
  개편 전 이름(중구·동구·서구)으로 쓰려면 `--district-col 구군별`
- 목록에 넣는 계열은 기본 `일반,자율형,특목` 입니다. 특성화고까지 넣으려면 `--include 일반,자율형,특목,특성화`

## 2. 편성표 엑셀 내려받기
```
python tools/fetch_ice_curriculum.py --limit 2                 # 먼저 2개만 시험
python tools/fetch_ice_curriculum.py --only 작전여자,도림,연수   # 준비 중인 학교만
python tools/fetch_ice_curriculum.py                           # 전체 (약 3~4분)
```
- 받은 학교는 `schools/<id>.xlsx` 로 저장되고, schools.json 에서 **"준비 중"이 자동으로 풀립니다.**
- 구·군은 `tools/districts.csv` 를 따릅니다 (잘못된 구·군에 있던 학교도 옮겨짐).
- `--year 2025` 다른 학년도 · `--delay 2` 요청 간격(초, 기본 1.5초 — 줄이지 마세요)
- 결과: `tools/ice_download_log.csv` (실패에 "엑셀이 아닌 응답(로그인 필요?)"가 뜨면 다운로드에 로그인이 필요한 상태)

## 올리기
`schools/` 폴더, `schools.json`, `tools/` 폴더를 깃허브에 올리면 사이트 학교 선택 목록에 바로 반영됩니다.
(사이트 `index.html` 안에도 같은 목록이 예비용으로 들어 있어, schools.json을 못 읽을 때도 목록이 보입니다.
 목록을 크게 바꿨다면 예비 목록도 맞춰 두는 것이 좋습니다.)
