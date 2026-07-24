@echo off
cd /d "%~dp0"
echo === Workflow Planner install ===
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found. Install Python 3.11+ and tick "Add to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Install OK. Double-click start.bat
pause
