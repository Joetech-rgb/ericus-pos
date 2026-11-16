"""
make_update.py - run on YOUR PC. Builds one zip file with all the program changes.
The shop's data (sales, products, photos, passwords) is never put in the zip.
"""
import datetime
import fnmatch
import os
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SKIP_DIRS = {"venv", ".venv", ".git", "media", "backups", "updates", "incoming", "applied",
             "staticfiles", "__pycache__", "ericus_update", "offline_packages", "node_modules"}
SKIP_FILES = ("db.sqlite3", "*.sqlite3", "secret.bat", "*.pyc", "*.bak*", "*.log",
              "bundle*.txt", "more*.txt", "pages*.txt", "structure.txt",
              "import_products.py", "hide_demo.py", "fix_shop.py", "check_stock.py")

stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
os.makedirs(os.path.join(ROOT, "updates"), exist_ok=True)
out = os.path.join(ROOT, "updates", "update_%s.zip" % stamp)

count = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if any(fnmatch.fnmatch(name, p) for p in SKIP_FILES):
                continue
            full = os.path.join(dirpath, name)
            z.write(full, os.path.relpath(full, ROOT))
            count += 1
    z.writestr("UPDATE_INFO.txt", "Update built %s\n" % datetime.datetime.now().isoformat(timespec="seconds"))

print("")
print("Update file ready: %s" % out)
print("It holds %d program files (no shop data)." % count)
print("Copy it to a flash drive, then to the shop PC folder 'incoming', and run apply_update.bat there.")
