f = open('templates/sales/pos.html', encoding='utf-8')
lines = f.readlines()
f.close()

# Line 392 (index): replace "  if (q) doSearch(q);\n" after filterCat
# Line 398 (index): replace "  if (q) doSearch(q);\n" after setSaleType
# Also remove the "const q = ..." lines before them (391 and 397)

new_lines = []
skip_next = False
for i, line in enumerate(lines):
    if skip_next:
        skip_next = False
        continue
    if i == 390 and 'const q' in line:  # before filterCat's if(q)
        new_lines.append('  doSearch(searchInput.value.trim());\n')
        skip_next = True  # skip the if(q) line
    elif i == 396 and 'const q' in line:  # before setSaleType's if(q)
        new_lines.append('  doSearch(searchInput.value.trim());\n')
        skip_next = True
    else:
        new_lines.append(line)

open('templates/sales/pos.html', 'w', encoding='utf-8').writelines(new_lines)
print('Done, lines written:', len(new_lines))
