import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DesignCard from './DesignCard'
import { gdriveThumbnail, parseLinkLines } from '../lib/gdrive'
import {
  checkAdminAuth,
  createPollRemote,
  pinLoginUrl,
  shareUrl,
  shortId,
} from '../lib/store'

/**
 * CreatePoll — admin only (Workflow Planner PIN session).
 * Non-admin: gate + link ke /pin?next=/poll/new
 */
export default function CreatePoll() {
  const navigate = useNavigate()
  const [auth, setAuth] = useState(null) // null loading | true | false
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [paste, setPaste] = useState('')
  const [designs, setDesigns] = useState([])
  const [creatorName, setCreatorName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [created, setCreated] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    let live = true
    checkAdminAuth().then((ok) => {
      if (live) setAuth(ok)
    })
    return () => {
      live = false
    }
  }, [])

  const canSubmit = useMemo(
    () => auth && title.trim() && designs.length > 0 && creatorName.trim() && !busy,
    [auth, title, designs, creatorName, busy],
  )

  function addLinks() {
    setError('')
    const lines = parseLinkLines(paste)
    if (!lines.length) {
      setError('Paste minimal 1 link Google Drive (satu per baris).')
      return
    }
    const existing = new Set(designs.map((d) => d.url))
    const next = [...designs]
    lines.forEach((url) => {
      if (existing.has(url)) return
      const id = shortId(6)
      next.push({
        id,
        url,
        name: `Desain ${next.length + 1}`,
        thumbnail: gdriveThumbnail(url, 800),
      })
      existing.add(url)
    })
    setDesigns(next)
    setPaste('')
  }

  function removeDesign(id) {
    setDesigns((d) => d.filter((x) => x.id !== id))
  }

  function renameDesign(id, name) {
    setDesigns((list) => list.map((d) => (d.id === id ? { ...d, name } : d)))
  }

  async function handleCreate(e) {
    e.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    setError('')
    try {
      const poll = {
        id: shortId(8),
        title: title.trim(),
        description: description.trim(),
        designs,
        creatorName: creatorName.trim(),
        createdAt: Date.now(),
        votes: [],
      }
      const { poll: saved, source } = await createPollRemote(poll)
      setCreated({ ...saved, source })
    } catch (err) {
      if (err.code === 401) {
        setAuth(false)
        setError('Session admin habis. Login PIN dulu.')
      } else {
        setError(err.message || 'Gagal buat poll')
      }
    } finally {
      setBusy(false)
    }
  }

  async function copyLink() {
    if (!created) return
    const url = shareUrl(created.id)
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      window.prompt('Copy link ini:', url)
    }
  }

  if (auth === null) {
    return (
      <div className="mx-auto max-w-md space-y-3 px-4 py-16">
        <div className="h-8 shimmer rounded-xl" />
        <div className="h-4 w-2/3 shimmer rounded-lg" />
        <div className="h-40 shimmer rounded-2xl" />
      </div>
    )
  }

  if (!auth) {
    return (
      <div className="poll-page mx-auto max-w-md text-center">
        <div className="zen-blob left-0 top-0 h-36 w-36 bg-cyan-300" />
        <div className="zen-blob right-0 top-10 h-32 w-32 bg-pink-300" />
        <div className="zen-card zen-card-pad relative space-y-4">
          <div className="text-4xl">🔐</div>
          <h1 className="poll-title text-xl sm:text-2xl">Admin only</h1>
          <p className="poll-subtitle">
            Buat Team Poll cuma buat admin. Login PIN dulu, abis itu balik ke sini.
          </p>
          <a href={pinLoginUrl('/poll/new')} className="zen-btn-primary inline-flex w-full justify-center">
            Login PIN →
          </a>
          <button
            type="button"
            className="text-sm font-bold text-slate-600 hover:text-[#111827]"
            onClick={() => navigate('/poll')}
          >
            ← Kembali ke riwayat
          </button>
        </div>
      </div>
    )
  }

  if (created) {
    const url = shareUrl(created.id)
    return (
      <div className="poll-page mx-auto max-w-xl">
        <div className="zen-blob left-0 top-0 h-40 w-40 bg-cyan-300" />
        <div className="zen-blob right-0 top-10 h-36 w-36 bg-pink-300" />
        <div className="zen-card zen-card-pad relative space-y-4 text-center">
          <div className="text-4xl">🎉</div>
          <h1 className="poll-title text-xl sm:text-2xl">Poll siap dishare!</h1>
          <p className="poll-subtitle">
            <strong className="text-[#111827]">{created.title}</strong>
            {' · '}
            {created.designs.length} desain
          </p>
          <div className="rounded-xl border border-dashed border-cyan-300 bg-cyan-50/70 px-3 py-3 text-left">
            <p className="mb-1 text-[11px] font-bold uppercase tracking-wide text-cyan-800">
              Shareable link
            </p>
            <code className="break-all text-sm font-semibold text-[#111827]">{url}</code>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button type="button" className="zen-btn-primary flex-1" onClick={copyLink}>
              {copied ? 'Copied ✓' : 'Copy Link'}
            </button>
            <button
              type="button"
              className="zen-btn-secondary flex-1"
              onClick={() => navigate(`/poll/${created.id}`)}
            >
              Buka Halaman Vote
            </button>
          </div>
          <button
            type="button"
            className="text-sm font-bold text-slate-600 hover:text-[#111827]"
            onClick={() => navigate(`/poll/${created.id}/stats`)}
          >
            📊 Lihat stats
          </button>
          <button
            type="button"
            className="text-sm font-bold text-slate-600 hover:text-[#111827]"
            onClick={() => navigate('/poll')}
          >
            Lihat Riwayat Poll
          </button>
          <button
            type="button"
            className="text-sm font-bold text-slate-600 hover:text-[#111827]"
            onClick={() => {
              setCreated(null)
              setTitle('')
              setDescription('')
              setDesigns([])
              setCreatorName('')
            }}
          >
            Buat poll baru
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="poll-page poll-stack">
      <div className="zen-blob -left-6 top-0 h-40 w-40 bg-cyan-300" />
      <div className="zen-blob right-0 top-20 h-32 w-32 bg-pink-300" />

      <header className="relative z-[1] space-y-2">
        <p className="poll-kicker">Workflow Planner · Design Feedback · Admin</p>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="poll-title sm:text-4xl">Team Poll</h1>
            <p className="poll-subtitle max-w-xl">
              Paste link Google Drive desain, generate shareable poll, biar tim vote favorite kicks-mu.
            </p>
          </div>
          <button
            type="button"
            className="zen-btn-secondary zen-btn-sm shrink-0"
            onClick={() => navigate('/poll')}
          >
            ← Riwayat Poll
          </button>
        </div>
      </header>

      <form onSubmit={handleCreate} className="relative z-[1] space-y-5">
        <section className="zen-card zen-card-pad space-y-4">
          <div>
            <label className="mb-1.5 block text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
              Judul Poll *
            </label>
            <input
              className="zen-input"
              placeholder='Contoh: "Review Kicks Batch Juli"'
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
              Deskripsi singkat
            </label>
            <textarea
              className="zen-input min-h-[80px] resize-y"
              placeholder="Opsional — konteks buat responden"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
              Nama Pembuat *
            </label>
            <input
              className="zen-input"
              placeholder="Nama kamu"
              value={creatorName}
              onChange={(e) => setCreatorName(e.target.value)}
              required
            />
          </div>
        </section>

        <section className="zen-card zen-card-pad space-y-4">
          <div className="flex items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <h2 className="font-heading text-lg font-extrabold text-[#111827]">Tambah Desain</h2>
            <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-bold text-cyan-800">
              {designs.length} item
            </span>
          </div>
          <p className="poll-meta">
            Paste multiple Google Drive links — <strong>satu link per baris</strong>. Thumbnail
            diambil dari GDrive otomatis.
          </p>
          <textarea
            className="zen-input min-h-[120px] font-mono text-xs"
            placeholder={
              'https://drive.google.com/file/d/...\nhttps://drive.google.com/file/d/...\nhttps://drive.google.com/open?id=...'
            }
            value={paste}
            onChange={(e) => setPaste(e.target.value)}
          />
          <button type="button" className="zen-btn-secondary" onClick={addLinks}>
            + Add Links
          </button>

          {designs.length > 0 && (
            <div className="grid gap-4 sm:grid-cols-2">
              {designs.map((d) => (
                <div key={d.id} className="space-y-2">
                  <DesignCard design={d} onRemove={removeDesign} zoomable />
                  <input
                    className="zen-input text-xs"
                    value={d.name}
                    onChange={(e) => renameDesign(d.id, e.target.value)}
                    placeholder="Nama desain"
                  />
                </div>
              ))}
            </div>
          )}
        </section>

        {error && (
          <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-700">
            {error}
            {error.includes('PIN') && (
              <div className="mt-2">
                <a href={pinLoginUrl('/poll/new')} className="font-extrabold underline">
                  Login PIN →
                </a>
              </div>
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="zen-btn-primary w-full py-3 text-base disabled:opacity-50"
        >
          {busy ? 'Membuat…' : 'Create Poll & Generate Link ✨'}
        </button>
      </form>
    </div>
  )
}
