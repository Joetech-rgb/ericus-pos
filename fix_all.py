content = open('sales/views.py', encoding='utf-8').read()

old = "    if not q and not cat_id:\n        return JsonResponse({'results': []})\n    products = products[:15]"
new = "    if not q and not cat_id:\n        pass  # show all when All tab clicked\n    products = products[:30]"

result = content.replace(old, new)
if result == content:
    print('WARNING: no match')
else:
    open('sales/views.py', 'w', encoding='utf-8').write(result)
    print('Done')
