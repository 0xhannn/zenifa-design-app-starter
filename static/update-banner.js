/**
 * Workflow Planner update banner
 * LOCAL (9router-style): show command → copy → stop app → paste in terminal → start.bat
 * PROD VPS: operator deploy.js (admin PIN)
 */
(function () {
  var POLL_MS = 60000;
  var BANNER_ID = 'king-update-banner';
  var KEY_PREFIX = 'kingAppVer:';

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function ensureStyles() {
    if (document.getElementById('king-update-banner-css')) return;
    var st = document.createElement('style');
    st.id = 'king-update-banner-css';
    st.textContent = [
      '#' + BANNER_ID + '{position:fixed;left:12px;right:12px;bottom:12px;z-index:10000;',
      'display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 14px;',
      'border-radius:12px;background:linear-gradient(135deg,#0f1b2e,#16263d);',
      'border:1px solid rgba(34,197,94,.35);box-shadow:0 12px 40px rgba(0,0,0,.45);',
      'color:#e8edf3;font:13px/1.35 system-ui,sans-serif}',
      '#' + BANNER_ID + ' .kub-label{flex:1;min-width:160px}',
      '#' + BANNER_ID + ' .kub-title{font-weight:700;color:#4ade80;font-size:12px;margin-bottom:2px}',
      '#' + BANNER_ID + ' .kub-sub{opacity:.75;font-size:12px}',
      '#' + BANNER_ID + ' .kub-cmd{',
      'width:100%;margin-top:4px;padding:8px 10px;border-radius:8px;',
      'background:#0b1220;border:1px solid #334155;color:#a7f3d0;',
      'font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;',
      'word-break:break-all;user-select:all}',
      '#' + BANNER_ID + ' .kub-steps{width:100%;font-size:11px;opacity:.7;margin-top:2px}',
      '#' + BANNER_ID + ' .kub-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}',
      '#' + BANNER_ID + ' .kub-btn{border:0;border-radius:8px;padding:7px 12px;font-weight:700;',
      'font-size:12px;cursor:pointer;color:#fff;background:#16a34a;text-decoration:none;display:inline-block}',
      '#' + BANNER_ID + ' .kub-btn:disabled{opacity:.55;cursor:wait}',
      '#' + BANNER_ID + ' .kub-btn.secondary{background:transparent;color:#9ca3af;border:1px solid #334155}',
      '#' + BANNER_ID + ' .kub-msg{width:100%;font-size:11px;opacity:.85}',
      '@media (max-width:520px){#' + BANNER_ID + '{left:8px;right:8px;bottom:8px}}',
    ].join('');
    document.head.appendChild(st);
  }

  function removeBanner() {
    var el = document.getElementById(BANNER_ID);
    if (el) el.remove();
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      try {
        var ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        var ok = document.execCommand('copy');
        document.body.removeChild(ta);
        ok ? resolve() : reject(new Error('copy failed'));
      } catch (e) {
        reject(e);
      }
    });
  }

  function showLocalBanner(d) {
    ensureStyles();
    var latest = d.latestVersion || '';
    var current = d.currentVersion || d.version || '';
    var isWin = /Win/i.test(navigator.platform || '') || /Windows/i.test(navigator.userAgent || '');
    var cmd =
      (isWin && (d.updateCommandWin || d.updateCommand)) ||
      d.updateCommand ||
      d.updateCmd ||
      d.updateCommandPosix ||
      (isWin ? 'update.bat' : 'git fetch origin --tags --prune && git checkout -B main origin/main && pip install -r requirements.txt');
    var el = document.getElementById(BANNER_ID);
    if (!el) {
      el = document.createElement('div');
      el.id = BANNER_ID;
      document.body.appendChild(el);
    }
    el.innerHTML =
      '<div class="kub-label">' +
      '<div class="kub-title">Update tersedia</div>' +
      '<div class="kub-sub">Sekarang ' +
      esc(current) +
      (latest ? ' → ' + esc(latest) : '') +
      (d.currentSha && d.latestSha ? ' · ' + esc(d.currentSha) + '→' + esc(d.latestSha) : '') +
      '</div>' +
      '</div>' +
      '<div class="kub-cmd" data-cmd>' +
      esc(cmd) +
      '</div>' +
      '<div class="kub-steps">1) Copy command &amp; stop app · 2) Paste di CMD/PowerShell folder app (biasanya update.bat) · 3) start.bat</div>' +
      '<div class="kub-actions">' +
      '<button type="button" class="kub-btn" data-act="copy-stop">Copy command &amp; stop app</button>' +
      '<button type="button" class="kub-btn secondary" data-act="copy-only">Copy only</button>' +
      '<button type="button" class="kub-btn secondary" data-act="dismiss">Nanti</button>' +
      '</div>' +
      '<div class="kub-msg" data-msg hidden></div>';

    el.querySelector('[data-act="dismiss"]').onclick = removeBanner;
    el.querySelector('[data-act="copy-only"]').onclick = function () {
      var msgEl = el.querySelector('[data-msg]');
      copyText(cmd)
        .then(function () {
          if (msgEl) {
            msgEl.hidden = false;
            msgEl.textContent = 'Command disalin. Tutup app, paste di terminal folder app, lalu start.bat';
          }
        })
        .catch(function () {
          if (msgEl) {
            msgEl.hidden = false;
            msgEl.textContent = 'Gagal copy — select manual di kotak command.';
          }
        });
    };
    el.querySelector('[data-act="copy-stop"]').onclick = function () {
      runLocalCopyStop(el.querySelector('[data-act="copy-stop"]'), el.querySelector('[data-msg]'), cmd);
    };
  }

  function runLocalCopyStop(btn, msgEl, cmd) {
    if (btn.disabled) return;
    btn.disabled = true;
    btn.textContent = 'Copy…';
    if (msgEl) {
      msgEl.hidden = false;
      msgEl.textContent = 'Menyalin command…';
    }
    copyText(cmd)
      .then(function () {
        if (msgEl) msgEl.textContent = 'Tersalin. Stop app… paste command di terminal, lalu start.bat';
        btn.textContent = 'Stopping…';
        return fetch('/admin/stop-local', {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          cache: 'no-store',
          body: JSON.stringify({ reason: 'update' }),
        });
      })
      .then(function (r) {
        if (!r) return;
        return r.json().catch(function () { return {}; }).then(function (j) {
          return { ok: r.ok, body: j };
        });
      })
      .then(function (res) {
        if (!res) return;
        if (msgEl) {
          msgEl.textContent =
            'App stop. Paste command di PowerShell/CMD (folder app) → tunggu Done → start.bat';
        }
        // server may already be dead
      })
      .catch(function (e) {
        // stop often aborts the connection — still OK if copy succeeded
        if (msgEl) {
          msgEl.textContent =
            'Command di clipboard. Kalau app masih hidup, tutup jendela terminal app, paste command, lalu start.bat';
        }
        btn.disabled = false;
        btn.textContent = 'Copy command & stop app';
      });
  }

  function showProdBanner(d) {
    ensureStyles();
    var latest = d.latestVersion || d.version || '';
    var current = d.currentVersion || d.version || '';
    var app = d.app || 'app';
    var releases = d.releasesUrl || '';
    var latestLabel = String(latest).replace(/^v/, '');
    var el = document.getElementById(BANNER_ID);
    if (!el) {
      el = document.createElement('div');
      el.id = BANNER_ID;
      document.body.appendChild(el);
    }
    el.innerHTML =
      '<div class="kub-label">' +
      '<div class="kub-title">Operator: new release v' +
      esc(latestLabel) +
      '</div>' +
      '<div class="kub-sub">Running ' +
      esc(current) +
      ' · ' +
      esc(app) +
      ' · admin only</div>' +
      '</div>' +
      '<div class="kub-actions">' +
      '<button type="button" class="kub-btn" data-act="update">Update now</button>' +
      (releases
        ? '<a class="kub-btn secondary" href="' + esc(releases) + '" target="_blank" rel="noopener">Releases</a>'
        : '') +
      '<button type="button" class="kub-btn secondary" data-act="dismiss">×</button>' +
      '</div>' +
      '<div class="kub-msg" data-msg hidden></div>';
    el.querySelector('[data-act="dismiss"]').onclick = removeBanner;
    var up = el.querySelector('[data-act="update"]');
    if (up) {
      up.onclick = function () {
        runProdUpdate(up, el.querySelector('[data-msg]'), latest);
      };
    }
  }

  function runProdUpdate(btn, msgEl, latest) {
    if (btn.disabled) return;
    var ver = latest ? 'v' + String(latest).replace(/^v/, '') : 'latest';
    if (
      !confirm(
        'OPERATOR: install official ' + ver + ' ke PROD?\n\n' + 'Semua user langsung pindah ke versi ini.'
      )
    )
      return;
    btn.disabled = true;
    btn.textContent = 'Updating…';
    if (msgEl) {
      msgEl.hidden = false;
      msgEl.textContent = 'Deploying ' + ver + '…';
    }
    var headers = { Accept: 'application/json', 'Content-Type': 'application/json' };
    try {
      var tok = sessionStorage.getItem('kingDeployToken') || localStorage.getItem('kingDeployToken');
      if (tok) headers['Authorization'] = 'Bearer ' + tok;
    } catch (e) {}
    fetch('/admin/deploy', {
      method: 'POST',
      credentials: 'include',
      headers: headers,
      cache: 'no-store',
      body: JSON.stringify({ version: ver || 'latest' }),
    })
      .then(function (r) {
        return r.json().then(function (j) {
          return { ok: r.ok, status: r.status, body: j };
        });
      })
      .then(function (res) {
        if (!res.ok || (res.body && res.body.status === 'error')) {
          var err =
            (res.body && (res.body.error || res.body.message || res.body.stderr)) ||
            'HTTP ' + res.status;
          if (msgEl) msgEl.textContent = 'Gagal: ' + err;
          btn.disabled = false;
          btn.textContent = 'Retry';
          return;
        }
        if (msgEl) msgEl.textContent = 'OK — reloading…';
        setTimeout(function () {
          location.reload();
        }, 2500);
      })
      .catch(function (e) {
        if (msgEl) msgEl.textContent = 'Network/error: ' + (e && e.message ? e.message : e);
        btn.disabled = false;
        btn.textContent = 'Retry';
      });
  }

  function check() {
    fetch('/api/version', { cache: 'no-store', credentials: 'include' })
      .then(function (r) {
        if (!r.ok) throw new Error('version HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        var appKey = d.app || 'app';
        var ver = d.version || d.currentVersion || '';
        var has = d.hasUpdate === true || d.hasUpdate === 1 || d.hasUpdate === 'true';
        if (!has && d.currentSha && d.latestSha && d.currentSha !== d.latestSha) has = true;
        if (has) {
          if (d.channel === 'local' || d.isLocal === true) {
            showLocalBanner(d);
          } else if (d.canDeploy === true) {
            showProdBanner(d);
          } else {
            removeBanner();
          }
        } else {
          removeBanner();
        }
        try {
          localStorage.setItem(KEY_PREFIX + appKey, ver);
        } catch (e) {}
      })
      .catch(function (e) {
        try {
          console.warn('[workflow-update]', e && e.message ? e.message : e);
        } catch (x) {}
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', check);
  } else {
    check();
  }
  var n = 0;
  var burst = setInterval(function () {
    n += 1;
    check();
    if (n >= 6) clearInterval(burst);
  }, 8000);
  setInterval(check, POLL_MS);
})();
