f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()

for i, line in enumerate(lines):
    if "doSearch('');" in line and i > 700:
        lines[i] = "setTimeout(() => doSearch(''), 100);\n"
        print(f'Fixed at line {i}')
        break

open('templates/sales/pos.html', 'w', encoding='utf-8').writelines(lines)
print('Done')
