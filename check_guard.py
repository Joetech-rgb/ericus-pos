f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
for i, line in enumerate(lines):
    if 'if (!q' in line or 'selectedCatId' in line:
        print(i, repr(line))
