import { useRef, useState } from 'react'

// Backend SSE base. Override with VITE_BACKEND_URL for a deployed backend.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'

const STAGES = ['trigger', 'geometry', 'law', 'granite', 'guardian', 'verdict'] as const

type Stage = { stage: string; [key: string]: unknown }

function describe(s: Stage): string {
  switch (s.stage) {
    case 'trigger':
      return ` — ${String(s.source)}`
    case 'geometry':
      return ` — margin ${String(s.margin_meters)}m, ${s.is_offside ? 'offside' : 'onside'}`
    case 'law':
      return ` — Law ${String(s.law)} (${String(s.title)})`
    case 'granite':
      return ` — ${String(s.model)}`
    case 'guardian':
      return ` — ${s.safe ? 'SAFE' : 'flagged'}, cites Law: ${String(s.cites_law)}`
    default:
      return ''
  }
}

export default function App() {
  const [explanation, setExplanation] = useState('')
  const [stages, setStages] = useState<Stage[]>([])
  const [streaming, setStreaming] = useState(false)
  const liveRef = useRef<HTMLDivElement>(null)
  const sourceRef = useRef<EventSource | null>(null)

  // The button is the deliberate user gesture that opens the stream (and would
  // unlock audio for the spatial-audio layer later).
  function explainTheCall() {
    sourceRef.current?.close()
    setStages([])
    setExplanation('')
    setStreaming(true)
    const source = new EventSource(`${BACKEND}/stream/canned`)
    sourceRef.current = source
    for (const name of STAGES) {
      source.addEventListener(name, (event) => {
        const data = JSON.parse((event as MessageEvent).data) as Stage
        setStages((prev) => [...prev, data])
        if (name === 'verdict') {
          setExplanation(String(data.text ?? ''))
          setStreaming(false)
          source.close()
        }
      })
    }
    source.onerror = () => {
      setStreaming(false)
      source.close()
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 px-6 py-16 text-center">
      <h1 className="text-4xl sm:text-6xl font-semibold tracking-tight">VARSITY</h1>
      <p className="max-w-xl text-balance text-slate-300">
        Real-time, screen-reader-native explanations of VAR and offside decisions.
      </p>
      <button
        onClick={explainTheCall}
        disabled={streaming}
        className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-60"
      >
        {streaming ? 'Explaining…' : 'Explain the call'}
      </button>

      {/* Pre-registered aria-live region: the screen reader speaks the verdict, mutated in place. */}
      <div ref={liveRef} aria-live="assertive" aria-atomic="true" role="status" className="sr-only">
        {explanation}
      </div>

      {/* Pipeline trace, decorative and hidden from the screen reader. */}
      {stages.length > 0 && (
        <ol aria-hidden="true" className="w-full max-w-md space-y-1 text-left text-sm text-slate-400">
          {stages.map((s, i) => (
            <li key={i} className="rounded bg-slate-800/40 px-3 py-1.5">
              <span className="font-medium text-emerald-300">{s.stage}</span>
              {describe(s)}
            </li>
          ))}
        </ol>
      )}

      {explanation && (
        <p aria-hidden="true" className="max-w-2xl text-lg text-emerald-200">
          {explanation}
        </p>
      )}
    </main>
  )
}
