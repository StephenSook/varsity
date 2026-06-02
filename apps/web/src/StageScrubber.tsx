import { useState } from 'react'

type Stage = { stage: string; [key: string]: unknown }

// Rewind-and-re-narrate: a keyboard-accessible slider over the pipeline steps that
// re-announces the selected step to a polite live region. The native range input is
// fully operable by arrow keys / Home / End, so this is reachable without a mouse.
export function StageScrubber({
  stages,
  describe,
}: {
  stages: Stage[]
  describe: (s: Stage) => string
}) {
  const [idx, setIdx] = useState(0)
  if (stages.length < 2) return null
  const clamped = Math.min(idx, stages.length - 1)
  const s = stages[clamped]
  const label = `${s.stage}${describe(s)}`

  return (
    <div className="w-full max-w-md text-left">
      <label htmlFor="stage-scrubber" className="text-xs font-medium text-slate-400">
        Replay any step ({clamped + 1} of {stages.length})
      </label>
      <input
        id="stage-scrubber"
        type="range"
        min={0}
        max={stages.length - 1}
        step={1}
        value={clamped}
        onChange={(e) => setIdx(Number(e.target.value))}
        aria-valuetext={label}
        className="mt-1 w-full accent-emerald-400"
      />
      <p role="status" aria-live="polite" className="mt-1 text-sm text-emerald-200">
        {label}
      </p>
    </div>
  )
}
