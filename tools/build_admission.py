"""Build crawlable admission pages: python tools/build_admission.py (stdlib only)."""
import html, json, re
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://wade-afk.github.io/2026-curriculum-fair/'
SOURCE = 'https://www2.yonsei.ac.kr/entrance/plan/2028_guide.pdf'
E = html.escape
data = json.loads((ROOT / 'admission/2028/yonsei/data.json').read_text(encoding='utf-8'))

# Keep the legacy tool's projection in sync with the reviewed source data.
# Alternatives and course-count rules stay in notes, never a mandatory subject list.
source_html = (ROOT/'index.html').read_text(encoding='utf-8')
match = re.search(r'const UNIV_DATA = (.*);', source_html)
universities = json.loads(match[1])
projection = []
for row in data['rows']:
    science = row['science']
    rec = ', '.join(value for value in [row['math'] if row['math'] != '미제시' else '', science if science not in ['미제시','자율선택'] and '택 1' not in science and '또는' not in science else ''] if value)
    note = '연세대 서울캠퍼스 · 2026.4 공식 가이드라인. 과학 일반선택: '+science+' / 과학 진로선택: '+row['advanced']+'. 권장 사항이며 도구의 과목 매칭은 대학 평가 판정이 아닙니다.'
    projection.append([row['college'],row['name'],'',rec,note])
yonsei = next((u for u in universities if u['univ']=='연세대'),None)
if yonsei is None:
    yonsei = dict(region='서울',univ='연세대')
    universities.append(yonsei)
yonsei['rows'] = projection
(ROOT/'index.html').write_text(source_html[:match.start(1)] + json.dumps(universities,ensure_ascii=False,separators=(',',':')) + source_html[match.end(1):],encoding='utf-8')

def page(title, desc, path, body, detail=False, name='연세대학교', citation=SOURCE):
    url = BASE + path
    crumbs = [{'@type':'ListItem','position':1,'name':'홈','item':BASE}, {'@type':'ListItem','position':2,'name':'2028 대입','item':BASE+'admission/2028/'}]
    if detail: crumbs.append({'@type':'ListItem','position':3,'name':name,'item':url})
    schema = [{'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':crumbs}]
    if detail: schema.append({'@context':'https://schema.org','@type':'Article','headline':title,'description':desc,'mainEntityOfPage':url,'citation':citation,'inLanguage':'ko-KR'})
    root = '../../../' if detail else '../../'
    assets = '../' if detail else './'
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><meta name="robots" content="index,follow"><link rel="canonical" href="{url}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:type" content="{'article' if detail else 'website'}"><meta property="og:image" content="{BASE}og-image.png">
<script type="application/ld+json">{json.dumps(schema,ensure_ascii=False)}</script><link rel="stylesheet" href="{assets}admission.css"><script src="{assets}admission.js" defer></script></head>
<body><a class="skip" href="#main">본문 바로가기</a><header><a class="brand" href="{root}"><span class="logo">作</span> 작전고 교육과정 박람회</a><a class="header-link school-link" href="{root}#checklist">내 과목 선택표 <span>↗</span></a></header>
<main id="main"><nav class="crumb" aria-label="현재 위치"><a href="{root}">홈</a><span>/</span><a href="{assets}">2028 대입</a>{'<span>/</span>'+E(name) if detail else ''}</nav>{body}</main>
<footer><strong>작전고 교육과정 박람회</strong><p>대학의 안내를 읽고, 우리 학교에서 가능한 선택으로 연결합니다.</p><a href="{root}#guide">과목 안내</a> · <a class="school-link" href="{root}#checklist">과목 선택 체크리스트</a></footer></body></html>'''

cards = []
for i, row in enumerate(data['rows']):
    query = urlencode({'university':'연세대','unit':i})
    cards.append(f'''<article class="unit" data-unit><div class="unit-heading"><span class="eyebrow">{E(row['college'])}</span><h3>{E(row['name'])}</h3></div><dl><div><dt>수학 · 진로선택</dt><dd>{E(row['math'])}</dd></div><div><dt>과학 · 일반선택</dt><dd>{E(row['science'])}</dd></div><div><dt>과학 · 진로선택</dt><dd>{E(row['advanced'])}</dd></div></dl><a class="unit-link school-link" href="../../../?{query}#checklist">이 모집단위로 과목 설계 <span>→</span></a></article>''')
body = f'''<section class="hero"><div><p class="eyebrow">2028 ADMISSION GUIDE · 서울캠퍼스</p><h1>연세대가 궁금하다면,<br><em>과목 선택</em>부터.</h1><p class="lead">모집단위별 전공연계과목을 확인하고<br>나의 3개년 과목 선택으로 이어가세요.</p><div class="actions"><a class="button" href="#departments">내 희망학과 찾기 ↓</a><a class="button light" href="{SOURCE}">대학 공식자료 ↗</a></div><p class="meta">기준 자료: 연세대학교 입학처 · 2026년 4월 가이드라인</p></div><aside class="summary"><span class="eyebrow">먼저 알아둘 3가지</span><ol><li><b>자연·의치약 계열 수학</b><span>기하와 미적분Ⅱ 이수를 권장합니다.</span></li><li><b>과학은 모집단위와 위계 확인</b><span>일반선택 안내와 진로선택 3과목 이상 권장을 함께 읽으세요.</span></li><li><b>학교의 개설 여건도 고려</b><span>과목 이수 여부 하나만으로 평가하지 않습니다.</span></li></ol></aside></section>
<nav class="sections" aria-label="본문 목차"><a href="#departments">01 모집단위 찾기</a><a href="#guide">02 선택 가이드</a><a href="#faq">03 자주 묻는 질문</a></nav>
<section id="departments"><div class="section-top"><div><p class="eyebrow">FIND YOUR MAJOR</p><h2>내 학과는 어떤 과목을 권장할까?</h2></div><span class="count" id="result-count" aria-live="polite">{len(cards)}개 모집단위·그룹</span></div><p>아래 내용은 공식자료의 전공연계과목 안내입니다. ‘미제시’는 과목 선택이 평가와 무관하다는 뜻이 아닙니다.</p><label class="search-label" for="major-search">학과·대학·과목 검색</label><input id="major-search" type="search" placeholder="예: 전기전자, 컴퓨터, 생명과학" autocomplete="off"><div class="units">{''.join(cards)}</div><p id="empty" hidden>일치하는 모집단위가 없습니다. 학과명 일부나 과목명으로 다시 검색해 보세요.</p></section>
<section id="guide"><p class="eyebrow">FROM GUIDE TO PLAN</p><h2>권장과목을 나의 시간표로</h2><div class="guides"><article><span class="step">01</span><h3>수학의 연결을 살펴보세요</h3><p>자연·의치약 계열은 기하와 미적분Ⅱ를 권장합니다. 학교 편성표에서 이수 순서와 개설 학기를 확인해 보세요.</p></article><article><span class="step">02</span><h3>과학은 위계를 함께 보세요</h3><p>‘자율선택’은 물리학·화학·생명과학·지구과학 중 선택할 수 있다는 의미입니다. 진로선택은 일반선택과의 위계를 고려합니다.</p></article><article><span class="step">03</span><h3>학교에서 가능한 선택을 확인하세요</h3><p>학교에 개설되지 않은 과목은 개설되어도 이수하지 않은 경우와 구분하여 평가합니다. 공동교육과정 등은 선생님과 상담해 보세요.</p></article></div></section>
<section class="cta"><div><p class="eyebrow">YOUR NEXT STEP</p><h2>읽었다면, 직접 설계해 볼까요?</h2><p>위에서 모집단위를 고르면 기존 체크리스트에 희망 대학이 연결됩니다.<br>일반선택의 ‘택 1’과 과학 진로선택 개수는 공식자료와 함께 확인하세요.</p></div><a class="button school-link" href="../../../#checklist">내 과목 선택표 만들기 →</a></section>
<section id="faq"><p class="eyebrow">QUESTIONS & ANSWERS</p><h2>선택 전에 많이 묻는 질문</h2><details><summary>미적분Ⅱ를 이수하지 않으면 지원할 수 없나요?</summary><p>이 자료는 전공연계과목 선택 가이드라인입니다. 권장과목을 곧바로 지원 자격으로 해석하지 마세요. 지원 자격은 해당 연도 전형별 모집요강에서 별도로 확인해야 합니다.</p></details><details><summary>컴퓨터과학과는 물리학을 반드시 골라야 하나요?</summary><p>공식 표의 컴퓨터과학과 과학 일반선택은 ‘자율선택’입니다. 수학 진로선택과 과학 진로선택 안내도 함께 확인하세요.</p></details><details><summary>인문계열과 간호대학은 어떻게 선택하나요?</summary><p>공식 표는 해당 그룹에 전공연계과목을 별도로 제시하지 않습니다. 진로와 적성에 맞는 선택과 이수를 권장합니다.</p></details><details><summary>과목 선택 도구가 대학 평가를 판정해 주나요?</summary><p>도구는 과목 설계를 돕는 참고 기능입니다. 과목 이름 매칭만으로 대학의 종합평가, 지원 가능 여부, 합격 가능성을 판단할 수 없습니다.</p></details></section>
<aside class="source"><h2>자료 출처와 적용 범위</h2><p><a href="{SOURCE}">연세대학교 2028학년도 전공연계과목 선택 가이드라인 · PDF</a></p><p>서울캠퍼스 기준이며 미래캠퍼스 자료와 구분합니다. 대학 발표가 변경될 수 있으므로 최종 내용은 <a href="https://admission.yonsei.ac.kr/seoul/">입학처</a>에서 확인하세요.</p></aside>'''
(ROOT/'admission/2028/yonsei/index.html').write_text(page('2028 연세대 선택과목｜모집단위별 전공연계과목 안내','연세대 서울캠퍼스 2028 전공연계과목: 기하·미적분Ⅱ, 과학 선택을 확인하고 학교 과목 선택표로 연결하세요.','admission/2028/yonsei/',body,True),encoding='utf-8')
hub='''<section class="hero hub-hero"><div><p class="eyebrow">2028 ADMISSION · SUBJECT PLANNING</p><h1>희망 대학에서 시작하는<br><em>나의 과목 선택.</em></h1><p class="lead">대학의 권장과목을 읽는 것에서 한 걸음 더.<br>공식자료 확인부터 우리 학교 과목 설계까지 함께해요.</p><a class="button" href="yonsei/">연세대 선택과목 살펴보기 →</a></div><aside class="journey"><span>01 대학 안내 읽기</span><span>02 모집단위 찾기</span><span>03 나의 과목표 만들기</span></aside></section><section><p class="eyebrow">UNIVERSITY GUIDES</p><h2>대학별 선택과목 안내</h2><p>공식자료를 확인한 상세페이지부터 순차적으로 추가합니다.</p><a class="featured" href="yonsei/"><div><span class="eyebrow">공식 가이드라인 기반 · 서울캠퍼스</span><h3>연세대학교</h3><p>기하·미적분Ⅱ부터 모집단위별 과학 선택까지</p></div><span class="big-arrow">↗</span></a></section><section class="guides"><article><h2>다른 대학도 궁금하다면</h2><p>기존 대학별 권장과목 도구에서 지역과 대학을 선택해 보세요. 대학별 자료의 발표 시점은 다를 수 있습니다.</p><a class="text-link school-link" href="../../#univ">대학별 권장과목 도구 →</a></article><article><h2>과목 이름이 낯설다면</h2><p>교과별 과목 안내에서 무엇을 배우는지 살펴보고, 관심 분야와 연결해 보세요.</p><a class="text-link school-link" href="../../#guide">교과별 과목 안내 →</a></article><article><h2>시간표로 옮겨보고 싶다면</h2><p>학교 편성표를 기준으로 학기별 과목을 선택하고 이수 학점을 확인하세요.</p><a class="text-link school-link" href="../../#checklist">과목 선택 체크리스트 →</a></article></section>'''
(ROOT/'admission/2028/index.html').write_text(page('2028 대입 선택과목 안내｜작전고 교육과정 박람회','대학별 공식자료와 전공연계과목을 확인하고 나의 3개년 과목 선택표로 연결하는 2028 대입 안내.','admission/2028/',hub),encoding='utf-8')
(ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{BASE}{p}</loc></url>\n' for p in ['', 'admission/2028/','admission/2028/yonsei/'])+'</urlset>\n',encoding='utf-8')
print('Generated hub, Yonsei page and sitemap.')

from admission_universities import build
build(ROOT, BASE, page)
