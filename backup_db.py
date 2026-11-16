import sqlite3, os, glob, datetime
os.chdir(os.path.dirname(os.path.abspath(__file__)))
os.makedirs('backups', exist_ok=True)
dst = 'backups/db_%s.sqlite3' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
src = sqlite3.connect('db.sqlite3')
out = sqlite3.connect(dst)
src.backup(out)
out.close(); src.close()
for old in sorted(glob.glob('backups/db_*.sqlite3'))[:-30]:
    os.remove(old)
print('Backup saved:', dst)
