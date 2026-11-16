from products.models import Product
keep = ['Rice', 'Oil and Cooking Fat', 'Flour, Sugar and Salt', 'Canned Fish', 'Spaghetti', 'Seasoning']
n = Product.objects.exclude(category__name__in=keep).update(is_active=False)
print('old products hidden:', n)
