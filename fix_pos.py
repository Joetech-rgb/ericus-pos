content = open('templates/sales/pos.html', encoding='utf-8').read()

old1 = 'function doSearch(q) {\n  if (!q) return;\n  fetch(`{% url \'sales:product_search\' %}?q=${encodeURIComponent(q)}&sale_type=${currentSaleType}`)'
new1 = 'function doSearch(q) {\n  fetch(`{% url \'sales:product_search\' %}?q=${encodeURIComponent(q)}&sale_type=${currentSaleType}&cat=${selectedCatId}`)'
content = content.replace(old1, new1)

old2 = '  const q = searchInput.value.trim();\n  if (q) doSearch(q);\n}\nfunction setSaleType'
new2 = '  doSearch(searchInput.value.trim());\n}\nfunction setSaleType'
content = content.replace(old2, new2)

old3 = 'if (!q) {'
new3 = 'if (!q && !selectedCatId) {'
content = content.replace(old3, new3, 1)

open('templates/sales/pos.html', 'w', encoding='utf-8').write(content)
print('Done - replacements made')
