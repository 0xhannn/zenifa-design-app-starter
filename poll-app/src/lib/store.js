/**
 * Hybrid store: localStorage first (offline / same-browser),
 * plus backend /api/polls for shareable cross-device links.
 *
 * Auth: create + list = admin PIN session only.
 * Vote + fetch single poll = public.
 */

const LS_KEY = 'workflow_polls_v1'

function readLocalAll() {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return {}
    const data = JSON.parse(raw)
    return data && typeof data === 'object' ? data : {}
  } catch {
    return {}
  }
}

function writeLocalAll(map) {
  localStorage.setItem(LS_KEY, JSON.stringify(map))
}

export function shortId(len = 8) {
  const alphabet = 'abcdefghijklmnopqrstuvwxyz0123456789'
  const arr = new Uint8Array(len)
  crypto.getRandomValues(arr)
  return Array.from(arr, (b) => alphabet[b % alphabet.length]).join('')
}

export function listLocalPolls() {
  const map = readLocalAll()
  return Object.values(map).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0))
}

export function getLocalPoll(id) {
  const map = readLocalAll()
  return map[id] || null
}

export function saveLocalPoll(poll) {
  const map = readLocalAll()
  map[poll.id] = poll
  writeLocalAll(map)
  return poll
}

export function deleteLocalPoll(id) {
  const map = readLocalAll()
  delete map[id]
  writeLocalAll(map)
}

/** Admin-only hard delete on server + wipe local cache. */
export async function deletePollRemote(pollId) {
  const res = await fetch(`/api/polls/${encodeURIComponent(pollId)}`, {
    method: 'DELETE',
    headers: { Accept: 'application/json' },
    credentials: 'same-origin',
  })
  if (res.status === 401) {
    const err = new Error('Admin PIN required')
    err.code = 401
    throw err
  }
  if (res.status === 404) {
    // still clear local so UI can recover
    try {
      deleteLocalPoll(pollId)
    } catch (_) {}
    throw new Error('Poll tidak ditemukan')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Gagal hapus poll (${res.status})`)
  }
  try {
    deleteLocalPoll(pollId)
  } catch (_) {}
  return { ok: true, id: pollId }
}

/** Probe admin PIN session (cookie). */
export async function checkAdminAuth() {
  try {
    const res = await fetch('/api/polls/auth', {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
    if (res.ok) {
      const data = await res.json()
      return Boolean(data.pin_ok || data.admin)
    }
  } catch (_) {}
  return false
}

export function pinLoginUrl(nextPath = '/poll/new') {
  // /pin form uses ? via referer; we pass next as query for SPA deep-link after login
  const next = encodeURIComponent(nextPath)
  return `/pin?next=${next}`
}

/** Prefer API when available; fall back to localStorage. Public. */
export async function fetchPoll(id) {
  try {
    const res = await fetch(`/api/polls/${encodeURIComponent(id)}`, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
    if (res.ok) {
      const poll = await res.json()
      try {
        saveLocalPoll(poll)
      } catch (_) {}
      return { poll, source: 'api' }
    }
  } catch (_) {}

  const local = getLocalPoll(id)
  if (local) return { poll: local, source: 'local' }
  return { poll: null, source: 'none' }
}

/**
 * List polls — API requires admin.
 * Non-admin: empty remote; do NOT pretend local-only drafts are server polls.
 */
export async function listPolls() {
  const byId = {}
  try {
    const res = await fetch('/api/polls', {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    })
    if (res.status === 401) {
      return { polls: [], admin: false, unauthorized: true }
    }
    if (res.ok) {
      const remote = await res.json()
      for (const p of remote || []) {
        if (!p?.id) continue
        const prev = getLocalPoll(p.id)
        byId[p.id] = {
          id: p.id,
          title: p.title || prev?.title || 'Untitled',
          description: prev?.description || '',
          creatorName: p.creatorName || prev?.creatorName || '—',
          designs: prev?.designs || Array.from({ length: p.designCount || 0 }),
          designCount: p.designCount ?? prev?.designs?.length ?? 0,
          votes: prev?.votes || Array.from({ length: p.voteCount || 0 }),
          voteCount: p.voteCount ?? prev?.votes?.length ?? 0,
          createdAt: p.createdAt || prev?.createdAt || 0,
          source: 'api',
        }
      }
      return {
        polls: Object.values(byId).sort((a, b) => (b.createdAt || 0) - (a.createdAt || 0)),
        admin: true,
        unauthorized: false,
      }
    }
  } catch (_) {}
  // Network fail — show local cache only for offline admin convenience
  const local = listLocalPolls().map((p) => ({ ...p, source: 'local' }))
  return { polls: local, admin: null, unauthorized: false }
}

/** Create poll — admin only. NO local fallback (would bypass PIN). */
export async function createPollRemote(poll) {
  const res = await fetch('/api/polls', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'same-origin',
    body: JSON.stringify(poll),
  })
  if (res.status === 401) {
    const err = new Error('Admin PIN required')
    err.code = 401
    throw err
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Gagal buat poll (${res.status})`)
  }
  const saved = await res.json()
  try {
    saveLocalPoll(saved)
  } catch (_) {}
  return { poll: saved, source: 'api' }
}

export async function submitVoteRemote(pollId, payload) {
  // payload: { voterName, designIds: string[] }
  try {
    const res = await fetch(`/api/polls/${encodeURIComponent(pollId)}/vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(payload),
    })
    if (res.ok) {
      const poll = await res.json()
      try {
        saveLocalPoll(poll)
      } catch (_) {}
      return { poll, source: 'api' }
    }
    if (res.status === 409) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Nama ini sudah vote')
    }
  } catch (e) {
    if (e.message && e.message !== 'Failed to fetch') throw e
  }

  // local fallback only when API unreachable
  const poll = getLocalPoll(pollId)
  if (!poll) throw new Error('Poll tidak ditemukan')
  const name = String(payload.voterName || '').trim()
  if (!name) throw new Error('Nama wajib diisi')
  if (!Array.isArray(payload.designIds) || !payload.designIds.length) {
    throw new Error('Pilih minimal 1 desain')
  }
  poll.votes = poll.votes || []
  if (poll.votes.some((v) => v.voterName.toLowerCase() === name.toLowerCase())) {
    throw new Error('Nama ini sudah vote di browser ini')
  }
  poll.votes.push({
    voterName: name,
    designIds: payload.designIds,
    at: Date.now(),
  })
  saveLocalPoll(poll)
  return { poll, source: 'local' }
}

export function tallyVotes(poll) {
  const designs = poll?.designs || []
  const votes = poll?.votes || []
  const totalVoters = votes.length
  const counts = Object.fromEntries(designs.map((d) => [d.id, 0]))
  for (const v of votes) {
    for (const id of v.designIds || []) {
      if (counts[id] != null) counts[id] += 1
    }
  }
  const rows = designs.map((d) => {
    const count = counts[d.id] || 0
    const pct = totalVoters ? Math.round((count / totalVoters) * 100) : 0
    return { ...d, count, pct }
  })
  rows.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
  return { rows, totalVoters }
}

export function shareUrl(pollId) {
  const base = window.location.origin
  return `${base}/poll/${pollId}`
}
