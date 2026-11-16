@echo off
cd /d "%~dp0"
if exist secret.bat call secret.bat
set DJANGO_DEBUG=0
if exist venv\Scripts\python.exe (set PY=venv\Scripts\python.exe) else (set PY=python)
%PY% -m waitress --listen=127.0.0.1:8000 ericus.wsgi:application
