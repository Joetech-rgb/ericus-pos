f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
for i, line in enumerate(lines):
    if any(x in line for x in ['filterCat', 'doSearch', 'setSaleType', 'if (q)']):
        print(i, repr(line))
