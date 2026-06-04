import { useState } from 'react'
import { usePrefersReducedMotion } from './useReducedMotion'

// Over-the-air broadcast runs roughly 18-22s behind live action, glass-to-glass
// (Phenix / Stats Perform Real-Time Latency study: ~18s in 2023, ~22s in 2024,
// ~19s in 2026). We take 20s as the broadcast offset. The lead VARSITY shows is
// that offset minus its OWN measured trigger->verdict latency, so the number is a
// real measured delta for this run, never a hardcoded constant.
const BROADCAST_DELAY_S = 20

export function BroadcastTicker({ latencyMs }: { latencyMs: number | null }) {
  const reduced = usePrefersReducedMotion()
  const [paused, setPaused] = useState(false)
  if (latencyMs == null) return null

  const latencyS = latencyMs / 1000
  const lead = Math.max(0, BROADCAST_DELAY_S - latencyS)
  const varsityPct = Math.min(100, (latencyS / BROADCAST_DELAY_S) * 100)
  const animate = !reduced && !paused

  return (
    <div className="glass w-full max-w-2xl rounded-2xl p-4 text-left" lang="en">
      <div role="status" aria-live="polite" className="text-sm font-medium text-emerald-200">
        {lead >= 1
          ? `VARSITY explained this call ${lead.toFixed(1)}s before the broadcast picture.`
          : 'VARSITY explained this call in step with the broadcast picture.'}
      </div>
      <p className="mt-1 text-xs text-slate-400">
        Over-the-air broadcast runs about {BROADCAST_DELAY_S}s behind live action (Phenix real-time
        latency study); VARSITY took {latencyS.toFixed(1)}s end to end.
      </p>

      {/* Decorative race bar: VARSITY's marker lands early, the broadcast marker at the end. */}
      <div aria-hidden="true" className="mt-3">
        <div className="relative h-2 rounded-full bg-slate-700/50">
          <div
            className={`absolute inset-y-0 left-0 rounded-full bg-emerald-500/30 ${
              animate ? 'animate-pulse' : ''
            }`}
            style={{ width: `${varsityPct}%` }}
          />
          <span
            className="absolute top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-400 ring-2 ring-emerald-300"
            style={{ left: `${varsityPct}%` }}
          />
          <span className="absolute right-0 top-1/2 h-3 w-3 -translate-y-1/2 translate-x-1/2 rounded-full bg-slate-400" />
        </div>
        <div className="mt-1 flex justify-between text-[10px] uppercase tracking-wider text-slate-400">
          <span className="text-emerald-400">VARSITY</span>
          <span>Broadcast</span>
        </div>
      </div>

      {!reduced && (
        <button
          type="button"
          aria-pressed={paused}
          onClick={() => setPaused((p) => !p)}
          className="mt-2 text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          {paused ? 'Resume animation' : 'Pause animation'}
        </button>
      )}
    </div>
  )
}
