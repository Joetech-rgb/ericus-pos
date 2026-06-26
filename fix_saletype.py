f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()

for i, line in enumerate(lines):
    if 'const data = new FormData(form);' in line:
        lines[i] = line + '  data.append(\'sale_type\', currentSaleType);\n'
        print(f'Fixed at line {i}')
        break

open('templates/sales/pos.html', 'w', encoding='utf-8').writelines(lines)
print('Done')
