content = open('sales/views.py', encoding='utf-8').read()

old = '''    if len(q) < 1:
        return JsonResponse({'results': []})

    products = (
        Product.objects
        .select_related('category')
        .prefetch_related('stock_level')
        .filter(is_active=True)
        .filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(barcode__iexact=q) |
            Q(sku__icontains=q) |
            Q(model_number__icontains=q)
        )[:15]
    )'''

new = '''    cat_id = request.GET.get('cat', '').strip()

    products = (
        Product.objects
        .select_related('category')
        .prefetch_related('stock_level')
        .filter(is_active=True)
    )
    if q:
        products = products.filter(
            Q(name__icontains=q) |
            Q(brand__icontains=q) |
            Q(barcode__iexact=q) |
            Q(sku__icontains=q) |
            Q(model_number__icontains=q)
        )
    if cat_id:
        products = products.filter(category_id=cat_id)
    if not q and not cat_id:
        return JsonResponse({'results': []})
    products = products[:15]'''

content = content.replace(old, new)
open('sales/views.py', 'w', encoding='utf-8').write(content)
print('Done')
