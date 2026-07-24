import os
import re
import subprocess
import json
import sqlite3
import uuid
import mimetypes
from uuid import uuid4
import httpx
from datetime import datetime
from io import BytesIO
from pathlib import Path
from werkzeug.utils import secure_filename

from fastapi import FastAPI, Request, Form, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except Exception:
    pass

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

_R2_CLIENT = None
def _r2():
    global _R2_CLIENT
    if _R2_CLIENT is None:
        _R2_CLIENT = boto3.client(
            's3',
            endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
            aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'],
            config=Config(signature_version='s3v4'),
            region_name='auto',
        )
    return _R2_CLIENT
def _resolve_db_path() -> str:
    """DB path: env DB_PATH / WORKFLOW_DB_PATH → ./data/shoes.db (local starter)."""
    env = (os.environ.get('DB_PATH') or os.environ.get('WORKFLOW_DB_PATH') or '').strip()
    if env:
        return env
    return str(Path(__file__).parent / 'data' / 'shoes.db')

def _is_staging_env() -> bool:
    """True only for DEV/staging — NOT merely because prod sets DB_PATH off-tree."""
    if str(os.environ.get('PORT') or '') == '3888':
        return True
    if str(os.environ.get('HERMES_DEV') or '').lower() in ('1', 'true', 'yes'):
        return True
    if str(os.environ.get('NODE_ENV') or '').lower() in ('staging', 'development', 'dev'):
        return True
    try:
        cwd = str(Path(__file__).resolve().parent)
        if '/app-dev/' in cwd or cwd.startswith('/app-dev'):
            return True
    except Exception:
        pass
    p = (os.environ.get('DB_PATH') or os.environ.get('WORKFLOW_DB_PATH') or '').strip()
    if 'data-staging' in p or '/staging/' in p:
        return True
    return False

def _get_task_by_id(task_id: int):
    """Get single task by ID."""
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None

def _get_products():
    """Get all products from DB."""
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, name FROM products ORDER BY name")
    products = [dict(row) for row in c.fetchall()]
    conn.close()
    return products

def _get_product_by_id(product_id):
    """Get single product by ID."""
    conn = sqlite3.connect(_resolve_db_path())
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, name FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None




def _r2_prefix() -> str:
    """Return R2 key prefix from env, always ends without trailing slash."""
    return os.environ.get('R2_PREFIX', '').strip('/') + '/' if os.environ.get('R2_PREFIX') else ''

def _cdn_key(url: str) -> str | None:
    """Extract R2 key from CDN URL. Returns key WITHOUT base, WITH prefix.
    e.g. https://cdn.example/prefix/tasks/foo.pdf → prefix/tasks/foo.pdf
    Returns None if not a CDN URL or unsafe.
    """
    base = os.environ.get('R2_PUBLIC_BASE', '').rstrip('/')
    if not base or not url.startswith(base + '/'):
        return None
    key = url[len(base) + 1:]  # strip base/
    if not key or '..' in key:
        return None
    return key

def _upload_pdf_to_r2(file: UploadFile) -> str:
    """Stream PDF upload to R2 under R2_PREFIX, return public CDN URL."""
    prefix = _r2_prefix()
    name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + '.pdf'
    r2_key = prefix + 'tasks/' + name
    _r2().upload_fileobj(
        file.file,
        os.environ['R2_BUCKET'],
        r2_key,
        ExtraArgs={'ContentType': 'application/pdf', 'ContentDisposition': 'inline'},
    )
    return f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{r2_key}"

def _upload_image_to_r2(local_path: str) -> str | None:
    """
    Upload already-compressed image file to R2 under R2_PREFIX, return CDN URL.
    Compress happens first (in-place), then upload, then local file is KEPT
    (not deleted) so StaticFiles can still serve it as fallback.
    Returns CDN URL or None on failure.
    """
    bucket = os.environ.get('R2_BUCKET')
    if not bucket:
        return None
    compressed = _compress_image(local_path)
    if not compressed:
        return None
    path_to_upload = compressed
    name = os.path.basename(path_to_upload)
    prefix = _r2_prefix()
    r2_key = prefix + 'tasks/' + name
    try:
        with open(path_to_upload, 'rb') as fh:
            _r2().upload_fileobj(
                fh,
                bucket,
                r2_key,
                ExtraArgs={'ContentType': 'image/webp', 'CacheControl': 'max-age=31536000'},
            )
        return f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{r2_key}"
    except Exception as e:
        print(f'Image R2 upload failed ({path_to_upload}): {e}')
        return None

def _upload_generic_to_r2(local_path: str, content_type: str) -> str | None:
    """Upload any file to R2 under R2_PREFIX, return CDN URL."""
    bucket = os.environ.get('R2_BUCKET')
    if not bucket:
        return None
    prefix = _r2_prefix()
    name = os.path.basename(local_path)
    r2_key = prefix + 'tasks/' + name
    try:
        with open(local_path, 'rb') as fh:
            _r2().upload_fileobj(
                fh,
                bucket,
                r2_key,
                ExtraArgs={'ContentType': content_type, 'CacheControl': 'max-age=31536000'},
            )
        return f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{r2_key}"
    except Exception as e:
        print(f'Generic R2 upload failed ({local_path}): {e}')
        return None


def _extract_remote_pdfs(urls: list[str]) -> list[str]:
    """Filter list to R2-hosted PDF URLs only."""
    base = os.environ.get('R2_PUBLIC_BASE', '').rstrip('/')
    if not base:
        return []
    return [u for u in (urls or []) if isinstance(u, str) and u.startswith(base + '/') and u.lower().endswith('.pdf')]

def _delete_r2_objects(urls: list[str]):
    """Best-effort batch delete of R2 objects by public URL. Silently no-ops if R2 not configured."""
    if not urls:
        return
    bucket = os.environ.get('R2_BUCKET')
    if not bucket:
        return
    objects = []
    for url in urls:
        key = _cdn_key(url)
        if not key:
            continue
        objects.append({'Key': key})
    if not objects:
        return
    try:
        _r2().delete_objects(Bucket=bucket, Delete={'Objects': objects, 'Quiet': True})
    except Exception as e:
        print('R2 delete failed:', e)


def _delete_removed_files(old_urls: list[str], new_urls: list[str]):
    """Diff old vs new: delete anything in old but not in new from R2 (URL) or local fs."""
    new_set = set(new_urls or [])
    removed = [u for u in (old_urls or []) if u and u not in new_set]
    if not removed:
        return
    # 1. R2 URLs → batch delete
    r2_urls = [u for u in removed if u.startswith('http://') or u.startswith('https://')]
    if r2_urls:
        try:
            _delete_r2_objects(r2_urls)
        except Exception as e:
            print('R2 delete error:', e)
    # 2. Local paths (relative like uploads/tasks/xxx.webp) → unlink
    for u in removed:
        if u.startswith(('http://', 'https://')):
            continue
        # Strip leading slash, resolve to absolute
        rel = u.lstrip('/')
        if not rel or rel.startswith('static/') or '..' in rel:
            continue
        full = os.path.join(BASE_DIR, rel)
        try:
            if os.path.isfile(full):
                os.remove(full)
                print(f'Deleted local file: {full}')
        except Exception as e:
            print(f'Local delete failed for {u}: {e}')

def _compress_image(file_path: str, max_width: int = 1200, quality: int = 72):
    """In-place: resize + convert to .webp. Fast encode (method=4). Skip if already small webp/jpeg."""
    try:
        from PIL import Image
        if not os.path.exists(file_path):
            return None
        # Fast-path: already small compressed image — don't re-encode (saves 1–3s on mobile uploads)
        ext = os.path.splitext(file_path)[1].lower()
        try:
            size = os.path.getsize(file_path)
        except OSError:
            size = 0
        if ext in ('.webp', '.jpg', '.jpeg') and 0 < size <= 380_000:
            return file_path

        img = Image.open(file_path)
        if img.format not in ('JPEG', 'PNG', 'WEBP', 'GIF'):
            return None
        # EXIF orientation so phone photos aren't sideways after compress
        try:
            from PIL import ImageOps
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.BILINEAR)
        base, _ = os.path.splitext(file_path)
        new_path = base + '.webp'
        # method=4 is ~3-5x faster than method=6 with tiny quality delta
        if img.mode in ('RGBA', 'LA', 'P'):
            img.save(new_path, 'WEBP', quality=quality, method=4)
        else:
            img.convert('RGB').save(new_path, 'WEBP', quality=quality, method=4)
        if os.path.abspath(new_path) != os.path.abspath(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        return new_path
    except Exception as e:
        print(f'compress_image failed for {file_path}:', e)
        return None


async def _save_upload_stream(upload: UploadFile, abs_path: str, chunk_size: int = 64 * 1024) -> int:
    """Stream UploadFile to disk in chunks (avoids giant in-memory buffers on tunnel uploads)."""
    total = 0
    with open(abs_path, 'wb') as buffer:
        while True:
            chunk = await upload.read(chunk_size)
            if not chunk:
                break
            buffer.write(chunk)
            total += len(chunk)
    return total


def _store_design_image_local(abs_path: str) -> str:
    """Compress (or skip) and return local uploads/ relative path. Fast — no R2 wait."""
    compressed = _compress_image(abs_path)
    path_to_use = compressed or abs_path
    return 'uploads/' + os.path.basename(path_to_use)


def _promote_design_image_r2(design_id: int, local_rel: str, old_path: str | None = None) -> None:
    """
    Background: upload local design image to R2, patch DB to CDN URL, cleanup old.
    Called after HTTP response so tunnel upload feels instant.
    """
    try:
        abs_path = os.path.join(BASE_DIR, local_rel.lstrip('/'))
        if not os.path.isfile(abs_path):
            print(f'promote r2 skip missing {abs_path}')
            return
        bucket = os.environ.get('R2_BUCKET')
        if not bucket:
            return
        name = os.path.basename(abs_path)
        prefix = _r2_prefix()
        r2_key = prefix + name
        with open(abs_path, 'rb') as fh:
            _r2().upload_fileobj(
                fh,
                bucket,
                r2_key,
                ExtraArgs={
                    'ContentType': 'image/webp' if abs_path.endswith('.webp') else (
                        'image/jpeg' if abs_path.lower().endswith(('.jpg', '.jpeg')) else 'application/octet-stream'
                    ),
                    'CacheControl': 'max-age=31536000',
                },
            )
        cdn_url = f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{r2_key}"
        conn = get_db()
        # Only overwrite if still pointing at this local file (user may have re-uploaded)
        row = conn.execute('SELECT image_path FROM designs WHERE id = ?', (design_id,)).fetchone()
        if row and row['image_path'] == local_rel:
            conn.execute('UPDATE designs SET image_path = ? WHERE id = ?', (cdn_url, design_id))
            conn.commit()
            print(f'promote r2 ok design#{design_id} → {cdn_url}')
        conn.close()
        if old_path and old_path not in (local_rel, cdn_url):
            try:
                if str(old_path).startswith(os.environ.get('R2_PUBLIC_BASE', '___')):
                    _delete_r2_objects([old_path])
                else:
                    old_local = os.path.join(BASE_DIR, str(old_path).lstrip('/'))
                    if os.path.isfile(old_local):
                        os.remove(old_local)
            except Exception as e:
                print(f'old image cleanup failed: {e}')
    except Exception as e:
        print(f'promote r2 fail design#{design_id}: {e}')


def _store_design_image(abs_path: str) -> str:
    """
    Compress + best-effort R2 for product/design images (sync path — prefer local+bg promote).
    Returns CDN URL when R2 works, else local uploads/ relative path.
    """
    compressed = _compress_image(abs_path)
    path_to_use = compressed or abs_path
    local_rel = 'uploads/' + os.path.basename(path_to_use)

    bucket = os.environ.get('R2_BUCKET')
    if not bucket:
        return local_rel

    name = os.path.basename(path_to_use)
    prefix = _r2_prefix()
    r2_key = prefix + name
    try:
        with open(path_to_use, 'rb') as fh:
            _r2().upload_fileobj(
                fh,
                bucket,
                r2_key,
                ExtraArgs={'ContentType': 'image/webp' if path_to_use.endswith('.webp') else 'application/octet-stream',
                           'CacheControl': 'max-age=31536000'},
            )
        return f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{r2_key}"
    except Exception as e:
        print(f'Design image R2 upload failed ({path_to_use}): {e}')
        return local_rel

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

app = FastAPI(
    # Increase max upload size to 50MB
    limit_concurrent_tasks=100,
)

from starlette.middleware.sessions import SessionMiddleware
import secrets as _secrets

def _load_session_secret() -> str:
    """Stable session key: env → .session_secret file → mint once (local starter)."""
    for key in ('WORKFLOW_SESSION_SECRET', 'SESSION_SECRET', 'ZENIFA_SESSION_SECRET'):
        v = (os.environ.get(key) or '').strip()
        if v:
            return v
    path = Path(__file__).resolve().parent / '.session_secret'
    try:
        if path.is_file():
            s = path.read_text(encoding='utf-8').strip()
            if s:
                return s
    except Exception:
        pass
    s = _secrets.token_hex(32)
    try:
        path.write_text(s + '\n', encoding='utf-8')
    except Exception:
        pass
    return s

ADMIN_PIN = (os.environ.get('WORKFLOW_PIN') or os.environ.get('PIN') or os.environ.get('ZENIFA_PIN') or '0000')

def _git_version():
    """Read version from `git describe --tags --always`. Returns 'unknown' if not a git repo."""
    try:
        return subprocess.check_output(
            ['git', 'describe', '--tags', '--always', '--dirty'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return 'unknown'

APP_VERSION = _git_version()


def live_app_version() -> str:
    """Always re-read git (footer/API). Module-level APP_VERSION freezes until process restart."""
    try:
        # Prefer local git describe when helpers exist (defined later in file).
        if '_local_git_version' in globals() and callable(globals().get('_local_git_version')):
            return _local_git_version()
        return _git_version()
    except Exception:
        return APP_VERSION



def _welcome_context(request: Request) -> dict:
    """Shared landing data for / and /welcome."""
    conn = get_db()
    featured_designs = conn.execute(
        """
        SELECT id, model_name, status, image_path, created_at
        FROM designs
        WHERE image_path IS NOT NULL AND image_path != ''
        ORDER BY id DESC
        LIMIT 8
        """
    ).fetchall()
    recent_tasks = conn.execute(
        """
        SELECT id, title, category, status, created_at, product_id
        FROM tasks
        ORDER BY id DESC
        LIMIT 6
        """
    ).fetchall()
    counts = {
        "designs": conn.execute("SELECT COUNT(*) AS n FROM designs").fetchone()["n"],
        "tasks": conn.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()["n"],
        "inwork": conn.execute(
            "SELECT COUNT(*) AS n FROM designs WHERE status != 'finish'"
        ).fetchone()["n"],
        "finished": conn.execute(
            "SELECT COUNT(*) AS n FROM designs WHERE status = 'finish'"
        ).fetchone()["n"],
        "proses": conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE status = 'proses'"
        ).fetchone()["n"],
        "draft": conn.execute(
            "SELECT COUNT(*) AS n FROM tasks WHERE status = 'draft'"
        ).fetchone()["n"],
    }
    conn.close()
    return {
        "menu": "welcome",
        "pin_ok": _pin_ok(request),
        "app_version": APP_VERSION,
        "featured_designs": featured_designs,
        "recent_tasks": recent_tasks,
        "welcome_counts": counts,
    }


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context=_welcome_context(request)
    )


@app.get("/__health__", include_in_schema=False)
def __health__():
    return {"status": "ok", "version": live_app_version(), "ts": datetime.utcnow().isoformat() + "Z"}

# ── VERSION & DEPLOY (prod deploy.js OR local starter git pull) ──
# LOCAL/STARTER (Windows/laptop) → one-click git pull + pip (9router-style)

def _app_root() -> Path:
    return Path(__file__).resolve().parent


def _is_local_starter() -> bool:
    """True on laptop/starter: no VPS deploy.js, or explicit flag."""
    if (os.environ.get('WORKFLOW_LOCAL_UPDATE') or '').strip().lower() in ('1', 'true', 'yes'):
        return True
    if (os.environ.get('WORKFLOW_STARTER') or '').strip().lower() in ('1', 'true', 'yes'):
        return True
    if not Path('/root/deploy.js').exists():
        return True
    if os.name == 'nt':
        return True
    cwd = _app_root().as_posix()
    if 'workflow-planner-app' in cwd:
        return True
    return False


def _git_cmd(args, cwd=None, timeout=120):
    return subprocess.run(
        ['git'] + list(args),
        cwd=str(cwd or _app_root()),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _local_git_version() -> str:
    try:
        r = _git_cmd(['describe', '--tags', '--always', '--dirty'])
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        r = _git_cmd(['rev-parse', '--short', 'HEAD'])
        return r.stdout.strip() if r.returncode == 0 else 'local'
    except Exception:
        return 'local'


def _starter_public_url() -> str:
    """Public starter remote — works without auth (orphan re-exports)."""
    try:
        r = _git_cmd(['remote', 'get-url', 'origin'])
        url = (r.stdout or '').strip() if r.returncode == 0 else ''
        if url and 'workflow-planner-app' in url:
            return url
    except Exception:
        pass
    return 'https://github.com/0xhannn/workflow-planner-app.git'


def _sha_equal(a: str, b: str) -> bool:
    if not a or not b:
        return False
    a, b = a.strip().lower(), b.strip().lower()
    if a == b:
        return True
    # short vs full
    return a.startswith(b) or b.startswith(a)


def _local_remote_head() -> str:
    """Resolve GitHub main SHA. Prefer ls-remote (no stale origin/*)."""
    url = _starter_public_url()
    for ref in ('refs/heads/main', 'HEAD', 'refs/heads/master'):
        try:
            r = _git_cmd(['ls-remote', url, ref], timeout=45)
            if r.returncode == 0 and r.stdout.strip():
                sha = r.stdout.strip().split()[0]
                if re.fullmatch(r'[0-9a-f]{7,40}', sha):
                    return sha
        except Exception:
            continue
    try:
        _git_cmd(['fetch', 'origin', '--tags', '--prune', '--quiet'], timeout=90)
    except Exception:
        pass
    for ref in ('origin/main', 'origin/master'):
        try:
            r = _git_cmd(['rev-parse', ref])
            if r.returncode == 0 and r.stdout.strip():
                return r.stdout.strip()
        except Exception:
            continue
    return ''


def _local_current_head() -> str:
    try:
        r = _git_cmd(['rev-parse', 'HEAD'])
        return r.stdout.strip() if r.returncode == 0 else ''
    except Exception:
        return ''



def _local_update_command() -> str:
    """Command user pastes after stopping the app (9router-style)."""
    if os.name == 'nt':
        return 'update.bat'
    return (
        'git remote set-url origin https://github.com/0xhannn/workflow-planner-app.git && '
        'git fetch origin --tags --prune && '
        'git checkout -B main origin/main && '
        'pip install -r requirements.txt'
    )


def _local_version_payload(can_deploy: bool = True) -> dict:
    cur = _local_git_version()
    cur_sha = _local_current_head()
    rem_sha = _local_remote_head()
    has = bool(cur_sha and rem_sha and not _sha_equal(cur_sha, rem_sha))
    latest_label = (rem_sha[:7] if rem_sha else cur)
    try:
        if rem_sha:
            r = _git_cmd(['describe', '--tags', '--always', rem_sha])
            if r.returncode == 0 and r.stdout.strip():
                latest_label = r.stdout.strip()
            else:
                latest_label = rem_sha[:7]
    except Exception:
        pass
    return {
        'version': cur,
        'app': 'workflow-planner-app',
        'currentVersion': cur,
        'latestVersion': latest_label if has else cur,
        'hasUpdate': has,
        'canDeploy': bool(can_deploy),
        'isDev': True,
        'isLocal': True,
        'channel': 'local',
        'releasesUrl': 'https://github.com/0xhannn/workflow-planner-app',
        'updateHint': 'Copy command, stop app, paste in terminal, then start.bat',
        'updateCommand': _local_update_command(),
        'updateCommandWin': 'update.bat',
        'updateCommandPosix': ('git remote set-url origin https://github.com/0xhannn/workflow-planner-app.git && ' 'git fetch origin --tags --prune && ' 'git checkout -B main origin/main && ' 'pip install -r requirements.txt'),
        'updateStyle': 'copy-stop',
        'currentSha': (cur_sha or '')[:12],
        'latestSha': (rem_sha or '')[:12],
    }


def _version_util():
    """VPS helper; may be missing on laptop."""
    import importlib.util
    p = '/root/scripts/app-update/version_util.py'
    if not os.path.isfile(p):
        return None
    spec = importlib.util.spec_from_file_location('king_version_util', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@app.get("/api/version", include_in_schema=False)
def api_version(request: Request):
    """Current version + update availability (local starter OR prod VPS)."""
    if _is_local_starter():
        return _local_version_payload(can_deploy=True)
    vu = _version_util()
    cwd = os.path.dirname(os.path.abspath(__file__))
    if vu is None:
        return {
            'version': APP_VERSION,
            'app': 'workflow-planner-app',
            'currentVersion': APP_VERSION,
            'latestVersion': APP_VERSION,
            'hasUpdate': False,
            'canDeploy': _pin_ok(request),
            'isDev': False,
            'channel': 'official',
        }
    ver = vu.git_describe(cwd)
    return vu.version_payload(
        cwd,
        'workflow-planner-app',
        can_deploy=_pin_ok(request),
        version=ver,
    )


@app.post("/admin/deploy", include_in_schema=False)
async def admin_deploy(request: Request):
    """PROD: deploy.js. LOCAL starter: git pull + pip (9router-style one-click)."""
    if _is_local_starter():
        root = _app_root()
        logs = []
        try:
            # Orphan re-exports cannot always ff-only pull — hard-sync to GitHub main.
            # .env / data/ / uploads/ stay (gitignored, untracked).
            url = _starter_public_url()
            cmds = [
                ['git', 'remote', 'set-url', 'origin', url],
                ['git', 'fetch', 'origin', '--tags', '--prune'],
            ]
            for cmd in cmds:
                r = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True, timeout=120)
                logs.append('$ ' + ' '.join(cmd) + '\n' + (r.stdout or '') + '\n' + (r.stderr or ''))
                if r.returncode != 0 and cmd[1] == 'fetch':
                    return JSONResponse({
                        'status': 'error',
                        'error': ((r.stderr or r.stdout or 'git fetch failed')).strip()[:500],
                        'stdout': '\n'.join(logs)[-2000:],
                        'version': _local_git_version(),
                    }, status_code=500)

            branch = 'main'
            # detect remote default
            for cand in ('main', 'master'):
                r = subprocess.run(
                    ['git', 'rev-parse', '--verify', f'origin/{cand}'],
                    cwd=str(root), capture_output=True, text=True, timeout=30,
                )
                if r.returncode == 0:
                    branch = cand
                    break

            # Prefer reset --hard (works after force-push orphan history)
            r = subprocess.run(
                ['git', 'checkout', '-B', branch, f'origin/{branch}'],
                cwd=str(root), capture_output=True, text=True, timeout=120,
            )
            logs.append('$ git checkout -B ' + branch + ' origin/' + branch + '\n' + (r.stdout or '') + '\n' + (r.stderr or ''))
            if r.returncode != 0:
                r = subprocess.run(
                    ['git', 'reset', '--hard', f'origin/{branch}'],
                    cwd=str(root), capture_output=True, text=True, timeout=120,
                )
                logs.append('$ git reset --hard origin/' + branch + '\n' + (r.stdout or '') + '\n' + (r.stderr or ''))
                if r.returncode != 0:
                    return JSONResponse({
                        'status': 'error',
                        'error': ((r.stderr or 'git sync failed — run: git fetch && git reset --hard origin/main')).strip()[:500],
                        'stdout': '\n'.join(logs)[-2000:],
                        'version': _local_git_version(),
                    }, status_code=500)

            venv = os.environ.get('VIRTUAL_ENV')
            pip_cmd = None
            if venv:
                cand = Path(venv) / ('Scripts' if os.name == 'nt' else 'bin') / ('pip.exe' if os.name == 'nt' else 'pip')
                if cand.exists():
                    pip_cmd = [str(cand), 'install', '-r', 'requirements.txt']
            if not pip_cmd:
                pip_cmd = [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt']
            r = subprocess.run(pip_cmd, cwd=str(root), capture_output=True, text=True, timeout=300)
            logs.append('$ ' + ' '.join(pip_cmd) + '\n' + (r.stdout or '') + '\n' + (r.stderr or ''))
            if r.returncode != 0:
                return JSONResponse({
                    'status': 'error',
                    'error': ((r.stderr or 'pip install failed')).strip()[:500],
                    'stdout': '\n'.join(logs)[-2000:],
                    'version': _local_git_version(),
                }, status_code=500)

            ver = _local_git_version()
            sha = _local_current_head()
            # Signal start.bat loop to relaunch after this process exits.
            try:
                (_app_root() / '.restart').write_text(ver + '\n', encoding='utf-8')
            except Exception:
                pass
            # Schedule clean exit so Windows can unlock files & start.bat restarts python.
            import threading
            def _exit_soon():
                import time
                time.sleep(1.2)
                try:
                    os._exit(0)
                except Exception:
                    raise SystemExit(0)
            threading.Thread(target=_exit_soon, daemon=True).start()
            return JSONResponse({
                'status': 'ok',
                'message': 'Updated to ' + ver + '. App restarting…',
                'stdout': '\n'.join(logs)[-2000:],
                'version': ver,
                'currentSha': (sha or '')[:12],
                'restartRequired': True,
                'channel': 'local',
            })
        except Exception as e:
            return JSONResponse({'status': 'error', 'error': str(e), 'version': _local_git_version()}, status_code=500)

    if not _pin_ok(request):
        return JSONResponse({"error": "unauthorized", "message": "Login as admin first"}, status_code=401)
    vu = _version_util()
    cwd = os.path.dirname(os.path.abspath(__file__))
    if vu is not None and vu.is_dev_env(cwd):
        return JSONResponse({
            "status": "error",
            "error": "deploy blocked on DEV — release to GitHub, then Update now on prod",
        }, status_code=400)
    try:
        want = 'latest'
        try:
            body = await request.json()
            if isinstance(body, dict) and body.get('version'):
                want = str(body.get('version')).strip() or 'latest'
        except Exception:
            pass
        if not Path('/root/deploy.js').exists():
            return JSONResponse({
                'status': 'error',
                'error': 'deploy.js not found — this build is not on VPS prod',
            }, status_code=400)
        result = subprocess.run(
            ['node', '/root/deploy.js', 'workflow-planner-app', want],
            capture_output=True, text=True, timeout=180,
            cwd='/root',
        )
        ver = vu.git_describe(cwd) if vu else _local_git_version()
        return JSONResponse({
            "status": "ok" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "version": ver,
        })
    except Exception as e:
        return JSONResponse({"status": "error", "error": str(e)}, status_code=500)


# Stable secret required: multi-worker + restarts. Random default only for local one-off.
# Env: WORKFLOW_SESSION_SECRET (set in .env). Without it, each worker/restart mints a new key → admin "randomly" logs out.
SESSION_SECRET=_load_session_secret()
# Admin stays until toggle OFF (/pin/logout). Default 400 days (Starlette max_age seconds).
# Override: WORKFLOW_SESSION_MAX_AGE (seconds).
try:
    _SESSION_MAX_AGE = int(os.environ.get('WORKFLOW_SESSION_MAX_AGE') or str(60 * 60 * 24 * 400))
except ValueError:
    _SESSION_MAX_AGE = 60 * 60 * 24 * 400
if _SESSION_MAX_AGE < 3600:
    _SESSION_MAX_AGE = 3600
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=_SESSION_MAX_AGE,
    same_site='lax',  # strict can drop cookie on some external→app return navigations
    https_only=False,
)

def _pin_ok(request: Request) -> bool:
    return bool(request.session.get('pin_ok'))

def _pin_guard(request: Request):
    # Return RedirectResponse if NOT authed; None if authed. Use for POST mutators.
    if not _pin_ok(request):
        return RedirectResponse(url="/pin", status_code=303)
    return None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_WORK_DIR = os.path.join(BASE_DIR, "pdf_work")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_WORK_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "static"))


_GDRIVE_ID_RE = re.compile(r'^[a-zA-Z0-9_-]{10,}$')

@app.get("/api/gdrive-stream/{file_id}", include_in_schema=False)
async def api_gdrive_stream(file_id: str, request: Request):
    """Same-origin proxy for public GDrive videos.

    Browser <video> sends Origin + Range → Google often 403s. We fetch without
    Origin, forward Range, stream bytes so the custom player (auto-hide chrome)
    works and the sticky Google iframe player is avoided.
    """
    if not _GDRIVE_ID_RE.match(file_id or ''):
        raise HTTPException(status_code=400, detail="invalid file id")
    upstream = f"https://drive.google.com/uc?export=download&id={file_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; WorkflowPlannerGDriveProxy/1.0)",
        "Accept": "*/*",
    }
    rng = request.headers.get("range") or request.headers.get("Range")
    if rng:
        headers["Range"] = rng
    client = httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0))
    try:
        req = client.build_request("GET", upstream, headers=headers)
        resp = await client.send(req, stream=True)
    except Exception as e:
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"upstream error: {e}")

    # Virus-scan / confirm interstitial sometimes returns HTML + cookie
    ct0 = (resp.headers.get("content-type") or "").lower()
    if resp.status_code == 200 and "text/html" in ct0:
        body = await resp.aread()
        await resp.aclose()
        await client.aclose()
        # try confirm token
        m = re.search(rb'confirm=([0-9A-Za-z_]+)', body) or re.search(rb'name="confirm"\s+value="([^"]+)"', body)
        if not m:
            raise HTTPException(status_code=502, detail="gdrive blocked or private")
        confirm = m.group(1).decode("utf-8", "ignore")
        upstream2 = f"https://drive.google.com/uc?export=download&id={file_id}&confirm={confirm}"
        client = httpx.AsyncClient(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0))
        try:
            req = client.build_request("GET", upstream2, headers=headers)
            resp = await client.send(req, stream=True)
        except Exception as e:
            await client.aclose()
            raise HTTPException(status_code=502, detail=f"upstream confirm error: {e}")

    if resp.status_code not in (200, 206):
        await resp.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail=f"upstream status {resp.status_code}")

    ct = resp.headers.get("content-type") or "video/mp4"
    if "text/html" in ct.lower():
        await resp.aclose()
        await client.aclose()
        raise HTTPException(status_code=502, detail="gdrive returned html")

    out_headers = {
        "Accept-Ranges": resp.headers.get("accept-ranges", "bytes"),
        "Cache-Control": "private, max-age=3600",
        "Content-Disposition": "inline",
    }
    for hk in ("content-length", "content-range"):
        if hk in resp.headers:
            out_headers[hk.title() if hk != "content-length" else "Content-Length"] = resp.headers[hk]
            if hk == "content-range":
                out_headers["Content-Range"] = resp.headers[hk]

    async def body_iter():
        try:
            async for chunk in resp.aiter_bytes(chunk_size=64 * 1024):
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return StreamingResponse(
        body_iter(),
        status_code=resp.status_code,
        media_type=ct,
        headers=out_headers,
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")
DATA_DIR = os.path.join(BASE_DIR, "data")
PDF_WORK_DIR = os.path.join(BASE_DIR, "pdf_work")
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_WORK_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "static"))

# ── Brand / header settings (editable per install; stored in DB) ──────────
# Default product branding: text-only "Workflow Planner", no logo.
_DEFAULT_BRAND_NAME = (os.environ.get('WORKFLOW_BRAND_NAME') or 'Workflow Planner').strip() or 'Workflow Planner'
_DEFAULT_BRAND_TAGLINE = (os.environ.get('WORKFLOW_BRAND_TAGLINE') or '').strip()
_DEFAULT_BRAND_LOGO = ''  # empty = no logo in header


def _get_setting(key: str, default: str = '') -> str:
    """Read app_settings. Empty string is valid for brand_tagline / brand_logo."""
    try:
        conn = get_db()
        row = conn.execute('SELECT value FROM app_settings WHERE key = ?', (key,)).fetchone()
        conn.close()
        if row is not None:
            val = '' if row['value'] is None else str(row['value']).strip()
            if key in ('brand_tagline', 'brand_logo'):
                return val  # may be empty on purpose
            if val:
                return val
    except Exception:
        pass
    return default


def _set_setting(key: str, value: str) -> None:
    conn = get_db()
    conn.execute(
        '''INSERT INTO app_settings (key, value, updated_at) VALUES (?,?,?)
           ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at''',
        (key, value, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
    )
    conn.commit()
    conn.close()


def _brand_ctx() -> dict:
    name = _get_setting('brand_name', _DEFAULT_BRAND_NAME) or _DEFAULT_BRAND_NAME
    tagline = _get_setting('brand_tagline', _DEFAULT_BRAND_TAGLINE)
    logo = _get_setting('brand_logo', _DEFAULT_BRAND_LOGO) or ''
    # Only allow local static / uploads brand paths (no open redirect / remote inject)
    if logo and not (logo.startswith('/static/') or logo.startswith('/uploads/brand/')):
        logo = ''
    if logo.startswith('/uploads/'):
        abs_logo = os.path.join(BASE_DIR, logo.lstrip('/').split('?', 1)[0])
        if not os.path.isfile(abs_logo):
            logo = ''
        else:
            try:
                mtime = int(os.path.getmtime(abs_logo))
                logo = f'{logo.split("?", 1)[0]}?v={mtime}'
            except Exception:
                pass
    title = f'{name} {tagline}'.strip() if tagline else name
    return {
        'brand_name': name,
        'brand_tagline': tagline,
        'brand_title': title,
        'brand_logo_url': logo,  # '' = no logo
        'brand_has_logo': bool(logo),
    }


# Inject brand into every template render (no need to touch each route)
_orig_template_response = templates.TemplateResponse


def _template_response_with_brand(*args, **kwargs):
    brand = _brand_ctx()
    try:
        live_ver = live_app_version()
    except Exception:
        live_ver = APP_VERSION

    def _merge(ctx):
        if not isinstance(ctx, dict):
            return ctx
        merged = dict(ctx)
        for k, v in brand.items():
            merged.setdefault(k, v)
        merged['app_version'] = live_ver
        return merged

    ctx = kwargs.get('context')
    if ctx is None and len(args) >= 3 and isinstance(args[2], dict):
        # legacy positional context
        args = list(args)
        args[2] = _merge(args[2])
        return _orig_template_response(*args, **kwargs)
    if isinstance(ctx, dict):
        kwargs = dict(kwargs)
        kwargs['context'] = _merge(ctx)
    return _orig_template_response(*args, **kwargs)


templates.TemplateResponse = _template_response_with_brand


def gdrive_thumbnail(url: str) -> str:
    """Public Drive thumbnail URL for files (image/video/doc). Folders have no thumb API."""
    if not url:
        return ''
    s = str(url)
    m = re.search(r'/folders/([a-zA-Z0-9_-]{10,})', s)
    if m:
        return ''  # no official folder thumbnail
    m = re.search(r'/file/d/([a-zA-Z0-9_-]{10,})', s)
    if not m:
        m = re.search(r'[?&]id=([a-zA-Z0-9_-]{10,})', s)
    if not m:
        m = re.search(r'([a-zA-Z0-9_-]{25,})', s)
    if not m:
        return ''
    file_id = m.group(1)
    return f"https://drive.google.com/thumbnail?sz=w400&id={file_id}"

templates.env.filters['gdrive_thumbnail'] = gdrive_thumbnail

# Force HTML no-cache so latest JS always served; cache static/uploads aggressively
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import FileResponse, Response

class CacheHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resp = await call_next(request)
        path = request.url.path or ''
        ct = resp.headers.get('content-type', '')
        # HTML: always fresh (app shell + Jinja)
        if 'text/html' in ct:
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            resp.headers['Pragma'] = 'no-cache'
            return resp
        # Static assets + uploads: long cache (filenames are content-ish / versioned by deploy)
        if path.startswith('/static/') or path.startswith('/uploads/'):
            # Don't override SW / manifest (short-circuit routes set their own)
            if path.endswith('sw.js') or path.endswith('.webmanifest'):
                return resp
            if 'Cache-Control' not in resp.headers:
                resp.headers['Cache-Control'] = 'public, max-age=604800, immutable'
        return resp

# GZip first (outermost added last in Starlette — add gzip AFTER so it wraps responses)
app.add_middleware(CacheHeaders)
app.add_middleware(GZipMiddleware, minimum_size=500)


@app.get("/sw.js", include_in_schema=False)
async def pwa_service_worker():
    """Serve SW from site root so scope can be '/' (required for installability)."""
    path = os.path.join(BASE_DIR, "static", "sw.js")
    return FileResponse(
        path,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Service-Worker-Allowed": "/",
        },
    )


@app.get("/manifest.webmanifest", include_in_schema=False)
async def pwa_manifest_alias():
    path = os.path.join(BASE_DIR, "static", "manifest.webmanifest")
    return FileResponse(
        path,
        media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )

# PROD default: data/shoes.db. DEV: set DB_PATH via /root/dev.sh (data-staging/shoes.db)
DB_PATH = _resolve_db_path()
os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _save_task_images(files) -> list:
    """Route uploads by type with parallel R2 uploads.
    Images: compress to webp then upload to R2 (parallel via ThreadPoolExecutor).
    PDFs: parallel upload to R2 via ThreadPoolExecutor (4-8 workers).
    Both return CDN URLs (https://cdn...) stored in result_files.
    """
    files = [f for f in (files or []) if f and f.filename]
    if not files:
        return []
    tasks_dir = os.path.join(UPLOADS_DIR, "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    r2_ready = os.environ.get('R2_ACCOUNT_ID') and os.environ.get('R2_BUCKET')

    # Split work by type
    pdf_files = [f for f in files if os.path.splitext(f.filename)[1].lower() == '.pdf']
    img_files = [f for f in files if f not in pdf_files]

    saved = []

    # --- images: save locally, then parallel R2 upload ---
    if img_files:
        local_results = []
        for f in img_files:
            try:
                ext = os.path.splitext(f.filename)[1].lower()
                name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + ext
                path = os.path.join(tasks_dir, name)
                f.file.seek(0)
                with open(path, 'wb') as out:
                    out.write(f.file.read())
                local_results.append((path, f.filename))
            except Exception as e:
                print(f'Image save failed ({f.filename}): {e}')

        if r2_ready:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            def _upload_one_img(item):
                local_path, orig_name = item
                ext = os.path.splitext(local_path)[1].lower()
                
                # Only compress and use _upload_image_to_r2 for actual images
                if ext in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
                    # We need to redefine _upload_image_to_r2 or use a modified version
                    # Since I replaced _upload_image_to_r2 with _upload_generic_to_r2, 
                    # I'll handle compression here then upload generic.
                    compressed = _compress_image(local_path)
                    if compressed:
                        cdn_url = _upload_generic_to_r2(compressed, 'image/webp')
                    else:
                        cdn_url = _upload_generic_to_r2(local_path, 'application/octet-stream')
                else:
                    # Video or other files: upload as-is
                    mime, _ = mimetypes.guess_type(local_path)
                    cdn_url = _upload_generic_to_r2(local_path, mime or 'application/octet-stream')

                if cdn_url:
                    return (cdn_url, orig_name)
                # Fallback: return local path (StaticFiles serves it)
                return ('uploads/tasks/' + os.path.basename(local_path), orig_name)

            with ThreadPoolExecutor(max_workers=min(8, len(local_results))) as ex:
                futures = [ex.submit(_upload_one_img, item) for item in local_results]
                for fut in as_completed(futures):
                    url, orig_name = fut.result()
                    saved.append((url, orig_name))
                    kind = 'r2' if url.startswith('http') else 'local'
                    print(f'Image uploaded ({kind}): {url}')
        else:
            # R2 not configured: use local paths
            for local_path, orig_name in local_results:
                compressed = _compress_image(local_path)
                if compressed:
                    saved.append(('uploads/tasks/' + os.path.basename(compressed), orig_name))
                else:
                    saved.append(('uploads/tasks/' + os.path.basename(local_path), orig_name))

    # --- PDFs: parallel upload to R2 (or local fallback) ---
    if pdf_files:
        if r2_ready:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            def _upload_one_pdf(f):
                try:
                    return ('r2', _upload_pdf_to_r2(f), f.filename)
                except Exception as e:
                    print(f'PDF R2 upload failed ({f.filename}): {e}')
                    name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + '.pdf'
                    path = os.path.join(tasks_dir, name)
                    f.file.seek(0)
                    with open(path, 'wb') as out:
                        out.write(f.file.read())
                    return ('local', f'uploads/tasks/{name}', f.filename)

            with ThreadPoolExecutor(max_workers=min(8, len(pdf_files))) as ex:
                futures = [ex.submit(_upload_one_pdf, f) for f in pdf_files]
                for fut in as_completed(futures):
                    kind, url, orig_name = fut.result()
                    saved.append((url, orig_name))
                    print(f'PDF uploaded ({kind}): {url}')
        else:
            for f in pdf_files:
                name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + '.pdf'
                path = os.path.join(tasks_dir, name)
                f.file.seek(0)
                with open(path, 'wb') as out:
                    out.write(f.file.read())
                saved.append((f'uploads/tasks/{name}', f.filename))

    return saved

def _parse_existing_images(raw: str) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [x for x in data if isinstance(x, str)]
    except Exception:
        return []

def _parse_existing_names(raw: str) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return [x for x in data if isinstance(x, str)]
    except Exception:
        return []

def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS designs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            material TEXT,
            color TEXT,
            status TEXT DEFAULT 'draft',
            image_path TEXT,
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pdf_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            title TEXT NOT NULL,
            notes TEXT,
            images_json TEXT,
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT,
            link TEXT,
            status TEXT DEFAULT 'draft',
            notes TEXT,
            result TEXT,
            result_files TEXT,
            result_files_names TEXT,
            created_at TEXT
        )
    ''')
    # Migrations: drop source, ensure result/result_files columns
    task_cols = {r[1] for r in conn.execute('PRAGMA table_info(tasks)').fetchall()}
    if 'source' in task_cols:
        conn.execute('ALTER TABLE tasks RENAME TO _tasks_old')
        conn.execute('''
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT,
                link TEXT,
                status TEXT DEFAULT 'draft',
                notes TEXT,
                result TEXT,
                result_files TEXT,
                created_at TEXT
            )
        ''')
        conn.execute('''
            INSERT INTO tasks (id, title, category, link, status, notes, created_at)
            SELECT id, title, category, link, status, notes, created_at FROM _tasks_old
        ''')
        conn.execute('DROP TABLE _tasks_old')
    task_cols = {r[1] for r in conn.execute('PRAGMA table_info(tasks)').fetchall()}
    if 'result_images' in task_cols and 'result_files' not in task_cols:
        conn.execute('ALTER TABLE tasks RENAME COLUMN result_images TO result_files')
    elif 'result_files' not in task_cols and 'result' in task_cols:
        conn.execute('ALTER TABLE tasks ADD COLUMN result_files TEXT')
    if 'result_files_names' not in task_cols:
        conn.execute('ALTER TABLE tasks ADD COLUMN result_files_names TEXT')
    task_cols = {r[1] for r in conn.execute('PRAGMA table_info(tasks)').fetchall()}
    for col, decl in (
        ('product_id', 'INTEGER'),
        ('gdrive_links', 'TEXT'),
        ('gdrive_types', 'TEXT'),
        ('gdrive_names', 'TEXT'),
    ):
        if col not in task_cols:
            conn.execute(f'ALTER TABLE tasks ADD COLUMN {col} {decl}')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS file_references (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            file_key    TEXT    NOT NULL UNIQUE,
            filename    TEXT    NOT NULL,
            file_type   TEXT,
            size_bytes  INTEGER,
            cdn_url     TEXT,
            local_path  TEXT,
            table_name  TEXT,
            row_id      INTEGER,
            column_name TEXT,
            migrated_at TEXT    DEFAULT (datetime('now')),
            UNIQUE(table_name, row_id, column_name)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fr_table_row ON file_references(table_name, row_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fr_local    ON file_references(local_path)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_fr_cdn     ON file_references(cdn_url)')
    # Design Feedback / Team Poll (JSON blob — easy to swap storage later)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS design_polls (
            id TEXT PRIMARY KEY,
            payload TEXT NOT NULL,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    # App branding / settings (editable header for public/starter installs)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    # Light staging seed only when empty (never overwrites real data)
    # NOTE: prod also sets DB_PATH off-tree — use _is_staging_env(), not bool(DB_PATH)
    is_staging = _is_staging_env()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    n_products = conn.execute('SELECT COUNT(*) AS n FROM products').fetchone()['n']
    n_designs = conn.execute('SELECT COUNT(*) AS n FROM designs').fetchone()['n']
    n_tasks = conn.execute('SELECT COUNT(*) AS n FROM tasks').fetchone()['n']
    if is_staging and n_products == 0:
        conn.execute(
            'INSERT INTO products (name, created_at) VALUES (?, ?)',
            ('DEV Sample Product', now),
        )
    if is_staging and n_designs == 0:
        conn.execute(
            'INSERT INTO designs (model_name, material, color, status, image_path, created_at) VALUES (?,?,?,?,?,?)',
            ('DEV Model A', 'mesh', 'navy', 'draft', None, now),
        )
        conn.execute(
            'INSERT INTO designs (model_name, material, color, status, image_path, created_at) VALUES (?,?,?,?,?,?)',
            ('DEV Model B', 'leather', 'black', 'review', None, now),
        )
    if is_staging and n_tasks == 0:
        pid = conn.execute('SELECT id FROM products ORDER BY id LIMIT 1').fetchone()
        pid = pid['id'] if pid else None
        conn.execute(
            'INSERT INTO tasks (title, category, link, status, notes, result, result_files, result_files_names, created_at, product_id) VALUES (?,?,?,?,?,?,?,?,?,?)',
            ('DEV sample task', 'design', '', 'draft', 'staging only — safe to edit/delete', None, None, None, now, pid),
        )
    conn.commit()
    conn.close()

init_db()

# ── Design Feedback / Team Poll API ────────────────────────────

from pydantic import BaseModel, Field
from typing import List, Optional, Any


# ── Brand settings API (editable header) ───────────────────────────

class BrandIn(BaseModel):
    brand_name: str = Field(..., min_length=1, max_length=40)
    brand_tagline: str = Field('', max_length=80)


@app.get("/api/brand", include_in_schema=False)
def api_brand_get():
    return _brand_ctx()


@app.post("/api/brand", include_in_schema=False)
async def api_brand_set(request: Request, body: BrandIn):
    if not _pin_ok(request):
        return JSONResponse({"error": "unauthorized", "message": "Login as admin first"}, status_code=401)
    name = body.brand_name.strip()
    tagline = (body.brand_tagline or '').strip()
    if not name:
        return JSONResponse({"error": "brand_name required"}, status_code=400)
    _set_setting('brand_name', name[:40])
    _set_setting('brand_tagline', tagline[:80])
    return {"status": "ok", **_brand_ctx()}


@app.post("/api/brand/logo", include_in_schema=False)
async def api_brand_logo_set(request: Request, logo: UploadFile = File(...)):
    """Admin: upload custom navbar logo (per-install, stored under uploads/brand/)."""
    if not _pin_ok(request):
        return JSONResponse({"error": "unauthorized", "message": "Login as admin first"}, status_code=401)
    if not logo or not logo.filename:
        return JSONResponse({"error": "logo file required"}, status_code=400)

    raw_ext = os.path.splitext(logo.filename)[1].lower() or '.png'
    allowed = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}
    if raw_ext not in allowed:
        return JSONResponse({"error": "format logo: png/jpg/webp/gif/svg"}, status_code=400)
    # normalize jpeg
    ext = '.jpg' if raw_ext == '.jpeg' else raw_ext

    brand_dir = os.path.join(UPLOADS_DIR, 'brand')
    os.makedirs(brand_dir, exist_ok=True)

    # wipe previous custom logos
    try:
        for fn in os.listdir(brand_dir):
            if fn.startswith('logo'):
                try:
                    os.remove(os.path.join(brand_dir, fn))
                except Exception:
                    pass
    except Exception:
        pass

    dest = os.path.join(brand_dir, f'logo{ext}')
    nbytes = await _save_upload_stream(logo, dest)
    # soft size guard ~2.5MB
    if nbytes > 2_500_000:
        try:
            os.remove(dest)
        except Exception:
            pass
        return JSONResponse({"error": "logo terlalu besar (max ~2.5MB)"}, status_code=400)

    rel = f'/uploads/brand/logo{ext}'
    _set_setting('brand_logo', rel)
    return {"status": "ok", **_brand_ctx()}


@app.delete("/api/brand/logo", include_in_schema=False)
async def api_brand_logo_reset(request: Request):
    """Admin: hapus logo custom → default tanpa logo."""
    if not _pin_ok(request):
        return JSONResponse({"error": "unauthorized", "message": "Login as admin first"}, status_code=401)
    brand_dir = os.path.join(UPLOADS_DIR, 'brand')
    try:
        if os.path.isdir(brand_dir):
            for fn in os.listdir(brand_dir):
                if fn.startswith('logo'):
                    try:
                        os.remove(os.path.join(brand_dir, fn))
                    except Exception:
                        pass
    except Exception:
        pass
    # explicit empty = no logo (default product look)
    _set_setting('brand_logo', '')
    return {"status": "ok", **_brand_ctx()}


class PollDesignIn(BaseModel):
    id: str
    url: str
    name: str = 'Desain'
    thumbnail: Optional[str] = None


class PollCreateIn(BaseModel):
    id: str = Field(..., min_length=4, max_length=32)
    title: str = Field(..., min_length=1, max_length=200)
    description: str = ''
    designs: List[PollDesignIn]
    creatorName: str = Field(..., min_length=1, max_length=80)
    createdAt: Optional[int] = None
    votes: Optional[List[Any]] = None


class PollVoteIn(BaseModel):
    voterName: str = Field(..., min_length=1, max_length=80)
    designIds: List[str]


def _poll_row_to_dict(row) -> dict:
    try:
        return json.loads(row['payload'])
    except Exception:
        return {}


def _save_poll_payload(conn, poll: dict):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    pid = poll['id']
    payload = json.dumps(poll, ensure_ascii=False)
    exists = conn.execute('SELECT id FROM design_polls WHERE id=?', (pid,)).fetchone()
    if exists:
        conn.execute(
            'UPDATE design_polls SET payload=?, updated_at=? WHERE id=?',
            (payload, now, pid),
        )
    else:
        conn.execute(
            'INSERT INTO design_polls (id, payload, created_at, updated_at) VALUES (?,?,?,?)',
            (pid, payload, now, now),
        )


@app.get('/api/polls')
async def api_list_polls(request: Request):
    # Admin-only: full poll history (non-admin uses shared /poll/:id links)
    if not _pin_ok(request):
        raise HTTPException(status_code=401, detail='Admin PIN required')
    conn = get_db()
    rows = conn.execute(
        'SELECT payload FROM design_polls ORDER BY created_at DESC LIMIT 50'
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        try:
            p = json.loads(r['payload'])
            out.append({
                'id': p.get('id'),
                'title': p.get('title'),
                'creatorName': p.get('creatorName'),
                'designCount': len(p.get('designs') or []),
                'voteCount': len(p.get('votes') or []),
                'createdAt': p.get('createdAt'),
            })
        except Exception:
            continue
    return JSONResponse(out)


@app.get('/api/polls/auth')
async def api_polls_auth(request: Request):
    """SPA probe: is current session admin?"""
    return JSONResponse({'pin_ok': _pin_ok(request), 'admin': _pin_ok(request)})


@app.post('/api/polls')
async def api_create_poll(request: Request, body: PollCreateIn):
    if not _pin_ok(request):
        raise HTTPException(status_code=401, detail='Admin PIN required — login di /pin dulu')
    if not body.designs:
        raise HTTPException(status_code=400, detail='Minimal 1 desain')
    poll = {
        'id': body.id.strip(),
        'title': body.title.strip(),
        'description': (body.description or '').strip(),
        'designs': [d.model_dump() if hasattr(d, 'model_dump') else d.dict() for d in body.designs],
        'creatorName': body.creatorName.strip(),
        'createdAt': body.createdAt or int(datetime.now().timestamp() * 1000),
        'votes': body.votes or [],
    }
    conn = get_db()
    try:
        if conn.execute('SELECT id FROM design_polls WHERE id=?', (poll['id'],)).fetchone():
            raise HTTPException(status_code=409, detail='Poll id sudah ada')
        _save_poll_payload(conn, poll)
        conn.commit()
    finally:
        conn.close()
    return JSONResponse(poll)


@app.get('/api/polls/{poll_id}')
async def api_get_poll(poll_id: str):
    conn = get_db()
    row = conn.execute('SELECT payload FROM design_polls WHERE id=?', (poll_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail='Poll tidak ditemukan')
    return JSONResponse(_poll_row_to_dict(row))


@app.post('/api/polls/{poll_id}/vote')
async def api_vote_poll(poll_id: str, body: PollVoteIn):
    name = body.voterName.strip()
    ids = list(dict.fromkeys(body.designIds or []))
    if not name:
        raise HTTPException(status_code=400, detail='Nama wajib diisi')
    if not ids:
        raise HTTPException(status_code=400, detail='Pilih minimal 1 desain')
    conn = get_db()
    try:
        row = conn.execute('SELECT payload FROM design_polls WHERE id=?', (poll_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Poll tidak ditemukan')
        poll = _poll_row_to_dict(row)
        valid = {d.get('id') for d in (poll.get('designs') or [])}
        ids = [i for i in ids if i in valid]
        if not ids:
            raise HTTPException(status_code=400, detail='Desain tidak valid')
        votes = poll.get('votes') or []
        if any(str(v.get('voterName', '')).lower() == name.lower() for v in votes):
            raise HTTPException(status_code=409, detail='Nama ini sudah vote')
        votes.append({
            'voterName': name,
            'designIds': ids,
            'at': int(datetime.now().timestamp() * 1000),
        })
        poll['votes'] = votes
        _save_poll_payload(conn, poll)
        conn.commit()
    finally:
        conn.close()
    return JSONResponse(poll)


@app.delete('/api/polls/{poll_id}')
async def api_delete_poll(request: Request, poll_id: str):
    """Admin-only hard delete of a design poll."""
    if not _pin_ok(request):
        raise HTTPException(status_code=401, detail='Admin PIN required')
    pid = (poll_id or '').strip()
    if not pid:
        raise HTTPException(status_code=400, detail='poll_id kosong')
    conn = get_db()
    try:
        row = conn.execute('SELECT id FROM design_polls WHERE id=?', (pid,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail='Poll tidak ditemukan')
        conn.execute('DELETE FROM design_polls WHERE id=?', (pid,))
        conn.commit()
    finally:
        conn.close()
    return JSONResponse({'ok': True, 'id': pid, 'deleted': True})


# SPA assets for Design Feedback (React build under static/poll-app)
# Shell = main index.html (same header/nav as other tabs). React mounts into #root.
_POLL_APP_DIR = os.path.join(BASE_DIR, 'static', 'poll-app')
_POLL_APP_INDEX = os.path.join(_POLL_APP_DIR, 'index.html')
_POLL_ASSETS_DIR = os.path.join(_POLL_APP_DIR, 'assets')


def _poll_build_assets():
    """CSS/JS paths from last Vite build (hashed filenames)."""
    css, js = [], []
    if not os.path.isfile(_POLL_APP_INDEX):
        return css, js
    try:
        with open(_POLL_APP_INDEX, 'r', encoding='utf-8') as f:
            html = f.read()
    except OSError:
        return css, js
    css = re.findall(r'href="(/poll-app/assets/[^"]+\.css)"', html)
    js = re.findall(r'src="(/poll-app/assets/[^"]+\.js)"', html)
    return css, js


# Built JS/CSS: /poll-app/assets/*
if os.path.isdir(_POLL_ASSETS_DIR):
    app.mount(
        '/poll-app/assets',
        StaticFiles(directory=_POLL_ASSETS_DIR),
        name='poll_app_assets',
    )


@app.get('/poll-app', response_class=HTMLResponse)
@app.get('/poll-app/', response_class=HTMLResponse)
@app.get('/poll-app/{path:path}', response_class=HTMLResponse)
async def poll_app_redirect(path: str = ''):
    # Legacy SPA URL → pretty path inside main shell
    if path and not path.startswith('assets'):
        dest = '/poll/' + path.lstrip('/')
    else:
        dest = '/poll'
    return RedirectResponse(url=dest, status_code=302)


@app.get('/poll', response_class=HTMLResponse)
@app.get('/poll/', response_class=HTMLResponse)
@app.get('/poll/{poll_id}', response_class=HTMLResponse)
@app.get('/poll/{poll_id}/{extra}', response_class=HTMLResponse)
async def poll_shell(request: Request, poll_id: str = '', extra: str = ''):
    """Same chrome as Tasks/In Work — React poll UI embeds into #root."""
    css, js = _poll_build_assets()
    return templates.TemplateResponse(
        request=request,
        name='index.html',
        context={
            'menu': 'poll',
            'pin_ok': _pin_ok(request),
            'app_version': APP_VERSION,
            'poll_css': css,
            'poll_js': js,
        },
    )


# ── TASKS (Jobdesk) ────────────────────────────────────────────


@app.get("/api/products-with-tasks")
async def get_products_with_tasks(request: Request):
    conn = get_db()
    # Query to get products that have at least one task
    query = """
        SELECT d.id, d.model_name, d.status, d.image_path
        FROM designs d
        WHERE EXISTS (
            SELECT 1 FROM tasks t WHERE t.product_id = d.id
        )
        ORDER BY d.id DESC
    """
    products_rows = conn.execute(query).fetchall()
    products = [dict(row) for row in products_rows]
    conn.close()
    return JSONResponse(content=products)

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    # Unified view: same template for admin & public. Admin chrome gated by pin_ok.
    pin_ok = _pin_ok(request)
    conn = get_db()
    tasks = conn.execute('SELECT * FROM tasks ORDER BY id DESC').fetchall()
    products = conn.execute('SELECT id, model_name, status, image_path FROM designs ORDER BY id DESC').fetchall()
    conn.close()
    tasks_list = []
    for t in tasks:
        d = dict(t)
        try:
            d['result_files_list'] = json.loads(d.get('result_files') or '[]')
        except Exception:
            d['result_files_list'] = []
        try:
            d['result_files_names_list'] = json.loads(d.get('result_files_names') or '[]')
        except Exception:
            d['result_files_names_list'] = []
        tasks_list.append(d)
    products_list = [dict(p) for p in products]
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"tasks": tasks_list, "products": products_list, "menu": "tasks", "pin_ok": pin_ok, "app_version": APP_VERSION}
    )


@app.get("/tasks/product/{product_id}", response_class=HTMLResponse)
async def tasks_by_product(product_id: int, request: Request):
    """Open a product's tasks in a new browser tab/page."""
    pin_ok = _pin_ok(request)
    
    conn = get_db()
    # Get product info — check designs table first, then products table (for Unlink)
    product_row = conn.execute("SELECT * FROM designs WHERE id = ?", (product_id,)).fetchone()
    if not product_row:
        # Try products table (for Unlink and other products)
        product_row = conn.execute("SELECT id, name FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product_row:
        conn.close()
        return {"error": "Produk tidak ditemukan"}, 404
    product = dict(product_row)
    if 'model_name' not in product:
        product['model_name'] = product.get('name', 'Unknown')
    
    # Get tasks for this product
    task_rows = conn.execute("SELECT * FROM tasks WHERE product_id = ? ORDER BY id DESC", (product_id,)).fetchall()
    conn.close()
    
    tasks_list = []
    for t in task_rows:
        d = dict(t)
        try:
            d['result_files_list'] = json.loads(d.get('result_files') or '[]')
        except Exception:
            d['result_files_list'] = []
        try:
            d['result_files_names_list'] = json.loads(d.get('result_files_names') or '[]')
        except Exception:
            d['result_files_names_list'] = []
        tasks_list.append(d)
    
    products = conn.execute("SELECT * FROM designs ORDER BY id DESC").fetchall() if False else []
    products_list = [dict(p) for p in products]
    
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "tasks": tasks_list,
            "products": products_list,
            "menu": "tasks",
            "pin_ok": pin_ok,
            "app_version": APP_VERSION,
            "view_mode": "product_detail",
            "product_name": product.get('model_name', 'Unknown'),
            "product_id": product_id
        }
    )



@app.get("/task/{task_id}", response_class=HTMLResponse)
async def task_detail(task_id: int, request: Request):
    pin_ok = _pin_ok(request)
    conn = get_db()
    row = conn.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Task tidak ditemukan")
    t = dict(row)
    try:
        t['result_files_list'] = json.loads(t.get('result_files') or '[]')
    except Exception:
        t['result_files_list'] = []
    try:
        t['result_files_names_list'] = json.loads(t.get('result_files_names') or '[]')
    except Exception:
        t['result_files_names_list'] = []
    try:
        t['gdrive_links_list'] = json.loads(t.get('gdrive_links') or '[]')
        t['gdrive_types_list'] = json.loads(t.get('gdrive_types') or '[]')
        t['gdrive_names_list'] = json.loads(t.get('gdrive_names') or '[]')
    except Exception:
        t['gdrive_links_list'] = []
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"tasks": [], "detail_task": t, "menu": "tasks", "pin_ok": pin_ok, "app_version": APP_VERSION}
    )

@app.get("/pin", response_class=HTMLResponse)
async def pin_form(request: Request):
    # Prefer ?next= for SPA deep-links (e.g. /poll/new), else referer, else /tasks
    nxt = (request.query_params.get("next") or "").strip() or request.headers.get("referer") or "/tasks"
    # only allow relative paths (open-redirect guard)
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = "/tasks"
    return templates.TemplateResponse(
        request=request,
        name="pin.html",
        context={"next": nxt, "pin_ok": _pin_ok(request), "app_version": APP_VERSION},
    )

@app.post("/pin")
async def pin_verify(request: Request, pin: str = Form(...), next: str = Form("/tasks")):
    if pin.strip() == ADMIN_PIN:
        request.session["pin_ok"] = True
        return RedirectResponse(url=next or "/tasks", status_code=303)
    return templates.TemplateResponse(request=request, name="pin.html", context={"next": next, "error": "PIN salah", "pin_ok": _pin_ok(request), "app_version": APP_VERSION}, status_code=401)

@app.post("/pin/logout")
async def pin_logout(request: Request, next: str = Form("")):
    """Toggle ADMIN OFF — drop session and stay on page. Never send user to PIN form."""
    request.session.clear()
    nxt = (next or "").strip() or request.headers.get("referer") or "/"
    # only allow relative paths (open-redirect guard)
    if not nxt.startswith("/") or nxt.startswith("//"):
        # referer may be absolute — extract path
        try:
            from urllib.parse import urlparse
            p = urlparse(nxt)
            nxt = p.path or "/"
            if p.query:
                nxt = nxt + "?" + p.query
        except Exception:
            nxt = "/"
    if not nxt.startswith("/") or nxt.startswith("//"):
        nxt = "/"
    # never bounce logout → /pin (that looks like "re-login popup")
    if nxt == "/pin" or nxt.startswith("/pin?"):
        nxt = "/tasks"
    return RedirectResponse(url=nxt, status_code=303)


@app.get("/api/products")
async def api_products(request: Request):
    conn = get_db()
    # Get from designs table
    designs = conn.execute('SELECT id, model_name, status, image_path FROM designs ORDER BY id DESC').fetchall()
    # Get from products table (Unlink, etc.)
    prods = conn.execute('SELECT id, name FROM products ORDER BY id DESC').fetchall()
    conn.close()
    # Merge from both tables — designs first, then products (overwrite duplicates)
    seen_ids = set()
    result = []
    for d in designs:
        seen_ids.add(d['id'])
        result.append(dict(d))
    for p in prods:
        if p['id'] not in seen_ids:
            result.append({
                'id': p['id'],
                'model_name': p['name'],
                'status': None,
                'image_path': None
            })
    # Sort by id descending
    result.sort(key=lambda x: x['id'], reverse=True)
    return result

@app.get("/api/tasks")
async def api_tasks(request: Request, product_id: int = Query(None)):
    conn = get_db()
    if product_id:
        tasks = conn.execute('SELECT * FROM tasks WHERE product_id = ? ORDER BY id DESC', (product_id,)).fetchall()
    else:
        tasks = conn.execute('SELECT * FROM tasks ORDER BY id DESC').fetchall()
    conn.close()
    result = []
    for t in tasks:
        d = dict(t)
        try:
            d['result_files_list'] = json.loads(d.get('result_files') or '[]')
        except Exception:
            d['result_files_list'] = []
        try:
            d['result_files_names_list'] = json.loads(d.get('result_files_names') or '[]')
        except Exception:
            d['result_files_names_list'] = []
        result.append(d)
    return result

@app.post("/tasks/add")
@app.post("/tasks/add")
async def task_add(request: Request,
    product_id: int = Form(...),
    title: str = Form(...),
    category: str = Form(""),
    link: str = Form(""),
    notes: str = Form(""),
    result: str = Form(""),
    status: str = Form("draft"),
    result_files: list[UploadFile] = File(default=[]),
    existing_images: str = Form(""),
    existing_images_names: str = Form(""),
    preuploaded_urls: str = Form(""),
    preuploaded_names: str = Form(""),
):
    guard = _pin_guard(request)
    if guard: return guard
    if not _pin_ok(request):
        return RedirectResponse(url="/pin?next=/add", status_code=303)
    saved = _save_task_images(result_files)
    keep = _parse_existing_images(existing_images)
    keep_names = _parse_existing_names(existing_images_names)
    # Parse pre-uploaded URLs from XHR parallel upload
    pre = []
    pre_names = []
    if preuploaded_urls:
        try:
            pre = [u for u in json.loads(preuploaded_urls) if u]
        except Exception:
            pre = []
    if preuploaded_names:
        try:
            pre_names = [n for n in json.loads(preuploaded_names) if n]
        except Exception:
            pre_names = []
    saved_urls = [u for u, _ in saved]
    saved_names = [n for _, n in saved]
    all_imgs = json.dumps(keep + pre + saved_urls)
    if keep_names and len(keep_names) >= len(keep):
        existing_names = keep_names[:len(keep)]
    else:
        existing_names = [os.path.basename(k) for k in keep]
    all_names = json.dumps(existing_names + pre_names + saved_names)
    conn = get_db()
    conn.execute(
        'INSERT INTO tasks (product_id, title, category, link, status, notes, result, result_files, result_files_names, created_at) VALUES (?,?,?,?,?,?,?,?,?,?)',
        (product_id, title.strip(), category.strip(), link.strip(), status,
         notes.strip(), result.strip(), all_imgs, all_names, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/tasks", status_code=303)

@app.post("/tasks/update/{task_id}")
async def task_update(request: Request, task_id: int,
    title: str = Form(...),
    category: str = Form(""),
    link: str = Form(""),
    notes: str = Form(""),
    result: str = Form(""),
    status: str = Form("draft"),
    result_files: list[UploadFile] = File(default=[]),
    existing_images: str = Form(""),
    existing_images_names: str = Form(""),
    preuploaded_urls: str = Form(""),
    preuploaded_names: str = Form(""),
    gdrive_links: str = Form(""),
    gdrive_types: str = Form(""),
    gdrive_names: str = Form(""),
    next: str = Form(""),
):
    guard = _pin_guard(request)
    if guard: return guard
    if not _pin_ok(request):
        return RedirectResponse(url=f"/pin?next=/task/{task_id}", status_code=303)
    # v1.1: fetch old URLs BEFORE update so we can diff + delete removed files
    conn = get_db()
    row = conn.execute('SELECT result_files FROM tasks WHERE id=?', (task_id,)).fetchone()
    try:
        old_urls = json.loads(row['result_files'] or '[]') if row else []
    except Exception:
        old_urls = []

    saved = _save_task_images(result_files)
    keep = _parse_existing_images(existing_images)
    keep_names = _parse_existing_names(existing_images_names)
    pre = []
    pre_names = []
    if preuploaded_urls:
        try:
            pre = [u for u in json.loads(preuploaded_urls) if u]
        except Exception:
            pre = []
    if preuploaded_names:
        try:
            pre_names = [n for n in json.loads(preuploaded_names) if n]
        except Exception:
            pre_names = []
    saved_urls = [u for u, _ in saved]
    saved_names = [n for _, n in saved]
    all_imgs = json.dumps(keep + pre + saved_urls)
    if keep_names and len(keep_names) >= len(keep):
        existing_names = keep_names[:len(keep)]
    else:
        existing_names = [os.path.basename(k) for k in keep]
    all_names = json.dumps(existing_names + pre_names + saved_names)
    conn.execute(
        'UPDATE tasks SET title=?, category=?, link=?, status=?, notes=?, result=?, result_files=?, result_files_names=?, gdrive_links=?, gdrive_types=?, gdrive_names=? WHERE id=?',
        (title.strip(), category.strip(), link.strip(), status,
         notes.strip(), result.strip(), all_imgs, all_names, gdrive_links, gdrive_types, gdrive_names, task_id)
    )
    conn.commit()
    conn.close()

    # v1.1: cleanup removed files from R2 + local fs
    new_urls = keep + pre + saved_urls
    try:
        _delete_removed_files(old_urls, new_urls)
    except Exception as e:
        print(f'Cleanup error: {e}')

    # Stay on this task detail (not /tasks list). Optional next= for rare callers.
    dest = f"/task/{task_id}"
    nxt = (next or "").strip()
    if nxt.startswith("/") and not nxt.startswith("//"):
        dest = nxt
    return RedirectResponse(url=dest, status_code=303)


@app.post("/tasks/gdrive-reorder/{task_id}")
async def task_gdrive_reorder(request: Request, task_id: int):
    """Reorder GDrive links/types/names by index permutation. Admin only."""
    if not _pin_ok(request):
        return JSONResponse({"ok": False, "error": "PIN required"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    order = body.get("order")
    if not isinstance(order, list) or not order:
        return JSONResponse({"ok": False, "error": "order required"}, status_code=400)
    try:
        order = [int(x) for x in order]
    except Exception:
        return JSONResponse({"ok": False, "error": "order must be int list"}, status_code=400)

    conn = get_db()
    row = conn.execute(
        "SELECT gdrive_links, gdrive_types, gdrive_names FROM tasks WHERE id=?",
        (task_id,),
    ).fetchone()
    if not row:
        conn.close()
        return JSONResponse({"ok": False, "error": "task not found"}, status_code=404)
    try:
        links = json.loads(row["gdrive_links"] or "[]")
    except Exception:
        links = []
    try:
        types = json.loads(row["gdrive_types"] or "[]")
    except Exception:
        types = []
    try:
        names = json.loads(row["gdrive_names"] or "[]")
    except Exception:
        names = []
    n = len(links)
    if n == 0:
        conn.close()
        return JSONResponse({"ok": False, "error": "no gdrive links"}, status_code=400)
    if len(order) != n or sorted(order) != list(range(n)):
        conn.close()
        return JSONResponse(
            {"ok": False, "error": f"order must be permutation of 0..{n-1}"},
            status_code=400,
        )
    while len(types) < n:
        types.append("image")
    while len(names) < n:
        names.append("")
    types = types[:n]
    names = names[:n]
    new_links = [links[i] for i in order]
    new_types = [types[i] for i in order]
    new_names = [names[i] for i in order]
    conn.execute(
        "UPDATE tasks SET gdrive_links=?, gdrive_types=?, gdrive_names=? WHERE id=?",
        (json.dumps(new_links), json.dumps(new_types), json.dumps(new_names), task_id),
    )
    conn.commit()
    conn.close()
    return JSONResponse(
        {
            "ok": True,
            "links": new_links,
            "types": new_types,
            "names": new_names,
        }
    )


@app.post("/tasks/rename-file/{task_id}")
async def task_rename_file(request: Request, task_id: int, idx: int = Form(...), name: str = Form(...)):

    guard = _pin_guard(request)
    if guard: return guard
    if not _pin_ok(request):
        return JSONResponse({"ok": False, "error": "PIN required"}, status_code=401)
    """Rename display name of one file in result_files_names (parallel to result_files).
    Does NOT touch disk / R2 - display-only, like the rest of the name flow."""
    conn = get_db()
    row = conn.execute('SELECT result_files, result_files_names FROM tasks WHERE id = ?', (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, detail='task not found')
    try:
        urls = json.loads(row['result_files'] or '[]')
    except Exception:
        urls = []
    try:
        names = json.loads(row['result_files_names'] or '[]')
    except Exception:
        names = []
    if idx < 0 or idx >= len(urls):
        conn.close()
        raise HTTPException(400, detail=f'idx out of range (0..{len(urls)-1})')
    while len(names) < len(urls):
        names.append(os.path.basename(urls[len(names)]))
    # sanitize: strip slashes/backslashes, control chars, length cap
    raw = (name or '').strip()
    safe = ''.join(c for c in raw if c.isprintable() and c not in '/\\\\|?*<>:"')[:200]
    if not safe:
        safe = os.path.basename(urls[idx])
    names[idx] = safe
    conn.execute('UPDATE tasks SET result_files_names = ? WHERE id = ?', (json.dumps(names), task_id))
    conn.commit()
    conn.close()
    return {'ok': True, 'idx': idx, 'name': safe}


@app.post("/tasks/delete/{task_id}")
async def task_delete(request: Request, task_id: int):
    guard = _pin_guard(request)
    if guard: return guard
    if not _pin_ok(request):
        return RedirectResponse(url="/pin?next=/tasks", status_code=303)
    conn = get_db()
    row = conn.execute('SELECT result_files FROM tasks WHERE id = ?', (task_id,)).fetchone()
    conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    if row and row['result_files']:
        try:
            urls = json.loads(row['result_files'])
        except Exception:
            urls = []
        _delete_r2_objects(_extract_remote_pdfs(urls))
    return RedirectResponse(url="/tasks", status_code=303)

@app.post("/tasks/bulk-delete")
async def task_bulk_delete(request: Request, ids: str = Form(...)):

    guard = _pin_guard(request)
    if guard: return guard
    if not _pin_ok(request):
        return RedirectResponse(url="/pin?next=/tasks", status_code=303)
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if id_list:
        conn = get_db()
        placeholders = ",".join("?" * len(id_list))
        rows = conn.execute(f'SELECT result_files FROM tasks WHERE id IN ({placeholders})', id_list).fetchall()
        conn.execute(f'DELETE FROM tasks WHERE id IN ({placeholders})', id_list)
        conn.commit()
        conn.close()
        for row in rows:
            if row and row['result_files']:
                try:
                    urls = json.loads(row['result_files'])
                except Exception:
                    urls = []
                _delete_r2_objects(_extract_remote_pdfs(urls))
    return RedirectResponse(url="/tasks", status_code=303)

@app.post("/tasks/status/{task_id}")
async def task_quick_status(request: Request, task_id: int, status: str = Form(...), next: str = Form(default="/tasks")):

    guard = _pin_guard(request)
    if guard: return guard
    if status not in ('draft', 'proses', 'finish'):
        raise HTTPException(status_code=400, detail="bad status")
    conn = get_db()
    conn.execute('UPDATE tasks SET status=? WHERE id=?', (status, task_id))
    conn.commit()
    conn.close()
    # Only honor internal next paths (avoid open-redirect)
    if not next.startswith('/') or next.startswith('//'):
        next = '/tasks'
    return RedirectResponse(url=next, status_code=303)

# ── SINGLE-FILE UPLOAD ENDPOINT (parallel from browser) ──────



@app.get("/task/{task_id}/edit-product")
def edit_product_form(request: Request, task_id: int, pin_ok: bool = Depends(_pin_ok)):
    if not pin_ok:
        return RedirectResponse(url=f"/pin?next=/task/{task_id}/edit-product")
    task = _get_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    products = _get_products()
    return templates.TemplateResponse(
        request=request, name="edit_product.html", context={
            "task": task, "products": products, "pin_ok": pin_ok, "app_version": APP_VERSION
        }
    )

@app.post("/task/{task_id}/edit-product")
def edit_product_submit(task_id: int, product_id: int = Form(...), pin_ok: bool = Depends(_pin_ok)):
    if not pin_ok:
        return RedirectResponse(url=f"/pin?next=/task/{task_id}/edit-product")
    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE tasks SET product_id = ? WHERE id = ?", (product_id, task_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/task/{task_id}", status_code=303)



@app.get("/upload/check")
def upload_check(key: str = Query(...)):
    """Verify if R2 has a key. VPS-side check, used as fallback when browser HEAD is slow.
    Returns {ok, url, size, found}."""
    if not (os.environ.get('R2_ACCOUNT_ID') and os.environ.get('R2_BUCKET')):
        return {"ok": False, "found": False, "reason": "r2 not configured"}
    # Basic safety: reject keys with traversal
    if '..' in key or key.startswith('/'):
        return {"ok": False, "found": False, "reason": "bad key"}
    try:
        s3 = _r2()
        head = s3.head_object(Bucket=os.environ['R2_BUCKET'], Key=key)
        size = head.get('ContentLength', 0)
        return {"ok": True, "found": True, "url": f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{key}", "size": size}
    except ClientError as e:
        code = e.response.get('Error', {}).get('Code', '')
        if code in ('404', 'NoSuchKey', 'NotFound'):
            return {"ok": True, "found": False, "url": f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{key}"}
        return {"ok": False, "found": False, "reason": str(e)}
    except Exception as e:
        return {"ok": False, "found": False, "reason": str(e)[:120]}

@app.get("/upload/presign")
async def upload_presign(filename: str, content_type: str = "application/octet-stream"):
    """Return a presigned PUT URL for direct-to-R2 browser upload under R2_PREFIX.
    Skips VPS entirely. Requires R2 CORS configured to allow PUT from this origin.
    Falls back gracefully (frontend detects and uses /upload/single instead).
    """
    bucket = os.environ.get('R2_BUCKET')
    if not bucket:
        raise HTTPException(503, detail='R2 not configured')
    ext = os.path.splitext(filename)[1].lower() or '.bin'
    # Allow all extensions to preserve original file type in R2
    prefix = _r2_prefix()
    key = prefix + 'tasks/' + datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + ext
    try:
        url = _r2().generate_presigned_url(
            'put_object',
            Params={'Bucket': bucket, 'Key': key, 'ContentType': content_type},
            ExpiresIn=600,  # 10 min
            HttpMethod='PUT',
        )
        public_url = f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{key}"
        return {'ok': True, 'put_url': url, 'public_url': public_url, 'key': key}
    except Exception as e:
        raise HTTPException(500, detail=f'presign failed: {e}')


@app.post("/upload/telemetry")
async def upload_telemetry(req: Request):
    """Browser POSTs phase changes here so we can debug stuck uploads."""
    try:
        body = await req.json()
        msg = f"[upload-telemetry] {body}"
        print(msg, flush=True)
        with open('/tmp/workflow_telemetry.log', 'a') as f:
            import json
            f.write(f"{_t.strftime('%H:%M:%S')} {_j.dumps(body)}\n")
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'err': str(e)}

@app.post("/upload/chunk/init")
async def upload_chunk_init(payload: dict):
    """Init chunked upload. Returns upload_id. Client then POSTs each chunk sequentially."""
    filename = payload.get('filename', 'unknown')
    content_type = payload.get('content_type', 'application/octet-stream')
    total_chunks = int(payload.get('total_chunks', 0))
    file_size = int(payload.get('file_size', 0))
    if total_chunks < 1 or total_chunks > 100 or file_size < 1 or file_size > 200 * 1024 * 1024:
        raise HTTPException(400, detail='bad params')
    upload_id = uuid.uuid4().hex
    upload_dir = f'/tmp/workflow_chunks/{upload_id}'
    os.makedirs(upload_dir, exist_ok=True)
    with open(f'{upload_dir}/meta.json', 'w') as f:
        json.dump({'filename': filename, 'content_type': content_type, 'total_chunks': total_chunks, 'file_size': file_size, 'created': datetime.now().isoformat()}, f)
    return {'ok': True, 'upload_id': upload_id}

@app.post("/upload/chunk/{upload_id}")
async def upload_chunk_action(upload_id: str, request: Request, seq: int = Query(default=None), action: str = Query(default=None)):
    """Combined endpoint:
    - ?action=put&seq=N → store chunk binary
    - ?action=finalize → assemble + upload to R2, return URL
    - ?action=abort → cleanup
    """
    if not upload_id or not all(c in '0123456789abcdef' for c in upload_id):
        raise HTTPException(400, detail='bad upload_id')
    upload_dir = f'/tmp/workflow_chunks/{upload_id}'
    if not os.path.isdir(upload_dir):
        raise HTTPException(404, detail='upload not found')

    if action == 'put':
        if seq is None or seq < 0:
            raise HTTPException(400, detail='seq required')
        with open(f'{upload_dir}/meta.json') as f:
            meta = json.load(f)
        if seq >= meta['total_chunks']:
            raise HTTPException(400, detail='seq out of range')
        chunk_path = f'{upload_dir}/{seq:04d}.part'
        with open(chunk_path, 'wb') as out:
            import asyncio
            try:
                async def read_with_timeout():
                    read_timeout = 30  # seconds
                    chunk_count = 0
                    total_read = 0
                    async for chunk in request.stream():
                        chunk_count += 1
                        total_read += len(chunk)
                        if chunk_count > 10000:  # safety limit
                            break
                        out.write(chunk)
                await asyncio.wait_for(read_with_timeout(), timeout=read_timeout)
            except asyncio.TimeoutError:
                raise HTTPException(408, detail='upload timeout')
        return {'ok': True, 'seq': seq, 'size': os.path.getsize(chunk_path)}

    if action == 'finalize':
        with open(f'{upload_dir}/meta.json') as f:
            meta = json.load(f)
        parts = sorted([p for p in os.listdir(upload_dir) if p.endswith('.part')])
        if len(parts) != meta['total_chunks']:
            raise HTTPException(400, detail=f'incomplete: got {len(parts)} of {meta["total_chunks"]}')
        ext = os.path.splitext(meta['filename'])[1].lower()
        if ext == '.pdf' and os.environ.get('R2_ACCOUNT_ID') and os.environ.get('R2_BUCKET'):
            try:
                prefix = _r2_prefix()
                name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + '.pdf'
                r2_key = prefix + 'tasks/' + name
                bucket = os.environ['R2_BUCKET']
                # Concat chunks to assembled temp file, then upload via proven upload_fileobj path.
                # Disk usage: same as before (already in /tmp). Memory usage: bounded by 4MB chunks.
                assembled = f'{upload_dir}/_assembled'
                with open(assembled, 'wb') as out:
                    for p in parts:
                        ppath = f'{upload_dir}/{p}'
                        with open(ppath, 'rb') as fh:
                            while True:
                                buf = fh.read(1024 * 1024)
                                if not buf: break
                                out.write(buf)
                        os.remove(ppath)
                # Upload assembled file to R2
                with open(assembled, 'rb') as fh:
                    _r2().upload_fileobj(
                        fh,
                        bucket,
                        r2_key,
                        ExtraArgs={'ContentType': 'application/pdf', 'ContentDisposition': 'inline'},
                    )
                os.remove(assembled)
                import shutil
                shutil.rmtree(upload_dir, ignore_errors=True)
                return {'ok': True, 'url': f"{os.environ['R2_PUBLIC_BASE'].rstrip('/')}/{r2_key}", 'type': 'pdf', 'name': meta.get('filename')}
            except Exception as e:
                print(f'chunk finalize R2 fail: {e}')
                raise HTTPException(500, detail=f'R2 fail: {e}')
        else:
            tasks_dir = os.path.join(UPLOADS_DIR, 'tasks')
            os.makedirs(tasks_dir, exist_ok=True)
            safe_name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + ext
            final_path = os.path.join(tasks_dir, safe_name)
            with open(final_path, 'wb') as out:
                for p in parts:
                    ppath = f'{upload_dir}/{p}'
                    with open(ppath, 'rb') as fh:
                        while True:
                            buf = fh.read(1024 * 1024)
                            if not buf: break
                            out.write(buf)
            import shutil
            shutil.rmtree(upload_dir, ignore_errors=True)
            return {'ok': True, 'path': f'/uploads/tasks/{safe_name}', 'type': 'image' if ext in {'.jpg','.jpeg','.png','.webp','.gif'} else 'file', 'name': meta.get('filename')}

    if action == 'abort':
        import shutil
        shutil.rmtree(upload_dir, ignore_errors=True)
        return {'ok': True}

    raise HTTPException(400, detail='action required (put|finalize|abort)')

@app.post("/upload/single")
async def upload_single(file: UploadFile = File(...)):
    """Upload a single file via XHR. Returns JSON with final URL/path.
    - PDF/image: uploaded to R2, returns CDN URL
    - Designed for parallel client-side uploads (one XHR per file).
    """
    if not file or not file.filename:
        raise HTTPException(400, detail='no file')
    ext = os.path.splitext(file.filename)[1].lower()
    img_exts = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
    r2_ready = os.environ.get('R2_ACCOUNT_ID') and os.environ.get('R2_BUCKET')

    tasks_dir = os.path.join(UPLOADS_DIR, 'tasks')
    os.makedirs(tasks_dir, exist_ok=True)
    name = datetime.now().strftime('%Y%m%d%H%M%S') + '_' + uuid.uuid4().hex[:8] + ext
    path = os.path.join(tasks_dir, name)
    file.file.seek(0)
    with open(path, 'wb') as out:
        out.write(file.file.read())

    # Both images and PDFs go to R2 if configured
    if r2_ready:
        try:
            if ext == '.pdf':
                file.file.seek(0)  # reset for re-read
                url = _upload_pdf_to_r2(file)
                return {'ok': True, 'url': url, 'type': 'pdf', 'name': file.filename}
            elif ext in img_exts:
                url = _upload_image_to_r2(path)
                if url:
                    return {'ok': True, 'url': url, 'type': 'image', 'name': file.filename}
                # R2 failed: fallback to local
        except Exception as e:
            print(f'upload/single: R2 fail for {file.filename}: {e}, fallback local')

    # Local fallback (or R2 not configured)
    compressed = _compress_image(path) if ext in img_exts else None
    final_path = compressed or path
    return {'ok': True, 'url': 'uploads/tasks/' + os.path.basename(final_path),
            'type': 'image' if ext in img_exts else ext.lstrip('.') or 'file',
            'name': file.filename}


# ── WEB PAGES ────────────────────────────────────────────────

@app.get("/public/tasks", response_class=HTMLResponse)
async def public_tasks(request: Request):
    # Deprecated alias — redirects to unified /tasks (same view, no separate template).
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/tasks", status_code=301)

@app.get("/add", response_class=HTMLResponse)
async def add(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context={"menu": "home", "pin_ok": _pin_ok(request), "app_version": APP_VERSION}
    )

@app.get("/gallery", response_class=HTMLResponse)
async def gallery(request: Request):
    """All designs (any status) + client-side status filter chips."""
    conn = get_db()
    designs = conn.execute(
        'SELECT * FROM designs ORDER BY id DESC LIMIT 200'
    ).fetchall()
    conn.close()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"designs": designs, "menu": "gallery", "pin_ok": _pin_ok(request), "app_version": APP_VERSION}
    )

@app.get("/inwork", response_class=HTMLResponse)
async def inwork(request: Request):
    """Products that have at least one task (pipeline board)."""
    conn = get_db()
    products = conn.execute(
        """
        SELECT d.id, d.model_name, d.status, d.image_path, d.created_at,
               (SELECT COUNT(*) FROM tasks t WHERE t.product_id = d.id) AS task_count,
               (SELECT COUNT(*) FROM tasks t WHERE t.product_id = d.id AND t.status = 'draft') AS task_draft,
               (SELECT COUNT(*) FROM tasks t WHERE t.product_id = d.id AND t.status = 'proses') AS task_proses,
               (SELECT COUNT(*) FROM tasks t WHERE t.product_id = d.id AND t.status = 'finish') AS task_finish
        FROM designs d
        WHERE EXISTS (SELECT 1 FROM tasks t WHERE t.product_id = d.id)
        ORDER BY d.id DESC
        """
    ).fetchall()
    conn.close()
    products_list = [dict(p) for p in products]
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "products": products_list,
            "menu": "inwork",
            "pin_ok": _pin_ok(request),
            "app_version": APP_VERSION,
        }
    )

@app.get("/finished", response_class=HTMLResponse)
async def finished(request: Request):
    """Legacy route — Finished merged into Gallery."""
    return RedirectResponse(url="/gallery", status_code=303)

@app.post("/add")
async def add_design(
    model_name: str = Form(...),
    status: str = Form("draft"),
    image: UploadFile = File(None)
):
    image_path = ""
    bg_promote = None  # (local_rel,) for background R2
    if image and image.filename:
        file_ext = os.path.splitext(image.filename)[1].lower() or '.jpg'
        if file_ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif'):
            file_ext = '.jpg'
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        abs_path = os.path.join(UPLOADS_DIR, filename)
        await _save_upload_stream(image, abs_path)
        import asyncio
        # Fast path: local only in request; R2 promotes after redirect
        image_path = await asyncio.to_thread(_store_design_image_local, abs_path)
        bg_promote = image_path

    conn = get_db()
    cur = conn.execute(
        'INSERT INTO designs (model_name, status, image_path, created_at) VALUES (?, ?, ?, ?)',
        (model_name, status, image_path, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    if bg_promote and new_id:
        import threading
        threading.Thread(
            target=_promote_design_image_r2,
            args=(new_id, bg_promote, None),
            daemon=True,
            name=f'r2-promote-{new_id}',
        ).start()
    return RedirectResponse(url="/gallery", status_code=303)

@app.get("/edit/{design_id}", response_class=HTMLResponse)
async def edit_page(request: Request, design_id: int, next: str = "/gallery"):
    # Admin-only (PIN unlock)
    redirect_to = next if isinstance(next, str) and next.startswith('/') and not next.startswith('//') else '/gallery'
    if not _pin_ok(request):
        return RedirectResponse(url=f"/pin?next=/edit/{design_id}?next={redirect_to}", status_code=303)
    conn = get_db()
    design = conn.execute('SELECT * FROM designs WHERE id = ?', (design_id,)).fetchone()
    conn.close()
    if not design:
        return RedirectResponse(url="/gallery", status_code=303)
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={
            "design": design,
            "menu": "edit",
            "pin_ok": True,
            "app_version": APP_VERSION,
            "redirect_to": redirect_to,
        }
    )

@app.post("/update/{design_id}")
async def update_design(
    request: Request,
    design_id: int,
    model_name: str = Form(...),
    status: str = Form("draft"),
    image: UploadFile = File(None),
    redirect_to: str = Form("/gallery"),
):
    if not _pin_ok(request):
        dest = redirect_to if isinstance(redirect_to, str) and redirect_to.startswith('/') and not redirect_to.startswith('//') else '/gallery'
        return RedirectResponse(url=f"/pin?next=/edit/{design_id}?next={dest}", status_code=303)
    conn = get_db()
    current = conn.execute('SELECT image_path FROM designs WHERE id = ?', (design_id,)).fetchone()
    if not current:
        conn.close()
        return RedirectResponse(url="/gallery", status_code=303)

    image_path = current['image_path']
    old_path = current['image_path']
    bg_local = None
    if image and image.filename:
        # Save NEW first — never delete old until new is on disk (prevents blank product on failed tunnel upload)
        file_ext = os.path.splitext(image.filename)[1].lower() or '.jpg'
        if file_ext not in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.heic', '.heif'):
            file_ext = '.jpg'
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{file_ext}"
        abs_path = os.path.join(UPLOADS_DIR, filename)
        nbytes = await _save_upload_stream(image, abs_path)
        print(f'update/{design_id}: received {nbytes} bytes → {filename}')
        import asyncio
        # FAST: local compress only; R2 promote in background after 303
        image_path = await asyncio.to_thread(_store_design_image_local, abs_path)
        bg_local = image_path
        print(f'update/{design_id}: local ready {image_path} in-request (R2 bg)')

    conn.execute(
        'UPDATE designs SET model_name=?, status=?, image_path=? WHERE id=?',
        (model_name, status, image_path, design_id)
    )
    conn.commit()
    conn.close()

    if bg_local:
        import threading
        threading.Thread(
            target=_promote_design_image_r2,
            args=(design_id, bg_local, old_path),
            daemon=True,
            name=f'r2-promote-{design_id}',
        ).start()

    dest = redirect_to if isinstance(redirect_to, str) and redirect_to.startswith('/') and not redirect_to.startswith('//') else '/gallery'
    return RedirectResponse(url=dest, status_code=303)

@app.post("/delete-image/{design_id}")
async def delete_image(design_id: int):
    conn = get_db()
    design = conn.execute('SELECT image_path FROM designs WHERE id = ?', (design_id,)).fetchone()
    if design and design['image_path']:
        # Delete from R2 if CDN URL
        if design['image_path'].startswith(os.environ.get('R2_PUBLIC_BASE', '')):
            _delete_r2_objects([design['image_path']])
        # Delete local file if exists
        full_path = os.path.join(BASE_DIR, design['image_path'])
        if os.path.exists(full_path):
            try: os.remove(full_path)
            except OSError: pass
    conn.execute('DELETE FROM designs WHERE id = ?', (design_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.get("/delete/{design_id}")
async def delete_design(design_id: int):
    conn = get_db()
    design = conn.execute('SELECT image_path FROM designs WHERE id = ?', (design_id,)).fetchone()
    if design and design['image_path']:
        # Delete from R2 if CDN URL
        if design['image_path'].startswith(os.environ.get('R2_PUBLIC_BASE', '')):
            _delete_r2_objects([design['image_path']])
        # Delete local file if exists
        full_path = os.path.join(BASE_DIR, design['image_path'])
        if os.path.exists(full_path):
            try: os.remove(full_path)
            except OSError: pass
    conn.execute('DELETE FROM designs WHERE id = ?', (design_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/gallery", status_code=303)


@app.post("/bulk-delete")
async def bulk_delete(ids: str = Form(...), redirect_to: str = Form("/inwork")):
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if not id_list:
        return RedirectResponse(url=redirect_to, status_code=303)
    conn = get_db()
    placeholders = ",".join("?" * len(id_list))
    rows = conn.execute(f'SELECT id, image_path FROM designs WHERE id IN ({placeholders})', id_list).fetchall()
    for r in rows:
        if r['image_path']:
            full_path = os.path.join(BASE_DIR, r['image_path'])
            if os.path.exists(full_path):
                try: os.remove(full_path)
                except OSError: pass
    conn.execute(f'DELETE FROM designs WHERE id IN ({placeholders})', id_list)
    conn.commit()
    conn.close()
    return RedirectResponse(url=redirect_to, status_code=303)

# ── PDF BUILDER ────────────────────────────────────────────────

@app.get("/pdf", response_class=HTMLResponse)
async def pdf_builder(request: Request):
    """Legacy alias — Gallery lives at /gallery now."""
    return RedirectResponse(url="/gallery", status_code=303)

@app.post("/pdf/preview")
async def pdf_preview(
    title: str = Form(...),
    notes: str = Form(""),
    selected_images: str = Form("")  # comma-separated image paths
):
    import json
    from uuid import uuid4
    img_paths = []
    if selected_images:
        for p in selected_images.split(","):
            p = p.strip()
            if p:
                full = os.path.join(BASE_DIR, p)
                if os.path.exists(full):
                    img_paths.append(full)

    if not img_paths:
        raise HTTPException(status_code=400, detail="No valid images selected")

    buf = _build_pdf(title, notes, img_paths)
    return StreamingResponse(
        BytesIO(buf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={title}.pdf"}
    )

@app.post("/pdf/save-draft")
async def pdf_save_draft(
    session_id: str = Form(...),
    title: str = Form(...),
    notes: str = Form(""),
    selected_images: str = Form("")
):
    import json
    from uuid import uuid4
    conn = get_db()
    conn.execute(
        'INSERT INTO pdf_drafts (session_id, title, notes, images_json, created_at) VALUES (?, ?, ?, ?, ?)',
        (session_id, title, notes, json.dumps(selected_images.split(",") if selected_images else []),
         datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()
    return {"ok": True, "session_id": session_id}

@app.get("/pdf/drafts", response_class=HTMLResponse)
async def pdf_drafts(request: Request):
    conn = get_db()
    drafts = conn.execute('SELECT * FROM pdf_drafts ORDER BY id DESC').fetchall()
    conn.close()
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"menu": "pdf_drafts", "drafts": drafts, "pin_ok": _pin_ok(request), "app_version": APP_VERSION}
    )

@app.get("/pdf/draft/{draft_id}/download")
async def pdf_draft_download(draft_id: int):
    import json
    from uuid import uuid4
    conn = get_db()
    draft = conn.execute('SELECT * FROM pdf_drafts WHERE id = ?', (draft_id,)).fetchone()
    conn.close()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    img_paths = []
    for p in json.loads(draft['images_json'] or "[]"):
        p = p.strip()
        if p:
            full = os.path.join(BASE_DIR, p)
            if os.path.exists(full):
                img_paths.append(full)

    buf = _build_pdf(draft['title'], draft['notes'] or "", img_paths)
    safe_title = "".join(c for c in draft['title'] if c.isalnum() or c in " -_").strip() or "workflow-pdf"
    return StreamingResponse(
        BytesIO(buf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_title}.pdf"}
    )

@app.post("/pdf/draft/{draft_id}/delete")
async def pdf_draft_delete(draft_id: int):
    conn = get_db()
    conn.execute('DELETE FROM pdf_drafts WHERE id = ?', (draft_id,))
    conn.commit()
    conn.close()
    return RedirectResponse(url="/pdf/drafts", status_code=303)


def _build_pdf(title: str, notes: str, img_paths: list) -> bytes:
    buf = BytesIO()

    PAGE_BG = colors.HexColor('#111111')
    FG = colors.HexColor('#ffffff')
    DIM = colors.HexColor('#a3a3a3')

    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFillColor(PAGE_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        'Brand',
        parent=styles['Normal'],
        fontSize=9,
        textColor=DIM,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        textColor=FG,
        spaceAfter=6,
        alignment=TA_CENTER,
    )
    note_style = ParagraphStyle(
        'Note',
        parent=styles['Normal'],
        fontSize=10,
        textColor=DIM,
        leading=14,
    )
    caption_style = ParagraphStyle(
        'Caption',
        parent=styles['Normal'],
        fontSize=9,
        textColor=DIM,
        alignment=TA_CENTER,
    )

    story = []

    # Header
    story.append(Paragraph("WORKFLOW PLANNER", brand_style))
    story.append(Paragraph(title, title_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2a2a2a')))
    story.append(Spacer(1, 12))

    # Notes
    if notes.strip():
        story.append(Paragraph(f"<b>Notes:</b> {notes}", note_style))
        story.append(Spacer(1, 16))

    # Images
    for i, path in enumerate(img_paths, 1):
        try:
            img = Image(path, width=14*cm, height=10*cm)
            img.hAlign = 'CENTER'
            story.append(img)
            story.append(Paragraph(f"Halaman {i}", caption_style))
            story.append(Spacer(1, 16))
        except Exception:
            story.append(Paragraph(f"[Image {i}: could not load]", note_style))
            story.append(Spacer(1, 12))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#2a2a2a')))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} · Workflow Planner",
        caption_style
    ))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()




@app.post("/upload/express")
async def upload_express_proxy(request: Request):
    """
    Same-origin proxy: frontend (HTTPS via Cloudflare) → FastAPI :8080 → Express :8081 → R2.
    Avoids mixed-content block (HTTPS page cannot fetch plain HTTP).
    Streams multipart through; returns the {url, size, success} JSON that Express emits.
    """
    import httpx
    try:
        body = await request.body()
        ct = request.headers.get("content-type", "")
        if not ct:
            return {"success": False, "error": "missing content-type"}
        async with httpx.AsyncClient(timeout=httpx.Timeout(310.0, connect=10.0)) as cli:
            r = await cli.post("http://127.0.0.1:8082/upload/r2", content=body, headers={"content-type": ct})
        try:
            return JSONResponse(content=r.json(), status_code=r.status_code)
        except Exception:
            return JSONResponse(content={"success": False, "error": f"express returned {r.status_code}: {r.text[:200]}"}, status_code=502)
    except httpx.ReadTimeout:
        return JSONResponse(content={"success": False, "error": "express timeout"}, status_code=504)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": f"proxy: {e}"}, status_code=500)

@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context=_welcome_context(request)
    )




@app.post("/admin/stop-local", include_in_schema=False)
async def admin_stop_local(request: Request):
    """LOCAL only: exit python so user can paste update command (9router-style)."""
    if not _is_local_starter():
        return JSONResponse({"status": "error", "error": "stop-local only on laptop starter"}, status_code=403)
    try:
        await request.json()
    except Exception:
        pass
    import threading
    def _die():
        import time
        time.sleep(0.4)
        try:
            os._exit(0)
        except Exception:
            raise SystemExit(0)
    threading.Thread(target=_die, daemon=True).start()
    return JSONResponse({
        "status": "ok",
        "message": "Stopping. Paste update command in terminal, then start.bat",
        "updateCommand": _local_update_command(),
        "channel": "local",
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get('PORT', 8081)))
