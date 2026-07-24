# Install — Windows (detail)

## Requirements
- Python 3.11+ (Add to PATH)
- Git for Windows

## One-time setup

```powershell
git clone https://github.com/0xhannn/workflow-planner-app.git
cd workflow-planner-app
```

### A) Easy
Double-click **`install.bat`**

### B) Manual

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

`.env` (default already good):

```
WORKFLOW_PIN=0000
PORT=8080
WORKFLOW_STARTER=1
```

## Start app

| File | What |
|------|------|
| `start.bat` | open browser + run server |
| `start-hidden.vbs` | run without console window |
| `update.bat` | pull latest from GitHub + pip |

Open http://127.0.0.1:8080 · PIN `0000`

## Update when banner missing

```powershell
git remote set-url origin https://github.com/0xhannn/workflow-planner-app.git
git fetch origin --tags --prune
git checkout -B main origin/main
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Then restart app + **Ctrl+F5**.

## Data locations (local only)

| Path | Content |
|------|---------|
| `data/shoes.db` | app database |
| `uploads/` | product / task files |
| `uploads/brand/` | custom logo |
| `.env` | PIN + config |

None of these are committed to Git.

## Brand
Admin → pencil on header → name/logo.

## Update (recommended — same idea as 9router)

When the green banner appears:

1. Click **Copy command & stop app**
2. App process exits
3. Paste in PowerShell/CMD **in the app folder** (usually `update.bat`)
4. Wait for **UPDATE OK**
5. Double-click **start.bat** → Ctrl+F5

Or skip the banner: double-click `update.bat` anytime.

