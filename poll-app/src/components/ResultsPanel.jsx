import DesignCard from './DesignCard'

/**
 * Shared results UI: KPI strip + leaderboard + design grid + voter list.
 * Used by VotePoll (post-submit) and PollStats (creator dashboard).
 */
export default function ResultsPanel({
  poll,
  stats,
  onRefresh,
  share,
  title = 'Makasih udah vote!',
  subtitle,
  showVoters = true,
  actions,
}) {
  const top = (stats.rows || []).slice(0, 8)
  const votes = poll?.votes || []
  const designMap = Object.fromEntries((poll?.designs || []).map((d) => [d.id, d]))
  const totalDesigns = poll?.designs?.length || 0
  const totalVoters = stats.totalVoters || 0
  const totalPicks = votes.reduce((n, v) => n + (v.designIds?.length || 0), 0)
  const avgPicks = totalVoters ? (totalPicks / totalVoters).toFixed(1) : '0'
  const leader = top[0]

  return (
    <div className="relative space-y-5">
      <div className="zen-card zen-card-pad space-y-4 text-center">
        <div className="text-4xl">🏆</div>
        <h2 className="poll-title text-xl sm:text-2xl">{title}</h2>
        <p className="poll-subtitle">
          {subtitle || `Hasil real-time · ${totalVoters} orang udah isi`}
        </p>

        {/* KPI */}
        <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-4">
          <Kpi label="Voter" value={totalVoters} />
          <Kpi label="Desain" value={totalDesigns} />
          <Kpi label="Total pick" value={totalPicks} />
          <Kpi label="Avg pick/org" value={avgPicks} />
        </div>

        {leader && totalVoters > 0 && (
          <div className="rounded-xl bg-gradient-to-r from-cyan-50 to-pink-50 px-4 py-3 text-sm">
            <span className="font-bold text-slate-600">#1 sekarang: </span>
            <span className="font-extrabold text-[#111827]">{leader.name}</span>
            <span className="ml-2 font-bold text-cyan-800">
              {leader.count} vote · {leader.pct}%
            </span>
          </div>
        )}

        <div className="flex flex-col gap-2 sm:flex-row sm:justify-center">
          {onRefresh && (
            <button type="button" className="zen-btn-secondary" onClick={onRefresh}>
              Refresh hasil
            </button>
          )}
          {share && (
            <button
              type="button"
              className="zen-btn-primary"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(share)
                } catch {
                  window.prompt('Copy:', share)
                }
              }}
            >
              Share link vote
            </button>
          )}
          {actions}
        </div>
      </div>

      {/* Leaderboard */}
      <section className="zen-card zen-card-pad space-y-3">
        <h3 className="font-heading text-lg font-extrabold text-[#111827]">Leaderboard</h3>
        <ol className="space-y-2">
          {top.map((row, i) => (
            <li
              key={row.id}
              className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-2.5"
            >
              <span
                className={[
                  'flex h-8 w-8 items-center justify-center rounded-full text-sm font-black',
                  i === 0
                    ? 'bg-gradient-to-br from-yellow-300 to-amber-400 text-[#111827]'
                    : i === 1
                      ? 'bg-slate-200 text-slate-700'
                      : i === 2
                        ? 'bg-orange-200 text-orange-800'
                        : 'bg-slate-100 text-slate-600 border border-slate-200',
                ].join(' ')}
              >
                {i + 1}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-extrabold text-[#111827]">{row.name}</p>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-pink-500"
                    style={{ width: `${row.pct}%` }}
                  />
                </div>
              </div>
              <div className="text-right text-xs font-bold">
                <div className="text-[#111827]">{row.count} vote</div>
                <div className="text-cyan-700">{row.pct}%</div>
              </div>
            </li>
          ))}
          {!top.length && (
            <p className="text-sm font-medium text-slate-600">Belum ada vote — jadi yang pertama!</p>
          )}
        </ol>
      </section>

      {/* All designs with bars */}
      <section className="space-y-3">
        <h3 className="font-heading text-lg font-extrabold text-[#111827]">Semua desain</h3>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {(stats.rows || []).map((d, i) => (
            <DesignCard key={d.id} design={d} showStats rank={i + 1} zoomable />
          ))}
        </div>
      </section>

      {/* Who voted */}
      {showVoters && (
        <section className="zen-card zen-card-pad space-y-3">
          <div className="flex items-center justify-between gap-2">
            <h3 className="font-heading text-lg font-extrabold text-[#111827]">Siapa yang vote</h3>
            <span className="rounded-full bg-cyan-50 px-2.5 py-1 text-xs font-bold text-cyan-800">
              {votes.length} orang
            </span>
          </div>
          {votes.length === 0 ? (
            <p className="text-sm font-medium text-slate-600">Belum ada responden.</p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {[...votes]
                .sort((a, b) => (b.at || 0) - (a.at || 0))
                .map((v, idx) => {
                  const picks = (v.designIds || [])
                    .map((id) => designMap[id]?.name || id)
                    .filter(Boolean)
                  return (
                    <li key={`${v.voterName}-${v.at || idx}`} className="flex flex-col gap-1 py-3 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <p className="font-extrabold text-[#111827]">{v.voterName}</p>
                        <p className="text-xs font-medium text-slate-600">{formatWhen(v.at)}</p>
                      </div>
                      <p className="max-w-md text-xs font-semibold text-slate-700 sm:text-right">
                        {picks.length ? picks.join(' · ') : '—'}
                      </p>
                    </li>
                  )
                })}
            </ul>
          )}
        </section>
      )}

      <p className="text-center text-xs font-medium text-slate-600">
        Poll: <span className="font-mono text-slate-700">{poll?.id}</span>
      </p>
    </div>
  )
}

function Kpi({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 px-3 py-3">
      <p className="text-[10px] font-extrabold uppercase tracking-wide text-slate-600">{label}</p>
      <p className="font-heading text-xl font-extrabold text-[#111827]">{value}</p>
    </div>
  )
}

function formatWhen(ts) {
  if (!ts) return '—'
  try {
    const d = typeof ts === 'number' ? new Date(ts) : new Date(ts)
    if (Number.isNaN(d.getTime())) return '—'
    return d.toLocaleString('id-ID', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'Asia/Jakarta',
    })
  } catch {
    return '—'
  }
}
