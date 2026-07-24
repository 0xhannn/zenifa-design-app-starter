import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { deletePollRemote, listPolls, pinLoginUrl, shareUrl } from '../lib/store'

function formatWhen(ts) {
  if (!ts) return '—'
  try {
    const d = typeof ts === 'number' ? new Date(ts) : new Date(ts)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Jakarta',
    })
  } catch {
    return '—'
  }
}

/**
 * Riwayat Team Poll — admin only for full server list.
 * Non-admin: gate + CTA login; public voters use shared /poll/:id.
 */
export default function PollHistory() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [admin, setAdmin] = useState(null)
  const [copiedId, setCopiedId] = useState('')
  const [deletingId, setDeletingId] = useState('')
  const [q, setQ] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { polls, admin: isAdmin, unauthorized } = await listPolls()
      setItems(polls || [])
      setAdmin(unauthorized ? false : isAdmin)
    } catch (e) {
      setError(e.message || 'Gagal load riwayat')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function copyLink(id) {
    const url = shareUrl(id)
    try {
      await navigator.clipboard.writeText(url)
      setCopiedId(id)
      setTimeout(() => setCopiedId(''), 1600)
    } catch {
      window.prompt('Copy link:', url)
    }
  }

  async function handleDelete(p) {
    const title = p.title || p.id
    const ok = window.confirm(
      `Hapus poll "${title}"?\n\nLink vote & semua suara ikut hilang. Tidak bisa di-undo.`,
    )
    if (!ok) return
    setDeletingId(p.id)
    setError('')
    try {
      await deletePollRemote(p.id)
      setItems((prev) => prev.filter((x) => x.id !== p.id))
    } catch (e) {
      if (e.code === 401) {
        setError('Session admin habis — login PIN dulu.')
      } else {
        setError(e.message || 'Gagal hapus poll')
      }
    } finally {
      setDeletingId('')
    }
  }

  const filtered = items.filter((p) => {
    if (!q.trim()) return true
    const s = q.toLowerCase()
    return (
      (p.title || '').toLowerCase().includes(s) ||
      (p.creatorName || '').toLowerCase().includes(s) ||
      (p.id || '').toLowerCase().includes(s)
    )
  })

  if (!loading && admin === false) {
    return (
      <div className="poll-page">
        <div className="zen-blob left-0 top-0 h-40 w-40 bg-cyan-300" />
        <div className="zen-blob right-0 top-12 h-32 w-32 bg-pink-300" />
        <div className="zen-card zen-card-pad relative mx-auto max-w-md space-y-4 text-center">
          <div className="text-4xl">🔐</div>
          <h1 className="poll-title text-xl sm:text-2xl">Riwayat · Admin only</h1>
          <p className="poll-subtitle">
            Daftar semua poll cuma buat admin. Voter cukup buka link share{' '}
            <code className="rounded-md bg-slate-100 px-1.5 py-0.5 text-xs text-slate-700">
              /poll/&lt;id&gt;
            </code>
            .
          </p>
          <a href={pinLoginUrl('/poll')} className="zen-btn-primary inline-flex w-full justify-center">
            Login PIN →
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="poll-page poll-stack">
      <div className="zen-blob -left-6 top-0 h-40 w-40 bg-cyan-300" />
      <div className="zen-blob right-0 top-20 h-32 w-32 bg-pink-300" />

      <header className="relative z-[1] space-y-3">
        <p className="poll-kicker">Workflow Planner · Design Feedback · Admin</p>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="poll-title">Riwayat Poll</h1>
            <p className="poll-subtitle">Semua survey / team poll di server.</p>
          </div>
          <Link to="/poll/new" className="zen-btn-primary shrink-0">
            + Buat Poll
          </Link>
        </div>
      </header>

      <div className="relative z-[1] flex flex-col gap-2.5 sm:flex-row sm:items-center">
        <input
          className="zen-input flex-1"
          placeholder="Cari judul / pembuat / id…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <button type="button" className="zen-btn-secondary shrink-0" onClick={load}>
          Refresh
        </button>
      </div>

      {loading && (
        <div className="relative z-[1] space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-28 shimmer rounded-2xl" />
          ))}
        </div>
      )}

      {error && (
        <div className="relative z-[1] rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
          {error}
        </div>
      )}

      {!loading && !filtered.length && (
        <div className="zen-card zen-card-pad relative z-[1] space-y-3 text-center">
          <div className="text-4xl">📭</div>
          <p className="poll-title text-lg sm:text-xl">Belum ada poll</p>
          <Link to="/poll/new" className="zen-btn-primary inline-flex">
            Buat yang pertama
          </Link>
        </div>
      )}

      <ul className="relative z-[1] space-y-3.5">
        {filtered.map((p) => {
          const designs = p.designCount ?? p.designs?.length ?? 0
          const voters = p.voteCount ?? p.votes?.length ?? 0
          const busy = deletingId === p.id
          return (
            <li key={p.id} className="zen-card overflow-hidden">
              <div className="zen-card-pad">
                <div className="zen-card-header !mb-0 !border-0 !pb-0">
                  <div className="min-w-0 flex-1">
                    <h2 className="truncate font-heading text-lg font-extrabold text-[#111827] sm:text-xl">
                      {p.title || 'Untitled'}
                    </h2>
                    <p className="poll-meta mt-1.5">
                      <strong>{p.creatorName || '—'}</strong>
                      <span className="mx-1.5 text-slate-300">·</span>
                      {formatWhen(p.createdAt)}
                      <span className="mx-1.5 text-slate-300">·</span>
                      <code className="rounded-md bg-slate-100 px-1.5 py-0.5 text-[11px] font-semibold text-[#111827]">
                        {p.id}
                      </code>
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-[#111827]">
                        {designs} desain
                      </span>
                      <span className="inline-flex items-center rounded-full bg-cyan-50 px-2.5 py-1 text-[11px] font-bold text-cyan-800">
                        {voters} voter
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 border-t border-slate-100 pt-4">
                  <Link to={`/poll/${p.id}`} className="zen-btn-secondary zen-btn-sm">
                    Vote page
                  </Link>
                  <Link to={`/poll/${p.id}/stats`} className="zen-btn-secondary zen-btn-sm">
                    📊 Lihat Hasil
                  </Link>
                  <button
                    type="button"
                    className="zen-btn-primary zen-btn-sm !text-white"
                    onClick={() => copyLink(p.id)}
                  >
                    {copiedId === p.id ? 'Copied ✓' : 'Copy link'}
                  </button>
                  <button
                    type="button"
                    className="zen-btn-danger zen-btn-sm"
                    disabled={busy}
                    onClick={() => handleDelete(p)}
                  >
                    {busy ? 'Menghapus…' : '🗑 Hapus'}
                  </button>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
