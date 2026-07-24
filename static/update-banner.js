/**
 * Workflow Planner update banner
 * - LOCAL/STARTER (channel=local): one-click git pull + pip (anyone) — 9router-style
 * - PROD VPS: operator-only deploy via deploy.js (admin PIN)
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
      '#' + BANNER_ID + ' .kub-label{flex:1;min-width:180px}',
      '#' + BANNER_ID + ' .kub-title{font-weight:700;color:#4ade80;font-size:12px;margin-bottom:2px}',
      '#' + BANNER_ID + ' .kub-sub{opacity:.75;font-size:12px}',
      '#' + BANNER_ID + ' .kub-actions{display:flex;align-items:center;gap:8px;flex-wrap:wrap}',
      '#' + BANNER_ID + ' .kub-btn{border:0;border-radius:8px;padding:7px 12px;font-weight:700;',
      'font-size:12px;cursor:pointer;color:#fff;background:#16a34a;text-decoration:none;display:inline-block}',
      '#' + BANNER_ID + ' .kub-btn:disabled{opacity:.55;cursor:wait}',
      '#' + BANNER_ID + ' .kub-btn.secondary{background:transparent;color:#9ca3af;border:1px solid #334155}',
      '#' + BANNER_ID + ' .kub-msg{width:100%;font-size:11px;opacity:.8}',
      '@media (max-width:520px){#' + BANNER_ID + '{left:8px;right:8px;bottom:8px}}',
    ].join('');
    document.head.appendChild(st);
  }

  function removeBanner() {
    var el = document.getElementById(BANNER_ID);
    if (el) el.remove();
  }

  function showLocalBanner(d) {
    ensureStyles();
    var latest = d.latestVersion || '';
    var current = d.currentVersion || d.version || '';
    var el = document.getElementById(BANNER_ID);
    if (!el) {
      el = document.createElement('div');
      el.id = BANNER_ID;
      document.body.appendChild(el);
    }
    el.innerHTML =
      '<div class="kub-label">' +
      '<div class="kub-title">Update tersedia</div>' +
      '<div class="kub-sub">Sekarang ' + esc(current) + (latest ? ' → ' + esc(latest) : '') +
      ' · data + .env aman · satu klik</div>' +
      '</div>' +
      '<div class="kub-actions">' +
      '<button type="button" class="kub-btn" data-act="update">Update</button>' +
      '<button type="button" class="kub-btn secondary" data-act="dismiss">Nanti</button>' +
      '</div>' +
      '<div class="kub-msg" data-msg hidden></div>';
    el.querySelector('[data-act="dismiss"]').onclick = removeBanner;
    el.querySelector('[data-act="update"]').onclick = function () {
      runLocalUpdate(el.querySelector('[data-act="update"]'), el.querySelector('[data-msg]'));
    };
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
      '<div class="kub-title">Operator: new release v' + esc(latestLabel) + '</div>' +
      '<div class="kub-sub">Running ' + esc(current) + ' · ' + esc(app) + ' · admin only</div>' +
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
      up.onclick = function () { runProdUpdate(up, el.querySelector('[data-msg]'), latest); };
    }
  }

  function runLocalUpdate(btn, msgEl) {
    if (btn.disabled) return;
    if (!confirm('Update Workflow Planner di laptop ini?\n\n· git pull dari GitHub\n· pip install requirements\n· .env + data/shoes.db TETAP\n\nApp akan reload setelah selesai.')) return;
    btn.disabled = true;
    btn.textContent = 'Updating…';
    if (msgEl) {
      msgEl.hidden = false;
      msgEl.textContent = 'Pull + install… (bisa 10–60 dtk)';
    }
    fetch('/admin/deploy', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Accept': 'application/json', 'Content-Type': 'application/json' },
      cache: 'no-store',
      body: JSON.stringify({ channel: 'local' }),
    })
      .then(function (r) {
        return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; });
      })
      .then(function (res) {
        if (!res.ok || (res.body && res.body.status === 'error')) {
          var err = (res.body && (res.body.error || res.body.message || res.body.stderr)) || ('HTTP ' + res.status);
          if (msgEl) msgEl.textContent = 'Gagal: ' + err;
          btn.disabled = false;
          btn.textContent = 'Retry';
          return;
        }
        if (msgEl) msgEl.textContent = 'OK ' + (res.body && res.body.version ? res.body.version : '') + ' — reload…';
        setTimeout(function () { location.reload(); }, 1200);
      })
      .catch(function (e) {
        if (msgEl) msgEl.textContent = 'Network/error: ' + (e && e.message ? e.message : e);
        btn.disabled = false;
        btn.textContent = 'Retry';
      });
  }

  function runProdUpdate(btn, msgEl, latest) {
    if (btn.disabled) return;
    var ver = latest ? ('v' + String(latest).replace(/^v/, '')) : 'latest';
    if (!confirm(
      'OPERATOR: install official ' + ver + ' ke PROD?\n\n' +
      'Semua user langsung pindah ke versi ini.'
    )) return;
    btn.disabled = true;
    btn.textContent = 'Updating…';
    if (msgEl) {
      msgEl.hidden = false;
      msgEl.textContent = 'Deploying ' + ver + '…';
    }
    var headers = { 'Accept': 'application/json', 'Content-Type': 'application/json' };
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
        return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; });
      })
      .then(function (res) {
        if (!res.ok || (res.body && res.body.status === 'error')) {
          var err = (res.body && (res.body.error || res.body.message || res.body.stderr)) || ('HTTP ' + res.status);
          if (msgEl) msgEl.textContent = 'Gagal: ' + err;
          btn.disabled = false;
          btn.textContent = 'Retry';
          return;
        }
        if (msgEl) msgEl.textContent = 'OK — reloading…';
        setTimeout(function () { location.reload(); }, 2500);
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
        // also treat SHA mismatch fields if present
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
        try { localStorage.setItem(KEY_PREFIX + appKey, ver); } catch (e) {}
      })
      .catch(function (e) {
        try { console.warn('[workflow-update]', e && e.message ? e.message : e); } catch (x) {}
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', check);
  } else {
    check();
  }
  // Burst polls early (orphan force-push / slow fetch), then settle
  var n = 0;
  var burst = setInterval(function () {
    n += 1;
    check();
    if (n >= 6) clearInterval(burst);
  }, 8000);
  setInterval(check, POLL_MS);
})();
