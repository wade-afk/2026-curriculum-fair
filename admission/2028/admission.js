// Static HTML stays readable and linked when JavaScript is unavailable.
const search = document.getElementById('major-search');
if (search) {
  const units = [...document.querySelectorAll('[data-unit]')];
  const normalize = value => value.normalize('NFKC').toLocaleLowerCase('ko').replace(/\s+/g, '');
  search.addEventListener('input', () => {
    const query = normalize(search.value);
    let count = 0;
    units.forEach(unit => {
      unit.hidden = !normalize(unit.textContent).includes(query);
      if (!unit.hidden) count++;
    });
    document.getElementById('result-count').textContent = `${count}개 모집단위·그룹`;
    document.getElementById('empty').hidden = count !== 0;
  });
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
