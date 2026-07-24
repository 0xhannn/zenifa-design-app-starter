import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DesignCard from './DesignCard'
import ResultsPanel from './ResultsPanel'
import { fetchPoll, shareUrl, submitVoteRemote, tallyVotes } from '../lib/store'

/**
 * VotePoll — public survey page for shared /poll/:id
 * Multi-select designs + voter name + live results + mini leaderboard
 */
export default function VotePoll() {
  const { pollId } = useParams()
  const [poll, setPoll] = useState(null)
  const [source, setSource] = useState('none')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(() => new Set())
  const [voterName, setVoterName] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    if (!pollId) return
    setLoading(true)
    setError('')
    try {
      const { poll: p, source: s } = await fetchPoll(pollId)
      if (!p) {
        setPoll(null)
        setError('Poll tidak ditemukan. Cek link atau buat baru.')
      } else {
        setPoll(p)
        setSource(s)
      }
    } catch (e) {
      setError(e.message || 'Gagal load poll')
    } finally {
      setLoading(false)
    }
  }, [pollId])

  useEffect(() => {
    load()
  }, [load])

  // soft realtime: poll API every 8s when viewing results
  useEffect(() => {
    if (!pollId || !done) return
    const t = setInterval(async () => {
      const { poll: p } = await fetchPoll(pollId)
      if (p) setPoll(p)
    }, 8000)
    return () => clearInterval(t)
  }, [pollId, done])

  const stats = useMemo(() => (poll ? tallyVotes(poll) : { rows: [], totalVoters: 0 }), [poll])

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setToast('')
    if (!voterName.trim()) {
      setToast('Isi nama kamu dulu ya')
      return
    }
    if (!selected.size) {
      setToast('Pilih minimal 1 desain')
      return
    }
    setSubmitting(true)
    try {
      const { poll: updated } = await submitVoteRemote(pollId, {
        voterName: voterName.trim(),
        designIds: Array.from(selected),
      })
      setPoll(updated)
      setDone(true)
    } catch (err) {
      setToast(err.message || 'Gagal submit')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-12">
        <div className="h-8 w-2/3 shimmer rounded-xl" />
        <div className="h-4 w-1/2 shimmer rounded-lg" />
        <div className="grid gap-4 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="aspect-[4/3] shimmer rounded-2xl" />
          ))}
        </div>
      </div>
    )
  }

  if (!poll) {
    return (
      <div className="poll-page mx-auto max-w-md space-y-4 text-center">
        <div className="text-5xl">🧐</div>
        <h1 className="poll-title text-2xl">Poll gak ketemu</h1>
        <p className="poll-subtitle">{error || 'Link mungkin salah / expired.'}</p>
        <p className="poll-meta">
          Minta link share dari admin, atau login admin buat bikin poll baru.
        </p>
      </div>
    )
  }

  return (
    <div className="poll-page-wide poll-stack pb-28 sm:pb-10">
      <div className="zen-blob -left-6 top-0 h-40 w-40 bg-cyan-300" />
      <div className="zen-blob right-0 top-16 h-32 w-32 bg-pink-300" />

      <header className="relative z-[1] space-y-2.5">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-gradient-to-r from-cyan-500 to-pink-500 px-3 py-1 text-[11px] font-extrabold uppercase tracking-wide text-[#111827]">
            Design Feedback
          </span>
          {source === 'local' && (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-bold text-amber-800">
              localStorage
            </span>
          )}
          <Link
            to={`/poll/${poll.id}/stats`}
            className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-bold text-slate-700 hover:bg-cyan-50 hover:text-cyan-800"
          >
            📊 Lihat stats
          </Link>
        </div>
        <h1 className="poll-title sm:text-4xl">{poll.title}</h1>
        {poll.description && (
          <p className="poll-subtitle max-w-2xl">{poll.description}</p>
        )}
        <p className="poll-meta">
          oleh <strong>{poll.creatorName}</strong>
          <span className="mx-1.5 text-slate-300">·</span>
          {poll.designs?.length || 0} desain
          <span className="mx-1.5 text-slate-300">·</span>
          {stats.totalVoters} voter
        </p>
      </header>

      {!done ? (
        <form onSubmit={handleSubmit} className="relative z-[1] space-y-5">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(poll.designs || []).map((d) => (
              <DesignCard
                key={d.id}
                design={d}
                selectable
                selected={selected.has(d.id)}
                onToggle={toggle}
                zoomable
              />
            ))}
          </div>

          <section className="zen-card zen-card-pad sticky bottom-20 z-20 space-y-3 border-cyan-100 sm:static sm:bottom-auto">
            <label className="block text-[11px] font-extrabold uppercase tracking-wide text-slate-600">
              Nama Kamu *
            </label>
            <input
              className="zen-input"
              placeholder="Nama pengisi (wajib)"
              value={voterName}
              onChange={(e) => setVoterName(e.target.value)}
              required
            />
            <p className="poll-meta">
              Dipilih: <strong className="text-[#111827]">{selected.size}</strong> desain
            </p>
            {toast && (
              <div className="rounded-lg bg-rose-50 px-3 py-2 text-sm font-semibold text-rose-700">
                {toast}
              </div>
            )}
            <button
              type="submit"
              disabled={submitting}
              className="zen-btn-primary w-full py-3 text-base disabled:opacity-60"
            >
              {submitting ? 'Mengirim…' : 'Submit Vote 🚀'}
            </button>
            <p className="text-center text-[11px] font-medium text-slate-600">
              Creator?{' '}
              <Link to={`/poll/${poll.id}/stats`} className="font-bold text-cyan-700 hover:underline">
                Lihat kinerja/statistik tanpa vote →
              </Link>
            </p>
          </section>
        </form>
      ) : (
        <div className="relative z-[1]">
          <ResultsPanel
            poll={poll}
            stats={stats}
            onRefresh={load}
            share={shareUrl(poll.id)}
            actions={
              <Link to={`/poll/${poll.id}/stats`} className="zen-btn-secondary">
                Dashboard stats
              </Link>
            }
          />
        </div>
      )}
    </div>
  )
}
