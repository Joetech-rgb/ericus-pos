import inspect, re
from django.conf import settings
from django.db import transaction
from django.test import Client
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.hashers import check_password
from accounts.models import OwnerPIN

User = get_user_model()

print("\n=== 1. SETTINGS ===")
print("AUTH_USER_MODEL:", settings.AUTH_USER_MODEL)
print("BACKENDS:", getattr(settings, "AUTHENTICATION_BACKENDS", ["default"]))
print("PASSWORD VALIDATORS:", [v["NAME"].split(".")[-1] for v in settings.AUTH_PASSWORD_VALIDATORS])
print("MIDDLEWARE:")
for m in settings.MIDDLEWARE:
    print("   ", m)

print("\n=== 2. OWNER + PIN ===")
for o in User.objects.filter(role="owner").order_by("id"):
    try:
        p = o.pin
        print(repr(o.username), "| attempts:", p.attempts, "| locked:", p.is_locked,
              "| 1234 works:", check_password("1234", p.pin_hash))
    except Exception as e:
        print(repr(o.username), "| PIN ERROR:", repr(e))

print("\n=== 3. OwnerPIN MODEL CODE ===")
print(inspect.getsource(OwnerPIN))

print("\n=== 4. USERS ===")
for u in User.objects.all().order_by("id"):
    print(repr(u.username), "| role:", u.role, "| active:", u.is_active)

print("\n=== 5. SIMULATED FORGOT-PASSWORD (rolled back) ===")
class Rollback(Exception):
    pass

NEW = "TestPass#2026x"
c = Client(HTTP_HOST="127.0.0.1")
try:
    with transaction.atomic():
        r = c.post("/forgot-password/", {
            "username": "koah", "pin": "1234",
            "new_password": NEW, "confirm_password": NEW,
        })
        print("HTTP status:", r.status_code, "(302 = success, 200 = rejected)")
        if r.status_code == 200:
            m = re.search(r'class="error">(.*?)</div>', r.content.decode(), re.S)
            print("Error on page:", m.group(1).strip() if m else "none found")
        print("Login works with new password:", authenticate(username="koah", password=NEW))
        raise Rollback
except Rollback:
    print("(rolled back, nothing was changed)")
