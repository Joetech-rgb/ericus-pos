f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
for i in range(385, 402):
    print(i, repr(lines[i]))
