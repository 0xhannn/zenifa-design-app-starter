import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { gdriveThumbnail, gdriveViewUrl } from '../lib/gdrive'

/**
 * DesignCard — preview + optional select/stats.
 * zoomable=true → tap image opens full-screen lightbox (voters can enlarge).
 * Lightbox is portaled to document.body so shell #root overflow/transform
 * cannot clip fixed fullscreen overlays.
 */
export default function DesignCard({
  design,
  selectable = false,
  selected = false,
  onToggle,
  onRemove,
  showStats = false,
  rank,
  zoomable = false,
}) {
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [open, setOpen] = useState(false)
  const thumb = design.thumbnail || gdriveThumbnail(design.url, 800)
  // Prefer larger Drive thumb for lightbox (card thumb is often w800)
  const full = gdriveThumbnail(design.url, 2000) || design.thumbnail || thumb

  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [open])

  const lightbox =
    open &&
    typeof document !== 'undefined' &&
    createPortal(
      <div
        className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/90 p-3 backdrop-blur-sm sm:p-6"
        role="dialog"
        aria-modal="true"
        aria-label={`Preview ${design.name}`}
        onClick={() => setOpen(false)}
        style={{ position: 'fixed', inset: 0, zIndex: 9999 }}
      >
        <button
          type="button"
          className="absolute right-4 top-4 z-10 rounded-full bg-white/15 px-3 py-1.5 text-sm font-extrabold text-white hover:bg-white/25"
          onClick={() => setOpen(false)}
        >
          Tutup ✕
        </button>
        <div
          className="relative flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-2xl bg-black/50 shadow-2xl"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex min-h-0 flex-1 items-center justify-center p-2 sm:p-4">
            <img
              src={full || thumb}
              alt={design.name}
              className="max-h-[78vh] w-auto max-w-full object-contain"
              referrerPolicy="no-referrer"
              onError={(e) => {
                // fallback to card thumb if large Drive thumb fails
                if (thumb && e.currentTarget.src !== thumb) {
                  e.currentTarget.src = thumb
                }
              }}
            />
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/10 bg-black/80 px-4 py-3 text-white">
            <div className="min-w-0">
              <p className="truncate font-heading text-base font-extrabold text-white">
                {design.name}
              </p>
              <p className="truncate text-xs text-slate-300">{design.url}</p>
            </div>
            <a
              href={gdriveViewUrl(design.url)}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 rounded-xl bg-white/15 px-3 py-2 text-xs font-extrabold text-white hover:bg-white/25"
            >
              Buka di Drive ↗
            </a>
          </div>
        </div>
      </div>,
      document.body,
    )

  return (
    <>
      <div
        className={[
          'zen-card pop-in relative overflow-hidden group',
          selectable ? 'cursor-pointer' : '',
          selected ? 'ring-4 ring-cyan-300 border-cyan-300 shadow-cyan' : '',
        ].join(' ')}
        onClick={() => selectable && onToggle?.(design.id)}
        role={selectable ? 'button' : undefined}
        tabIndex={selectable ? 0 : undefined}
        onKeyDown={(e) => {
          if (!selectable) return
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            onToggle?.(design.id)
          }
        }}
      >
        {rank != null && (
          <div className="absolute left-3 top-3 z-10 rounded-full bg-zen-ink/90 px-2.5 py-1 text-xs font-extrabold text-[#111827] shadow">
            #{rank}
          </div>
        )}

        <div className="relative aspect-[4/3] overflow-hidden bg-slate-100">
          {loading && !failed && <div className="absolute inset-0 shimmer" />}
          {failed || !thumb ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-gradient-to-br from-cyan-50 to-pink-50 text-slate-500">
              <span className="text-3xl">🎨</span>
              <span className="text-xs font-semibold">Preview GDrive</span>
              <a
                href={gdriveViewUrl(design.url)}
                target="_blank"
                rel="noreferrer"
                className="text-xs font-bold text-cyan-700 underline"
                onClick={(e) => e.stopPropagation()}
              >
                Buka link
              </a>
            </div>
          ) : (
            <>
              <img
                src={thumb}
                alt={design.name}
                className={[
                  'h-full w-full object-cover transition duration-500 group-hover:scale-105',
                  loading ? 'opacity-0' : 'opacity-100',
                  zoomable ? 'cursor-zoom-in' : '',
                ].join(' ')}
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false)
                  setFailed(true)
                }}
                referrerPolicy="no-referrer"
                onClick={
                  zoomable
                    ? (e) => {
                        e.stopPropagation()
                        setOpen(true)
                      }
                    : undefined
                }
              />
              {zoomable && !loading && (
                <button
                  type="button"
                  aria-label="Perbesar gambar"
                  className="absolute bottom-3 right-3 z-10 rounded-xl bg-zen-ink/80 px-2.5 py-1.5 text-xs font-extrabold text-[#111827] shadow backdrop-blur hover:bg-zen-ink"
                  onClick={(e) => {
                    e.stopPropagation()
                    setOpen(true)
                  }}
                >
                  🔍 Zoom
                </button>
              )}
            </>
          )}

          {selectable && (
            <div
              className={[
                'absolute right-3 top-3 flex h-10 w-10 items-center justify-center rounded-xl border-2 text-lg font-black shadow transition',
                selected
                  ? 'border-transparent bg-gradient-to-br from-cyan-400 to-pink-500 text-[#111827]'
                  : 'border-white/80 bg-white/90 text-slate-400',
              ].join(' ')}
            >
              {selected ? '✓' : ''}
            </div>
          )}
        </div>

        <div className="space-y-2.5 p-4">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="truncate font-heading text-sm font-extrabold text-[#111827]">
                {design.name}
              </p>
              <p className="truncate text-[11px] font-medium text-slate-600">{design.url}</p>
            </div>
            {onRemove && (
              <button
                type="button"
                className="shrink-0 rounded-lg bg-rose-50 px-2 py-1 text-xs font-bold text-rose-700 hover:bg-rose-100"
                onClick={(e) => {
                  e.stopPropagation()
                  onRemove(design.id)
                }}
              >
                Hapus
              </button>
            )}
          </div>

          {showStats && (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between text-xs font-bold">
                <span className="text-slate-600">{design.count || 0} vote</span>
                <span className="text-cyan-700">{design.pct || 0}%</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-pink-500 transition-all duration-500"
                  style={{ width: `${Math.min(100, design.pct || 0)}%` }}
                />
              </div>
            </div>
          )}

          {selectable && (
            <button
              type="button"
              className={[
                'w-full rounded-xl py-2.5 text-sm font-extrabold transition',
                selected
                  ? 'bg-[#111827] text-white'
                  : 'bg-cyan-50 text-cyan-800 hover:bg-cyan-100',
              ].join(' ')}
              onClick={(e) => {
                e.stopPropagation()
                onToggle?.(design.id)
              }}
            >
              {selected ? 'Dipilih ✓' : 'Pilih'}
            </button>
          )}
        </div>
      </div>

      {lightbox}
    </>
  )
}
