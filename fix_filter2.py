content = open('templates/sales/pos.html', encoding='utf-8').read()

old = "  const q = searchInput.value.trim();\n  if (q) doSearch(q);\n}\nfunction setSaleType(val) {\n  currentSaleType = val;\n  const q = searchInput.value.trim();\n  if (q) doSearch(q);\n}"
new = "  doSearch(searchInput.value.trim());\n}\nfunction setSaleType(val) {\n  currentSaleType = val;\n  doSearch(searchInput.value.trim());\n}"

result = content.replace(old, new)
if result == content:
    print('WARNING: no match found')
else:
    open('templates/sales/pos.html', 'w', encoding='utf-8').write(result)
    print('Done')
