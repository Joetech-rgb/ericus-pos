from decimal import Decimal
from django.contrib.auth import get_user_model
from products.models import Product
from inventory.models import StockLevel
from inventory.utils import record_movement

TARGET_STOCK = 8
CATEGORIES = ['Rice', 'Oil and Cooking Fat', 'Flour, Sugar and Salt', 'Canned Fish', 'Spaghetti', 'Seasoning']

owner = next((u for u in get_user_model().objects.all() if getattr(u, 'is_owner', False)), None)
products = Product.objects.filter(category__name__in=CATEGORIES, track_serials=False, is_active=True).order_by('name')

stock_set = 0
cost_set = 0
half_price_items = []
for p in products:
    # ---- stock: bring it to exactly 8 through the normal stock records
    level, _ = StockLevel.objects.get_or_create(product=p)
    diff = TARGET_STOCK - level.quantity
    if diff > 0:
        record_movement(product=p, movement_type='initial', quantity=diff, user=owner,
                        note='Test stock: %s each' % TARGET_STOCK, serial_number='')
        stock_set += 1
    elif diff < 0:
        record_movement(product=p, movement_type='adjustment_out', quantity=-diff, user=owner,
                        note='Test stock: %s each' % TARGET_STOCK, serial_number='')
        stock_set += 1

    # ---- cost: selling price minus 10 (items under GHS 10 would go to zero, so they get half the price)
    price = p.selling_price
    if price > 10:
        cost = price - Decimal('10')
    else:
        cost = (price / Decimal('2')).quantize(Decimal('0.01'))
        half_price_items.append('%s (price %s, cost %s)' % (p.name, price, cost))
    Product.objects.filter(pk=p.pk).update(cost_price=cost)
    cost_set += 1

print('Products updated:', products.count())
print('Stock set to %s for: %s product(s)' % (TARGET_STOCK, stock_set))
print('Cost price set for: %s product(s)' % cost_set)
if half_price_items:
    print('Priced GHS 10 or less, so cost = half the price:')
    for line in half_price_items:
        print('   ', line)
for p in Product.objects.filter(category__name__in=CATEGORIES).order_by('name')[:3]:
    p.refresh_from_db()
    print('Example:', p.name, '| price', p.selling_price, '| cost', p.cost_price, '| stock', p.stock_level.quantity)
