f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()

for i, line in enumerate(lines):
    if 'const data = new FormData(form);' in line:
        # Add auto-fill cash tendered if empty
        insert = (
            '  const cashInput = document.getElementById(\'cashTendered\');\n'
            '  if (document.getElementById(\'paymentMethod\').value === \'cash\' && !cashInput.value) {\n'
            '    cashInput.value = cartTotal.toFixed(2);\n'
            '  }\n'
        )
        lines[i] = insert + line
        print(f'Fixed at line {i}')
        break

open('templates/sales/pos.html', 'w', encoding='utf-8').writelines(lines)
print('Done')
