f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
for i in range(718, 727):
    print(i, repr(lines[i]))
