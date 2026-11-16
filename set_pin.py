from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from accounts.models import OwnerPIN

NEW_PIN = '1234'   # <-- change this to the PIN you want
User = get_user_model()
owner = User.objects.filter(role='owner').order_by('id').first()
OwnerPIN.objects.update_or_create(user=owner, defaults={'pin_hash': make_password(NEW_PIN), 'attempts': 0, 'locked_until': None})
print('Owner PIN saved for:', owner.username)
