@echo off
set DJANGO_SECRET_KEY=n1%_#rx-)7x3#e(&dyxmqyuyg$^t*2*hloe4t+px651+l*od3n
set DJANGO_DEBUG=0
call venv\Scripts\activate.bat
waitress-serve --host=0.0.0.0 --port=8000 ericus.wsgi:application
pause
