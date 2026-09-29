// Static HTML stays readable and linked when JavaScript is unavailable.
const search = document.getElementById('major-search');
if (search) {
  const units = [...document.querySelectorAll('[data-unit]')];
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g, '');
  const more = document.createElement('button');
  more.className = 'more-units';
  more.type = 'button';
  document.querySelector('.units').after(more);
  let limit = 6;
  const render = () => {
    const query = normalize(search.value);
    const matches = units.filter(unit => normalize(unit.textContent).includes(query));
    units.forEach(unit => { unit.hidden = true; });
    matches.slice(0, limit).forEach(unit => { unit.hidden = false; });
    document.getElementById('result-count').textContent = `${matches.length}개 모집단위·그룹`;
    document.getElementById('empty').hidden = matches.length !== 0;
    more.hidden = matches.length <= limit;
    more.textContent = `모집단위 더 보기 (${Math.min(limit, matches.length)}/${matches.length})`;
  };
  search.addEventListener('input', () => { limit = 6; render(); });
  more.addEventListener('click', () => { limit += 6; render(); });
  render();
}
if (matchMedia('(max-width:600px)').matches) {
  document.querySelectorAll('.mobile-fold').forEach(item => { item.open = false; });
}
// Retain explicit school context across content and tool navigation.
const params = new URLSearchParams(location.search);
for (const anchor of document.querySelectorAll('a')) {
  const url = new URL(anchor.href, location.href);
  if (url.origin !== location.origin) continue;
  for (const key of ['school', 'lock']) {
    if (params.has(key)) url.searchParams.set(key, params.get(key));
  }
  anchor.href = url.href;
}
