# Workflow Planner

Empty **local** install of Workflow Planner (design pipeline, tasks, product gallery, team poll).

- No production database
- No secrets / cloud keys
- Uploads stay on your machine under `uploads/`
- Default brand: **Workflow Planner** (rename/logo in-app as admin)

## Changelog

### v1.0.3
- **Update flow like 9router**: banner shows command → **Copy command & stop app** → paste in terminal → `start.bat`
- Avoids Windows file-lock when updating while Python is running


### v1.0.2
- One-click update **restarts** the app so version/footer refresh (no stuck SHA)
- Footer/API version re-reads git live
- `start.bat` auto-relaunches after update


### v1.0.1
- Custom Workflow Planner favicon / PWA icons
- Admin PIN session fix (stable secret, single middleware)
- One-click update: sync GitHub main + pip (keeps `.env` + `data/`)
- Install: `install.bat` → `start.bat` → `update.bat`

## Install (Windows)

1. Install [Python 3.11+](https://www.python.org/downloads/) — tick **Add Python to PATH**
2. Install [Git](https://git-scm.com/download/win)
3. PowerShell:

```
git clone https://github.com/0xhannn/workflow-planner-app.git
cd workflow-planner-app
```

Then double-click **install.bat**

(or: python -m venv .venv → activate → pip install -r requirements.txt → copy .env.example .env)

## Run

| File | What |
|------|------|
| start.bat | open browser + server |
| start-hidden.vbs | no black console |
| update.bat | sync latest from GitHub + pip |

- URL: http://127.0.0.1:8080
- PIN: 0000 (.env → WORKFLOW_PIN)

## Update

Green **Update** banner appears only when your folder is behind GitHub.

If no banner (rename / history rewrite):

1. Double-click **update.bat**
2. Restart start.bat
3. Browser Ctrl+F5

Keeps .env, data/, uploads/.

## Mac / Linux

```
git clone https://github.com/0xhannn/workflow-planner-app.git
cd workflow-planner-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## What this is not

| | |
|--|--|
| Production / live company data | private deploy only |
| Cloudflare R2 credentials | not included |
| Auto-sync from private server | never |

## Brand

Admin ON → pencil on header → change name / logo.
Default: **Workflow Planner**, no logo.

More detail: SETUP-WINDOWS.md

## Admin mode

1. Open http://127.0.0.1:8080/pin
2. PIN default: **0000** (from `.env` → `WORKFLOW_PIN`)
3. After login you can edit brand, tasks, gallery, poll admin

If PIN always fails after restart: app mints a stable `.session_secret` automatically — just try again once.

