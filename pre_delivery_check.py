import os, sys, subprocess
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ericus.settings")
CHECKS = []
def check(label, fn):
    try:
        ok, msg = fn()
        CHECKS.append((ok, label, msg))
    except Exception as e:
        CHECKS.append((False, label, str(e)))
def django_check():
    result = subprocess.run([sys.executable, "manage.py", "check"], capture_output=True, text=True)
    errors = [l for l in result.stdout.splitlines() if "ERROR" in l]
    return (len(errors) == 0), (result.stdout.strip()[:200] if result.stdout.strip() else "OK")
def migrations_check():
    result = subprocess.run([sys.executable, "manage.py", "showmigrations", "--list"], capture_output=True, text=True)
    unapplied = [l for l in result.stdout.splitlines() if "[ ]" in l]
    return (len(unapplied) == 0), (f"{len(unapplied)} unapplied" if unapplied else "All applied")
def static_check():
    import django; django.setup()
    from django.conf import settings
    sf = settings.STATIC_ROOT
    exists = os.path.isdir(sf) and len(os.listdir(sf)) > 0
    return exists, ("staticfiles/ present" if exists else "Run: python manage.py collectstatic")
def db_check():
    import django; django.setup()
    from accounts.models import User
    owner_exists = User.objects.filter(role="owner").exists()
    count = User.objects.count()
    return owner_exists, (f"{count} users, owner exists" if owner_exists else "NO OWNER found")
def whitenoise_check():
    try:
        import whitenoise
        return True, "whitenoise installed OK"
    except ImportError:
        return False, "Not installed -- run: pip install whitenoise"
def sqlite_check():
    exists = os.path.isfile("db.sqlite3")
    size = os.path.getsize("db.sqlite3") if exists else 0
    return exists, (f"db.sqlite3 ({size/1024:.1f} KB)" if exists else "MISSING")
check("Django system checks", django_check)
check("Unapplied migrations", migrations_check)
check("Static files collected", static_check)
check("Database and owner account", db_check)
check("WhiteNoise installed", whitenoise_check)
check("SQLite database file", sqlite_check)
print()
print("-- Pre-delivery checks --------------------------------------")
all_ok = True
for ok, label, msg in CHECKS:
    icon = "PASS" if ok else "FAIL"
    print(f"  [{icon}]  {label:<35} {msg}")
    if not ok:
        all_ok = False
print("-------------------------------------------------------------")
print("  All checks passed. Ready to deliver." if all_ok else "  Fix the FAIL items above before handing over.")
print()
