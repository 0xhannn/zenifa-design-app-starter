import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ResultsPanel from './ResultsPanel'
import { fetchPoll, shareUrl, tallyVotes } from '../lib/store'

/**
 * PollStats — creator/public results dashboard without voting.
 * Route: /poll/:pollId/stats
 */
export default function PollStats() {
  const { pollId } = useParams()
  const [poll, setPoll] = useState(null)
  const [source, setSource] = useState('none')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [live, setLive] = useState(true)

  const load = useCallback(async (silent = false) => {
    if (!pollId) return
    if (!silent) {
      setLoading(true)
      setError('')
    }
    try {
      const { poll: p, source: s } = await fetchPoll(pollId)
      if (!p) {
        setPoll(null)
        setError('Poll tidak ditemukan.')
      } else {
        setPoll(p)
        setSource(s)
      }
    } catch (e) {
      if (!silent) setError(e.message || 'Gagal load stats')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [pollId])

  useEffect(() => {
    load()
  }, [load])

  // live poll every 8s
  useEffect(() => {
    if (!pollId || !live) return
    const t = setInterval(() => load(true), 8000)
    return () => clearInterval(t)
  }, [pollId, live, load])

  const stats = useMemo(
    () => (poll ? tallyVotes(poll) : { rows: [], totalVoters: 0 }),
    [poll],
  )

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-12">
        <div className="h-8 w-2/3 shimmer rounded-xl" />
        <div className="h-24 shimmer rounded-2xl" />
        <div className="grid gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-20 shimmer rounded-2xl" />
          ))}
        </div>
      </div>
    )
  }

  if (!poll) {
    return (
      <div className="poll-page mx-auto max-w-md space-y-4 text-center">
        <div className="text-5xl">📊</div>
        <h1 className="poll-title text-2xl">Stats gak ketemu</h1>
        <p className="poll-subtitle">{error || 'Cek id poll.'}</p>
        <Link to="/poll" className="zen-btn-primary inline-flex">
          ← Riwayat Poll
        </Link>
      </div>
    )
  }

  return (
    <div className="poll-page-wide poll-stack pb-16">
      <div className="zen-blob -left-6 top-0 h-40 w-40 bg-cyan-300" />
      <div className="zen-blob right-0 top-16 h-32 w-32 bg-pink-300" />

      <header className="relative z-[1] space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-gradient-to-r from-cyan-500 to-pink-500 px-3 py-1 text-[11px] font-extrabold uppercase tracking-wide text-[#111827]">
            Statistik / Kinerja
          </span>
          {source === 'local' && (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[10px] font-bold text-amber-800">
              localStorage
            </span>
          )}
          <button
            type="button"
            onClick={() => setLive((v) => !v)}
            className={[
              'rounded-full px-2.5 py-1 text-[10px] font-bold',
              live ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600',
            ].join(' ')}
          >
            {live ? '● Live 8s' : '○ Live off'}
          </button>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="min-w-0">
            <h1 className="poll-title sm:text-4xl">{poll.title}</h1>
            {poll.description && (
              <p className="poll-subtitle max-w-2xl">{poll.description}</p>
            )}
            <p className="poll-meta mt-1.5">
              oleh <strong>{poll.creatorName}</strong>
              <span className="mx-1.5 text-slate-300">·</span>
              <span className="font-mono text-slate-700">/poll/{poll.id}</span>
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link to={`/poll/${poll.id}`} className="zen-btn-primary zen-btn-sm">
              Halaman Vote
            </Link>
            <Link to="/poll" className="zen-btn-secondary zen-btn-sm">
              ← Riwayat
            </Link>
          </div>
        </div>
      </header>

      <div className="relative z-[1]">
        <ResultsPanel
          poll={poll}
          stats={stats}
          onRefresh={() => load()}
          share={shareUrl(poll.id)}
          title="Kinerja Poll"
          subtitle={`Dashboard hasil · ${stats.totalVoters} voter · update ${live ? 'otomatis' : 'manual'}`}
          showVoters
        />
      </div>
    </div>
  )
}
