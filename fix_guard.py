f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()
lines[362] = "  if (!q && !selectedCatId && !initialLoad) {\n"
# Find the closing of that if block and add initialLoad = false after
for i in range(363, 370):
    if "return;" in lines[i]:
        lines[i+1] = "  initialLoad = false;\n" + lines[i+1]
        break
# Add initialLoad variable near selectedCatId
lines[347] = lines[347] + "let initialLoad = true;\n"
open('templates/sales/pos.html', 'w', encoding='utf-8').writelines(lines)
print('Done')
