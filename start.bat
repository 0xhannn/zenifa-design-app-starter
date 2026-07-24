@echo off
cd /d "%~dp0"
if not exist .venv (
  echo Run install.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if not exist .env copy .env.example .env
start "" http://127.0.0.1:8080
python main.py
pause
