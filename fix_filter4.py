f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()

lines[391] = '  doSearch(searchInput.value.trim());\n'
lines[392] = ''
lines[397] = '  doSearch(searchInput.value.trim());\n'
lines[398] = ''

open('templates/sales/pos.html', 'w', encoding='utf-8').writelines(lines)
print('Done')
