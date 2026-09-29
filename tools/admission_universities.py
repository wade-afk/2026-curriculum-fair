"""Build reviewed SNU/Korea articles and synchronize the existing planning tool."""
import html,json,re
from urllib.parse import urlencode

E=html.escape

def build(root,base,page):
    source=(root/'index.html').read_text(encoding='utf-8')
    match=re.search(r'const UNIV_DATA = (.*);',source)
    universities=json.loads(match[1])
    hub_cards=[]
    for slug in ('snu','korea'):
        folder=root/'admission/2028'/slug
        data=json.loads((folder/'data.json').read_text(encoding='utf-8'))
        article=json.loads((folder/'article.json').read_text(encoding='utf-8'))
        university=next(u for u in universities if u['univ']==data['university'])
        cards=[]
        for row in data['rows']:
            fields=[('수학 · 진로선택',row['math']),('과학 · 일반선택 우선 이수' if slug=='snu' else '과학 · 진로선택',row['science']),('과학 · 진로선택 조건' if slug=='snu' else '과학 선택 조건',row['advanced'])]
            if slug=='snu':fields.append(('제2외국어/한문',row['foreign']))
            note=' / '.join(f'{label}: {value}' for label,value in fields)+' / '+row['note']
            # Core/required is not an official category for these 2028 documents.
            candidates=[]
            if row['math']!='별도 제시 없음' and '또는' not in row['math']:candidates.append(row['math'])
            if row['science'] not in ('별도 제시 없음','일반선택 우선 이수 과목 별도 제시 없음') and '또는' not in row['science']:candidates.append(row['science'])
            if slug=='snu' and row['name']=='의예과':candidates.append('세포와 물질대사, 생물의 유전')
            projected=[row['college'],row['name'],'',', '.join(candidates),note]
            for idx in [row['index']]+row.get('aliases',[]):
                assert idx<=len(university['rows']), (slug,idx)
                if idx==len(university['rows']):university['rows'].append(projected)
                else:university['rows'][idx]=projected
            query=urlencode({'university':data['university'],'unit':row['index']})
            dl=''.join(f'<div><dt>{E(label)}</dt><dd>{E(value)}</dd></div>' for label,value in fields)
            cards.append(f'<article class="unit" data-unit><div class="unit-heading"><span class="eyebrow">{E(row["college"])} · {E(row["type"])}</span><h3>{E(row["name"])}</h3></div><dl>{dl}</dl><p class="unit-note">{E(row["note"])}</p><a class="unit-link school-link" href="../../../?{E(query)}#checklist">이 모집단위로 과목 설계 <span>→</span></a></article>')
        summary=''.join(f'<li><b>{E(title)}</b><span>{E(text)}</span></li>' for title,text in article['summary'])
        sections=''.join('<article class="reading"><h3>'+E(sec['title'])+'</h3>'+''.join('<p>'+E(p)+'</p>' for p in sec['paragraphs'])+'</article>' for sec in article['sections'])
        faq=''.join(f'<details><summary>{E(q)}</summary><p>{E(a)}</p></details>' for q,a in article['faq'])
        sources=''.join(f'<li><a href="{E(url)}">{E(label)} ↗</a></li>' for label,url in article['sources'])
        scope_note='공식 표의 단과대학·학부 범위를 학과별로 펼친 안내입니다. 유형이 겹치는 모집단위는 한 카드로 통합했습니다.' if slug=='snu' else '공식 자연계열 표에 실린 32개 모집단위입니다. 인문계열 등 표의 범위 밖 모집단위는 표시하지 않습니다.'
        body=f'''<section class="hero"><div><p class="eyebrow">2028 ADMISSION GUIDE · {E(article['scope'])}</p><h1>{E(article['headline'])}<br><em>{E(article['emphasis'])}</em></h1><p class="lead">{E(article['lead'])}</p><div class="actions"><a class="button" href="#departments">내 희망학과 찾기 ↓</a><a class="button light" href="{E(data['source'])}">대학 공식자료 ↗</a></div><p class="meta">자료 기준: {E(data['sourceDate'])} · 원문 대조: 2026-09-29</p></div><aside class="summary"><span class="eyebrow">먼저 알아둘 3가지</span><ol>{summary}</ol></aside></section>
<nav class="sections" aria-label="본문 목차"><a href="#guide">01 선택 가이드</a><a href="#departments">02 모집단위 찾기</a><a href="#faq">03 자주 묻는 질문</a></nav>
<section id="guide"><p class="eyebrow">READ BEFORE YOU CHOOSE</p><h2>{E(data['university'])} 선택과목, 이렇게 읽어보세요</h2><p class="intro">{E(article['intro'])}</p><div class="article-reading">{sections}</div></section>
<section id="departments"><div class="section-top"><div><p class="eyebrow">FIND YOUR MAJOR</p><h2>내 학과의 과목과 조건 확인하기</h2></div><span class="count" id="result-count" aria-live="polite">{len(cards)}개 모집단위·그룹</span></div><p>{scope_note}</p><label class="search-label" for="major-search">학과·대학·과목 검색</label><input id="major-search" type="search" placeholder="예: 컴퓨터, 간호, 미적분" autocomplete="off"><div class="units">{''.join(cards)}</div><p id="empty" hidden>일치하는 모집단위가 없습니다. 학과명 일부나 과목명으로 다시 검색해 보세요.</p></section>
<section class="cta"><div><p class="eyebrow">FROM INFORMATION TO YOUR PLAN</p><h2>이제 우리 학교 과목표로 옮겨보세요.</h2><p>위 카드의 과목 설계 버튼을 누르면 희망 대학과 모집단위가 연결됩니다.<br>‘또는’, ‘중 2개 이상’, 유형별 조건은 공식자료와 함께 확인하세요.</p></div><a class="button school-link" href="../../../#checklist">내 과목 선택표 만들기 →</a></section>
<section id="faq"><p class="eyebrow">QUESTIONS & ANSWERS</p><h2>선택 전에 많이 묻는 질문</h2>{faq}</section>
<aside class="source"><h2>공식자료와 적용 범위</h2><ul>{sources}</ul><p>{E(article['scope'])} 기준입니다. 발표 내용은 변경될 수 있으므로 최종 전형별 모집요강을 확인하세요. 과목 이름 매칭은 대학 평가·지원 자격·합격 가능성을 판정하는 기능이 아닙니다.</p></aside>
<nav class="related" aria-label="다른 대학 안내"><a href="../">전체 대학 안내 ←</a><a href="../yonsei/">연세대 →</a><a href="../{'korea' if slug=='snu' else 'snu'}/">{'고려대' if slug=='snu' else '서울대'} →</a></nav>'''
        guide_match=re.search(r'<section id="guide">.*?</section>',body,re.S)
        dept_match=re.search(r'<section id="departments">.*?</section>',body,re.S)
        body=body[:guide_match.start()]+dept_match[0]+guide_match[0]+body[dept_match.end():]
        body=body.replace('01 선택 가이드','선택 가이드').replace('02 모집단위 찾기','모집단위 찾기').replace('03 자주 묻는 질문','자주 묻는 질문')
        (folder/'index.html').write_text(page(article['title'],article['description'],f'admission/2028/{slug}/',body,True,article['name'],data['source']),encoding='utf-8')
        hub_cards.append(f'<a class="featured" href="{slug}/"><div><span class="eyebrow">{E(article["scope"])}</span><h3>{E(article["name"])}</h3><p>{E(article["emphasis"])}</p></div><span class="big-arrow">↗</span></a>')
    (root/'index.html').write_text(source[:match.start(1)]+json.dumps(universities,ensure_ascii=False,separators=(',',':'))+source[match.end(1):],encoding='utf-8')
    hub=root/'admission/2028/index.html'
    text=hub.read_text(encoding='utf-8')
    text=text.replace('<p>공식자료를 확인한 상세페이지부터 순차적으로 추가합니다.</p>','<p>서울대·고려대·연세대의 공식 안내를 각각의 기준에 맞춰 확인하세요.</p>'+''.join(hub_cards))
    text=text.replace('<a class="button" href="yonsei/">연세대 선택과목 살펴보기 →</a>','<a class="button" href="#universities">3개 대학 선택과목 살펴보기 ↓</a>')
    text=text.replace('<section><p class="eyebrow">UNIVERSITY GUIDES','<section id="universities"><p class="eyebrow">UNIVERSITY GUIDES')
    text=re.sub(r'<section class="hero hub-hero">.*?</section>', '<section class="catalog-heading"><p class="eyebrow">2028 ADMISSION GUIDE</p><h1>대학별 선택과목</h1><p>희망 대학을 누르면 학과별 과목 안내와 과목 설계로 연결됩니다.</p><span class="count">공식자료 기반 · 3개 대학</span></section>',text,flags=re.S)
    text=text.replace('<section id="universities"><p class="eyebrow">UNIVERSITY GUIDES</p><h2>대학별 선택과목 안내</h2><p>서울대·고려대·연세대의 공식 안내를 각각의 기준에 맞춰 확인하세요.</p>','<section id="universities" class="university-catalog" aria-label="대학 상세페이지 목록">')
    text=text.replace('<span class="big-arrow">↗</span>','<span class="big-arrow">상세보기 →</span>')
    hub.write_text(text,encoding='utf-8')
    yonsei=root/'admission/2028/yonsei/index.html'
    text=yonsei.read_text(encoding='utf-8').replace('</main>','<nav class="related" aria-label="다른 대학 안내"><a href="../">전체 대학 안내 ←</a><a href="../snu/">서울대 →</a><a href="../korea/">고려대 →</a></nav></main>')
    yonsei.write_text(text,encoding='utf-8')
    routes=['','admission/2028/']+[f'admission/2028/{s}/' for s in ('yonsei','snu','korea')]
    (root/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{base}{p}</loc></url>\n' for p in routes)+'</urlset>\n',encoding='utf-8')
    print('Generated SNU/Korea articles; synced tool data and all three university links.')
