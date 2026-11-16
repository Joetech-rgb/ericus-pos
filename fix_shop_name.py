from django.contrib.auth import get_user_model
from accounts.models import ShopProfile

OLD = "Adjei God First Ventures"
NEW = "Adjei\u2019s God First Ventures"

shops = list(ShopProfile.objects.all())
if not shops:
    owner = next((u for u in get_user_model().objects.all() if getattr(u, 'is_owner', False)), None)
    if owner is None:
        print('No owner account found.')
    else:
        ShopProfile.objects.create(owner=owner, name=NEW, receipt_footer='Thank you for choosing ' + NEW)
        print('Shop record created:', ascii(NEW))

for s in shops:
    s.name = NEW
    footer = s.receipt_footer or ''
    s.receipt_footer = footer.replace(OLD, NEW).replace('Ericus', NEW)
    s.save()
    print('Shop name now:', ascii(s.name), '| receipt message:', ascii(s.receipt_footer))
