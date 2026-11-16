@echo off
cd /d "%~dp0"
start "Ericus POS Server" /min cmd /c start_pos.bat
timeout /t 4 >nul
start "" http://127.0.0.1:8000/
