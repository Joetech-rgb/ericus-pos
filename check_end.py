f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
for i in range(714, 722):
    print(i, repr(lines[i]))
