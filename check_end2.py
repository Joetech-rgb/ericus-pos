f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
for i in range(720, 730):
    print(i, repr(lines[i]))
