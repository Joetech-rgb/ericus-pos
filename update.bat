@echo off
cd /d "%~dp0"
if exist venv\Scripts\python.exe (set PY=venv\Scripts\python.exe) else (set PY=python)
echo === 1/5 Backup database ===
%PY% backup_db.py
echo === 2/5 Download update ===
git pull
if errorlevel 1 (echo UPDATE FAILED at git pull. Nothing was changed. & pause & exit /b 1)
echo === 3/5 Install packages ===
%PY% -m pip install -r requirements.txt
echo === 4/5 Database + static files ===
%PY% manage.py migrate --noinput
%PY% manage.py collectstatic --noinput
echo === 5/5 Restart POS ===
nssm restart EricusPOS
echo.
echo Update finished. Latest backup is in the backups folder.
pause
