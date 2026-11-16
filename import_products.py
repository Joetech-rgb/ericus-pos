# Adjei God First Ventures - load the price list into the system
from decimal import Decimal
from django.contrib.auth import get_user_model
from products.models import Category, Product
from inventory.models import StockLevel

# (category, product name, brand, pack size, selling price in GHS)
PRODUCTS = [
    # ---- Rice
    ('Rice', 'OKI Rice 22.5kg', 'OKI', '22.5kg', 270),
    ('Rice', 'OKI Rice 50kg', 'OKI', '50kg', 570),
    ('Rice', 'LAFIA Rice 22.5kg', 'LAFIA', '22.5kg', 280),
    ('Rice', 'LAFIA Rice 50kg', 'LAFIA', '50kg', 590),
    ('Rice', 'LAYA Rice 22.5kg', 'LAYA', '22.5kg', 280),
    ('Rice', 'LE BANQUET Rice 22.5kg', 'LE BANQUET', '22.5kg', 280),
    ('Rice', 'LA MERVEILLE Rice 22.5kg', 'LA MERVEILLE', '22.5kg', 280),
    ('Rice', 'MARIANA Rice 22.5kg', 'MARIANA', '22.5kg', 265),
    ('Rice', 'MARIANA Rice 50kg', 'MARIANA', '50kg', 505),
    ('Rice', 'TILEMSI Rice 22.5kg', 'TILEMSI', '22.5kg', 280),
    ('Rice', 'TILEMSI Rice 50kg', 'TILEMSI', '50kg', 570),
    ('Rice', '3 DAUPHINS Rice 22.5kg', '3 DAUPHINS', '22.5kg', 300),
    ('Rice', '3 DAUPHINS Rice 50kg', '3 DAUPHINS', '50kg', 600),
    ('Rice', 'MON AMI Rice 50kg', 'MON AMI', '50kg', 570),
    ('Rice', 'POISSION Rice 22.5kg', 'POISSION', '22.5kg', 290),
    ('Rice', 'AL-FALAH Rice 50kg', 'AL-FALAH', '50kg', 570),
    ('Rice', 'HAPPY VIREN Rice 50kg', 'HAPPY VIREN', '50kg', 470),
    ('Rice', 'SAE LONY BLUE Rice 22.5kg', 'SAE LONY', '22.5kg', 280),
    ('Rice', 'SAE LONY BLUE Rice 50kg', 'SAE LONY', '50kg', 550),
    ('Rice', 'SAE LONY RED Rice 50kg', 'SAE LONY', '50kg', 440),
    ('Rice', 'RIZ MA VIE Rice 22.5kg', 'RIZ MA VIE', '22.5kg', 250),
    ('Rice', 'DINOR Rice 5kg', 'DINOR', '5kg', 90),
    # ---- Flour, sugar, salt, baking
    ('Flour, Sugar and Salt', 'STOOL FLOUR 50kg', 'STOOL', '50kg', 610),
    ('Flour, Sugar and Salt', 'SUGAR 50kg', '', '50kg', 580),
    ('Flour, Sugar and Salt', 'SALT 25kg', '', '25kg', 100),
    ('Flour, Sugar and Salt', 'MACI 26kg', 'MACI', '26kg', 260),
    ('Flour, Sugar and Salt', 'MACI 50kg', 'MACI', '50kg', 540),
    ('Flour, Sugar and Salt', 'BAKING POWDER Big', '', 'Big', 35),
    ('Flour, Sugar and Salt', 'BAKING POWDER Small', '', 'Small', 20),
    # ---- Oil
    ('Oil and Cooking Fat', 'OIL AYA 25 litres', 'AYA', '25 litres', 560),
    ('Oil and Cooking Fat', 'OIL VIKIN 22.5kg', 'VIKIN', '22.5kg', 535),
    ('Oil and Cooking Fat', 'OIL OHENE 25kg', 'OHENE', '25kg', 555),
    ('Oil and Cooking Fat', 'COOK BRAND 900g', 'COOK BRAND', '900g', 70),
    ('Oil and Cooking Fat', 'COOK BRAND 4.5kg', 'COOK BRAND', '4.5kg', 260),
    ('Oil and Cooking Fat', 'COOK BRAND 10kg', 'COOK BRAND', '10kg', 460),
    ('Oil and Cooking Fat', 'FORTUNE 4.5kg', 'FORTUNE', '4.5kg', 190),
    ('Oil and Cooking Fat', 'FORTUNE 10kg', 'FORTUNE', '10kg', 340),
    ('Oil and Cooking Fat', 'FRYTOL 4.5kg', 'FRYTOL', '4.5kg', 145),
    ('Oil and Cooking Fat', 'SUN FLOWER 5kg', 'SUN FLOWER', '5kg', 160),
    ('Oil and Cooking Fat', 'SUN FLOWER Small', 'SUN FLOWER', 'Small', 40),
    ('Oil and Cooking Fat', 'BUTTER FLAVOUR', '', '', 85),
    # ---- Canned fish
    ('Canned Fish', 'TIPA MACKEREL', 'TIPA', '', 15),
    ('Canned Fish', 'TIPA MACKEREL Box', 'TIPA', 'Box', 335),
    ('Canned Fish', 'TINAPA MACKEREL Small', 'TINAPA', 'Small', 7),
    ('Canned Fish', 'TIPA SARDINE 1', 'TIPA', '', 8),
    ('Canned Fish', 'TIPA SARDINE 2', 'TIPA', '', 15),
    ('Canned Fish', 'TIPA SARDINE Box', 'TIPA', 'Box', 330),
    # ---- Spaghetti
    ('Spaghetti', 'OBA SPAGHETTI Box', 'OBA', 'Box', 150),
    ('Spaghetti', 'GINNY SPAGHETTI Box', 'GINNY', 'Box', 140),
    ('Spaghetti', 'GINNY SPAGHETTI 1', 'GINNY', '1 pack', 8),
    # ---- Seasoning
    ('Seasoning', 'TOP CHEF Big', 'TOP CHEF', 'Big', 45),
    ('Seasoning', 'TOP CHEF Small', 'TOP CHEF', 'Small', 10),
    ('Seasoning', 'ONGA PACK', 'ONGA', 'Pack', 31),
]

owner = next((u for u in get_user_model().objects.all() if getattr(u, 'is_owner', False)), None)
made = 0
changed = 0
for cat, name, brand, size, price in PRODUCTS:
    category, _ = Category.objects.get_or_create(name=cat)
    product, was_new = Product.objects.update_or_create(
        name=name,
        defaults={
            'category': category,
            'brand': brand,
            'capacity': size,
            'selling_price': Decimal(str(price)),
            'track_serials': False,
            'warranty_months': 0,
            'reorder_point': 20 if price <= 50 else 5,
            'is_active': True,
            'created_by': owner,
        },
    )
    StockLevel.objects.get_or_create(product=product)
    if was_new:
        made += 1
    else:
        changed += 1

print('Products added:', made, '| already there (prices refreshed):', changed)
print('Categories:', ', '.join(sorted(set(p[0] for p in PRODUCTS))))
print('Total products in the list:', len(PRODUCTS))
