@echo off
cd /d "%~dp0"
echo === Workflow Planner update ===
echo Keeps: .env  data\  uploads\
echo.

if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat

git remote set-url origin https://github.com/0xhannn/workflow-planner-app.git
git fetch origin --tags --prune
if errorlevel 1 (
  echo FAIL: git fetch. Check internet / GitHub.
  pause
  exit /b 1
)

git checkout -B main origin/main
if errorlevel 1 git reset --hard origin/main
if errorlevel 1 (
  echo FAIL: git sync.
  pause
  exit /b 1
)

pip install -r requirements.txt
echo.
echo Done. Run start.bat then Ctrl+F5 in browser.
pause
