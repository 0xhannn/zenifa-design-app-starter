/**
 * REFERENCE ONLY — App is Jinja2 in production.
 * Live landing: static/index.html (menu == 'welcome') + main.py `_welcome_context`.
 * This file documents the component tree in React/Tailwind form for design handoff.
 */
import React from 'react';

const statusClass = {
  draft: 'bg-zen-yellow-400 text-zen-ink',
  proses: 'bg-zen-cyan-600 text-zen-ink',
  finish: 'bg-zen-lime-500 text-zen-ink',
};

export function LandingPage({ featuredDesigns = [], recentTasks = [], counts = {} }) {
  return (
    <div className="lp-wrap mx-auto max-w-[1120px] pb-12">
      <Hero counts={counts} />
      <FlowSection />
      <FeaturedDesigns designs={featuredDesigns} />
      <RecentTasks tasks={recentTasks} />
      <CtaBand />
    </div>
  );
}

function Hero({ counts }) {
  return (
    <section className="premium-hero relative grid items-center gap-6 overflow-hidden px-5 py-5 md:grid-cols-[1.05fr_0.95fr]">
      <div className="hero-copy flex flex-col items-start">
        <span className="premium-badge mb-3 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1 text-xs font-extrabold text-zen-cyan-700 shadow-[3px_3px_0_#0F1A2E]">
          <span className="h-2 w-2 rounded-full bg-zen-pink-500" />
          PlayStreet · Sneaker Design OS
        </span>
        <h1 className="font-display text-[clamp(2.4rem,5.5vw,3.75rem)] font-extrabold leading-[1.02] tracking-tight text-black">
          Where Sneaker
          <br />
          Design Lives
        </h1>
        <p className="mt-3 max-w-xl text-base font-medium text-[#222]">
          Sketch → sample → drop. One playful studio for every kick in the pipeline —
          track tasks, ship gallery-ready renders, keep the crew in sync.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <a href="/tasks" className="z-btn z-btn-primary">
            Jump into Tasks →
          </a>
          <a href="/pdf" className="z-btn z-btn-secondary">
            Peek the Gallery
          </a>
        </div>
      </div>

      <div className="hero-mascot-wrap flex min-h-[220px] items-center justify-center md:min-h-[280px]" aria-hidden>
        {/* CSS mascot: .zen-mascot in index.html */}
        <div className="zen-mascot" />
      </div>

      <div className="premium-stats col-span-full flex flex-wrap items-center gap-4 rounded-2xl bg-zen-cyan-700/90 px-5 py-3 text-white md:col-span-1">
        <Stat n={counts.tasks} label="Live Tasks" />
        <Stat n={counts.inwork} label="In the Lab" />
        <Stat n={counts.finished} label="Dropped" />
      </div>
    </section>
  );
}

function Stat({ n, label }) {
  return (
    <div className="min-w-[72px]">
      <div className="font-display text-2xl font-extrabold">{n ?? '—'}</div>
      <div className="text-[11px] font-bold uppercase tracking-wide opacity-90">{label}</div>
    </div>
  );
}

function FlowSection() {
  const steps = [
    { n: '01', icon: 'pen-ruler', title: 'Capture the brief', body: 'Drop refs, GDrive links, and notes into a task. Draft until the silhouette clicks.', tint: 'pink' },
    { n: '02', icon: 'running', title: 'Run the lab', body: 'Move work through Proses. In Work keeps WIP kicks visible for the whole crew.', tint: 'cyan' },
    { n: '03', icon: 'trophy', title: 'Ship to gallery', body: 'Finish lands in the catalog + CDN. Showcase renders without hunting folders.', tint: 'lime' },
  ];
  return (
    <section className="lp-section px-5 py-7">
      <Header kicker="How the studio moves" title="Three lanes. Zero chaos." lead="Same energy as a good design crit — clear stages, loud status, fast handoffs." />
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {steps.map((s) => (
          <article key={s.n} className="relative rounded-[20px] bg-white/95 p-5 shadow-zen-md">
            <span className="absolute right-4 top-4 font-display text-3xl font-extrabold text-zen-cyan-500/25">{s.n}</span>
            <h3 className="font-display text-lg font-bold text-zen-ink">{s.title}</h3>
            <p className="mt-2 text-sm text-zen-ink-muted">{s.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function FeaturedDesigns({ designs }) {
  return (
    <section className="lp-section px-5 py-7">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <Header kicker="Fresh out the oven" title="Featured kicks" lead="Latest models with assets — tap in, remix later." />
        <a href="/pdf" className="lp-link-btn rounded-full bg-white px-4 py-2 text-sm font-extrabold shadow-[3px_3px_0_#0F1A2E]">
          Full gallery →
        </a>
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-4">
        {designs.map((d) => (
          <a key={d.id} href="/pdf" className="group overflow-hidden rounded-[18px] bg-white shadow-zen-md transition hover:-translate-y-1.5 hover:shadow-zen-float">
            <div className="relative aspect-square overflow-hidden bg-zen-ice">
              <img src={d.image_path} alt={d.model_name} className="h-full w-full object-cover transition duration-300 group-hover:scale-105" loading="lazy" />
              <span className={`absolute left-2 top-2 rounded-full px-2 py-0.5 text-[10px] font-extrabold ${statusClass[d.status] || statusClass.draft}`}>
                {(d.status || 'draft').toUpperCase()}
              </span>
            </div>
            <div className="flex items-baseline justify-between gap-2 px-3 py-2.5">
              <h3 className="line-clamp-2 font-display text-sm font-extrabold text-zen-ink">{d.model_name}</h3>
              <span className="text-[11px] font-bold text-zen-ink-faint">#{d.id}</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

function RecentTasks({ tasks }) {
  return (
    <section className="lp-section px-5 py-7">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <Header kicker="On the board" title="Recent tasks" lead="What’s cooking in the pipeline right now." />
        <a href="/tasks" className="lp-link-btn rounded-full bg-white px-4 py-2 text-sm font-extrabold shadow-[3px_3px_0_#0F1A2E]">
          Open board →
        </a>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {tasks.map((t) => (
          <a key={t.id} href={`/tasks#task-${t.id}`} className="flex flex-col gap-2.5 rounded-[18px] bg-white/95 p-4 shadow-zen-sm transition hover:-translate-y-1 hover:shadow-zen-md">
            <div className="flex flex-wrap gap-1.5">
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${statusClass[t.status] || statusClass.draft}`}>
                {(t.status || 'draft').toUpperCase()}
              </span>
              {t.category && (
                <span className="rounded-lg bg-zen-cyan-500/15 px-2 py-0.5 text-[11px] font-bold text-zen-cyan-800">{t.category}</span>
              )}
            </div>
            <h3 className="line-clamp-2 font-display text-base font-extrabold text-zen-ink">{t.title}</h3>
            <div className="mt-auto flex justify-between text-xs font-bold text-zen-ink-faint">
              <span>#{t.id}</span>
              <span>↗</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

function CtaBand() {
  return (
    <section className="px-5 py-6">
      <div className="flex flex-wrap items-center justify-between gap-5 rounded-[28px] bg-gradient-to-br from-zen-ink via-zen-night-elev to-zen-night p-6 shadow-zen-lg">
        <div>
          <span className="text-xs font-extrabold uppercase tracking-wider text-zen-yellow-400">Ready when you are</span>
          <h2 className="mt-1 font-display text-2xl font-extrabold text-white">Build the next silhouette.</h2>
          <p className="mt-1 max-w-md text-sm text-white/85">Jump into the board or browse finished drops — the studio’s already warm.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a href="/tasks" className="z-btn z-btn-primary">Jump into Tasks</a>
          <a href="/inwork" className="z-btn z-btn-secondary">See In Work</a>
        </div>
      </div>
    </section>
  );
}

function Header({ kicker, title, lead }) {
  return (
    <div className="max-w-xl">
      <span className="text-[0.72rem] font-extrabold uppercase tracking-wider text-zen-cyan-700">{kicker}</span>
      <h2 className="font-display text-[clamp(1.5rem,3.5vw,2rem)] font-extrabold tracking-tight text-zen-ink">{title}</h2>
      <p className="mt-1 text-[0.95rem] text-[#222]">{lead}</p>
    </div>
  );
}

export default LandingPage;
