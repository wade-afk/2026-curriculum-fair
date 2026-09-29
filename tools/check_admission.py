"""Regression checks for source projection, static links and deep-link validation."""
import json,re,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote,parse_qs

root=Path(__file__).resolve().parents[1]
source=(root/'index.html').read_text(encoding='utf-8')
universities=json.loads(re.search(r'const UNIV_DATA = (.*);',source)[1])
data=json.loads((root/'admission/2028/yonsei/data.json').read_text(encoding='utf-8'))
yonsei=next(u for u in universities if u['univ']=='연세대')
assert len(yonsei['rows'])==len(data['rows'])==47
for row,legacy in zip(data['rows'],yonsei['rows']):
    assert legacy[:2]==[row['college'],row['name']]
    assert not legacy[2], 'Recommendations must not become core requirements'
    if '또는' in row['science'] or '택 1' in row['science']:
        assert legacy[3]=='기하, 미적분Ⅱ', 'Alternatives must not become all-required'

class Document(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[];self.canon=[];self.h1=0;self.units=0;self.script=False;self.schemas=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a':self.links.append(a.get('href',''))
        if tag=='link' and a.get('rel')=='canonical':self.canon.append(a['href'])
        if tag=='h1':self.h1+=1
        if 'data-unit' in a:self.units+=1
        if tag=='script' and a.get('type')=='application/ld+json':self.script=True
    def handle_data(self,text):
        if self.script:self.schemas.extend(json.loads(text))
    def handle_endtag(self,tag):
        if tag=='script':self.script=False

for path in [root/'admission/2028/index.html']+list((root/'admission/2028').glob('*/index.html')):
    doc=Document();doc.feed(path.read_text(encoding='utf-8'))
    assert doc.h1==1 and len(doc.canon)==1
    assert any(s['@type']=='BreadcrumbList' for s in doc.schemas)
    if path.parent.name=='yonsei':assert doc.units==47 and any(s['@type']=='Article' for s in doc.schemas)
    for href in doc.links:
        url=urlsplit(href)
        if url.scheme:continue
        target=(path.parent/unquote(url.path)).resolve() if url.path else path
        if target.is_dir():target=target/'index.html'
        assert target.is_file(), (path,href)
        query=parse_qs(url.query)
        if 'unit' in query:
            uni=next(u for u in universities if u['univ']==query['university'][0])
            assert uni['rows'][int(query['unit'][0])]
    print('Static page and links OK:',path.relative_to(root))
ET.parse(root/'sitemap.xml')
fn=re.search(r'function admissionTarget\(\)\{.*?\n\}',source,re.S)[0]
js='const assert=require("node:assert/strict");const UNIV_DATA='+json.dumps(universities)+';let location={search:""};'+fn+'''
for(const query of ['', '?university=missing&unit=0', '?university=%EC%97%B0%EC%84%B8%EB%8C%80&unit=-1', '?university=%EC%97%B0%EC%84%B8%EB%8C%80&unit=999', '?university=%EC%97%B0%EC%84%B8%EB%8C%80&unit=1.5']){location.search=query;assert.equal(admissionTarget(),null);}
location.search='?university=%EC%97%B0%EC%84%B8%EB%8C%80&unit=7';assert.equal(admissionTarget().index,7);
'''
subprocess.run(['node','-'],input=js,text=True,encoding='utf-8',check=True)
print('47 source rows, recommendation semantics, sitemap and URL validation OK.')

for slug,name,count in [('snu','서울대',78),('korea','고려대',32)]:
    rows=json.loads((root/f'admission/2028/{slug}/data.json').read_text(encoding='utf-8'))['rows']
    legacy=next(u for u in universities if u['univ']==name)['rows']
    assert len(rows)==count
    assert len({r['index'] for r in rows})==count
    for row in rows:
        for i in [row['index']]+row.get('aliases',[]):
            assert legacy[i][:2]==[row['college'],row['name']]
            assert not legacy[i][2], 'Official 2028 guidance has no core category'
            assert row['advanced'] in legacy[i][4]
    if slug=='snu':
        for unit in ['간호대학','식품영양학과','의류학과']:
            assert next(r for r in rows if r['name']==unit)['type']=='유형 ①·②'
        assert '또는' in next(r for r in rows if r['name']=='간호대학')['math']
        assert '또는' in next(r for r in rows if r['name']=='치의학과')['math']
        assert '세포와 물질대사' in next(r for r in rows if r['name']=='의예과')['advanced']
    else:
        for unit in ['신소재공학부','융합에너지공학과','바이오의공학부','스마트모빌리티학부']:
            row=next(r for r in rows if r['name']==unit)
            assert len(row['science'].split(', '))==4 and row['minimum']==2
            assert '세포와 물질대사' not in legacy[row['index']][3]
    print(name,count,'cards synchronized; official exceptions checked.')
