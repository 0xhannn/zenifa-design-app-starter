/**
 * Shared chrome so /poll feels like the main Workflow Planner app (logo, top nav, mobile tabs).
 * External routes use plain <a> (full navigation back into Jinja shell).
 */
const NAV = [
  { href: '/welcome', label: 'Home', icon: 'fa-house' },
  { href: '/inwork', label: 'In Work', icon: 'fa-person-running' },
  { href: '/gallery', label: 'Product', icon: 'fa-box-open' },
  { href: '/tasks', label: 'Tasks', icon: 'fa-list-check' },
  { href: '/poll', label: 'Poll', icon: 'fa-poll', poll: true },
]

function isActive(item, pathname) {
  if (item.poll) return pathname === '/poll' || pathname.startsWith('/poll/')
  return false
}

export default function AppChrome({ children }) {
  const pathname = typeof window !== 'undefined' ? window.location.pathname : '/poll'

  return (
    <div className="min-h-screen flex flex-col">
      {/* Desktop top nav — matches main app zen-topnav */}
      <nav className="hidden sm:block sticky top-0 z-40 border-b border-slate-700/80 bg-[#1f2937] text-white shadow-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <a href="/welcome" className="flex items-center gap-2 no-underline">
            <img src="/static/img/workflow-logo-64.png" alt="Workflow Planner" className="h-10 w-10" />
            <span className="font-heading text-xl font-extrabold tracking-tight text-white">
              Workflow Planner
            </span>
          </a>
          <div className="flex items-center gap-1">
            {NAV.map((item) => {
              const active = isActive(item, pathname)
              return (
                <a
                  key={item.href}
                  href={item.href}
                  className={
                    'inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-semibold transition ' +
                    (active
                      ? 'bg-white/15 text-white'
                      : 'text-slate-300 hover:bg-white/10 hover:text-white')
                  }
                >
                  <i className={`fas ${item.icon} text-xs opacity-90`} />
                  {item.label}
                </a>
              )
            })}
          </div>
        </div>
      </nav>

      {/* Mobile top bar */}
      <div className="sm:hidden sticky top-0 z-40 flex h-14 items-center justify-between border-b border-slate-700/80 bg-[#1f2937] px-4 text-white">
        <a href="/welcome" className="flex items-center gap-2 no-underline">
          <img src="/static/img/workflow-logo-64.png" alt="Workflow Planner" className="h-8 w-8" />
          <span className="font-heading text-base font-extrabold tracking-tight">Workflow Planner</span>
        </a>
        <span className="rounded-full bg-gradient-to-r from-[#00C4FF] to-[#FF3D9A] px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wide text-white">
          Poll
        </span>
      </div>

      <main className="relative flex-1 pb-[calc(4.5rem+env(safe-area-inset-bottom))] sm:pb-8">
        {children}
      </main>

      {/* Mobile bottom tabs — same destinations as main app + Poll active */}
      <nav
        className="sm:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-slate-700 bg-[#1f2937] pb-[max(0.5rem,env(safe-area-inset-bottom))] shadow-[0_-4px_12px_rgba(0,0,0,0.35)]"
        aria-label="Main"
      >
        <div className="grid h-16 grid-cols-5">
          {NAV.map((item) => {
            const active = isActive(item, pathname)
            return (
              <a
                key={item.href}
                href={item.href}
                className={
                  'relative flex flex-col items-center justify-center gap-0.5 transition ' +
                  (active ? 'text-cyan-300' : 'text-slate-400 hover:text-white')
                }
              >
                {active && (
                  <span className="absolute top-1 h-1 w-6 rounded-full bg-gradient-to-r from-[#00C4FF] to-[#FF3D9A]" />
                )}
                <i className={`fas ${item.icon} text-lg`} />
                <span className="text-[9px] font-semibold leading-none">{item.label}</span>
              </a>
            )
          })}
        </div>
      </nav>
    </div>
  )
}
