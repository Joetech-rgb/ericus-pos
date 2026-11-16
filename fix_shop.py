from accounts.models import ShopProfile

for s in ShopProfile.objects.all():
    s.name = 'Adjei God First Ventures'
    f = s.receipt_footer or ''
    if 'Ericus' in f:
        s.receipt_footer = f.replace('Ericus', 'Adjei God First Ventures')
    s.save()
    print('updated:', s.name, '|', s.receipt_footer)

print('shops found:', ShopProfile.objects.count())
