"""
apply_update.py - run on the SHOP PC. Puts a new update zip into the program.
The database, product photos and passwords are never touched.
"""
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
INCOMING = os.path.join(ROOT, "incoming")
APPLIED = os.path.join(ROOT, "applied")
SERVICE = "EricusPOS"
PROTECTED = ("db.sqlite3", "secret.bat")
PROTECTED_DIRS = ("media/", "backups/", "venv/", "staticfiles/")

PY = os.path.join(ROOT, "venv", "Scripts", "python.exe")
if not os.path.exists(PY):
    PY = sys.executable


def run(args, quiet=False):
    try:
        r = subprocess.run(args, cwd=ROOT)
        return r.returncode == 0
    except FileNotFoundError:
        if not quiet:
            print("  (not found: %s)" % args[0])
        return False


def file_hash(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


os.makedirs(INCOMING, exist_ok=True)
os.makedirs(APPLIED, exist_ok=True)

if len(sys.argv) > 1:
    zip_path = sys.argv[1]
else:
    found = sorted(glob.glob(os.path.join(INCOMING, "update_*.zip")))
    zip_path = found[-1] if found else None

if not zip_path or not os.path.exists(zip_path):
    sys.exit("No update file found. Put the update_*.zip file in the 'incoming' folder and run this again.")

print("Update file:", os.path.basename(zip_path))

print("\n1/6  Saving a backup of the shop data ...")
if not run([PY, "backup_db.py"]):
    sys.exit("Backup failed, so nothing was changed. Tell your developer.")

print("\n2/6  Stopping the POS ...")
run(["nssm", "stop", SERVICE], quiet=True)

print("\n3/6  Putting in the new program files ...")
req_before = file_hash(os.path.join(ROOT, "requirements.txt"))
count = 0
with zipfile.ZipFile(zip_path) as z:
    for member in z.namelist():
        name = member.replace("\\", "/")
        if name.endswith("/") or name == "UPDATE_INFO.txt":
            continue
        if os.path.basename(name) in PROTECTED or name.startswith(PROTECTED_DIRS):
            continue
        target = os.path.join(ROOT, *name.split("/"))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with z.open(member) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst)
        count += 1
print("     %d files updated." % count)

req_after = file_hash(os.path.join(ROOT, "requirements.txt"))
pip_ok = True
if req_before != req_after:
    print("\n4/6  New programs are needed - installing them ...")
    offline = os.path.join(ROOT, "offline_packages")
    if os.path.isdir(offline):
        pip_ok = run([PY, "-m", "pip", "install", "--no-index", "--find-links", offline, "-r", "requirements.txt"])
    else:
        pip_ok = run([PY, "-m", "pip", "install", "-r", "requirements.txt"])
    if not pip_ok:
        print("     WARNING: the new programs could not be installed.")
        print("     (Offline PC: the 'offline_packages' folder must come with the update.)")
else:
    print("\n4/6  No new programs needed.")

print("\n5/6  Updating the database and pages ...")
ok1 = run([PY, "manage.py", "migrate", "--noinput"])
ok2 = run([PY, "manage.py", "collectstatic", "--noinput"])

print("\n6/6  Starting the POS ...")
run(["nssm", "start", SERVICE], quiet=True)

shutil.move(zip_path, os.path.join(APPLIED, os.path.basename(zip_path)))
print("")
if ok1 and ok2 and pip_ok:
    print("DONE. The update is in. If the POS was open in Chrome, press F5 to refresh.")
else:
    print("The update was copied but a step reported a problem (see above). Tell your developer.")
    print("Your data is safe: a backup is in the 'backups' folder.")
