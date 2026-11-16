from products.models import Product

bad = 0
for p in Product.objects.filter(is_active=True):
    try:
        lvl = p.stock_level.quantity
    except Exception:
        lvl = None
    if lvl != p.current_stock:
        bad += 1
        print(p.id, p.name, '| products page:', p.current_stock, '| sales screen and dashboard:', lvl)

print('products that disagree:', bad)
