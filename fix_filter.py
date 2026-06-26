content = open('templates/sales/pos.html', encoding='utf-8').read()

old = '''function filterCat(catId, el) {
  selectedCatId = catId;
  document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  const q = searchInput.value.trim();
  if (q) doSearch(q);
}
function setSaleType(val) {
  currentSaleType = val;
  const q = searchInput.value.trim();
  if (q) doSearch(q);
}'''

new = '''function filterCat(catId, el) {
  selectedCatId = catId;
  document.querySelectorAll('.cat-tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  doSearch(searchInput.value.trim());
}
function setSaleType(val) {
  currentSaleType = val;
  doSearch(searchInput.value.trim());
}'''

result = content.replace(old, new)
if result == content:
    print('WARNING: no match found')
else:
    open('templates/sales/pos.html', 'w', encoding='utf-8').write(result)
    print('Done')
