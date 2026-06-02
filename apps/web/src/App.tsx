import { useRef, useState } from 'react'
import { OffsidePitch, type Geometry } from './OffsidePitch'

// Backend SSE base. Override with VITE_BACKEND_URL for a deployed backend.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'

const STAGES = ['trigger', 'geometry', 'law', 'granite', 'guardian', 'verdict'] as const

type Stage = { stage: string; [key: string]: unknown }
type Lang = 'English' | 'Spanish'

// Granite is multilingual (EN/DE/ES/FR/PT); VARSITY ships the World Cup pair EN/ES.
const UI: Record<Lang, {
  code: string
  bcp47: string
  langLabel: string
  sub: string
  explain: string
  explaining: string
  caption: (m: string, off: boolean) => string
}> = {
  English: {
    code: 'EN',
    bcp47: 'en',
    langLabel: 'Explanation language',
    sub: 'Real-time, screen-reader-native explanations of VAR and offside decisions.',
    explain: 'Explain the call',
    explaining: 'Explaining…',
    caption: (m, off) =>
      `Offside line at the second-to-last defender · attacker ${m} m ${off ? 'ahead' : 'behind'}`,
  },
  Spanish: {
    code: 'ES',
    bcp47: 'es',
    langLabel: 'Idioma de la explicación',
    sub: 'Explicaciones en tiempo real, nativas para lectores de pantalla, de decisiones de VAR y fuera de juego.',
    explain: 'Explicar la jugada',
    explaining: 'Explicando…',
    caption: (m, off) =>
      `Línea de fuera de juego en el penúltimo defensor · atacante ${m} m ${off ? 'por delante' : 'por detrás'}`,
  },
}

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
  const [geo, setGeo] = useState<Geometry | null>(null)
  const [streaming, setStreaming] = useState(false)
  const [lang, setLang] = useState<Lang>('English')
  const liveRef = useRef<HTMLDivElement>(null)
  const sourceRef = useRef<EventSource | null>(null)

  // The button is the deliberate user gesture that opens the stream (and would
  // unlock audio for the spatial-audio layer later). Language is passed explicitly
  // so re-narrating on a language toggle does not race the lang state update.
  function explainTheCall(language: Lang) {
    sourceRef.current?.close()
    setStages([])
    setExplanation('')
    setGeo(null)
    setStreaming(true)
    const url = `${BACKEND}/stream/canned?language=${encodeURIComponent(language)}`
    const source = new EventSource(url)
    sourceRef.current = source
    for (const name of STAGES) {
      source.addEventListener(name, (event) => {
        const data = JSON.parse((event as MessageEvent).data) as Stage
        setStages((prev) => [...prev, data])
        if (name === 'geometry') {
          setGeo(data as unknown as Geometry)
        }
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

  function selectLang(l: Lang) {
    setLang(l)
    // Re-narrate the same call in the new language if one is already showing.
    if (explanation || streaming || geo) {
      explainTheCall(l)
    }
  }

  const t = UI[lang]

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 px-6 py-16 text-center">
      <h1 className="text-4xl sm:text-6xl font-semibold tracking-tight">VARSITY</h1>
      <p className="max-w-xl text-balance text-slate-300" lang={t.bcp47}>
        {t.sub}
      </p>

      {/* Language toggle: real buttons with aria-pressed; switching re-narrates the call. */}
      <div role="group" aria-label={t.langLabel} className="inline-flex rounded-full bg-slate-800/60 p-1">
        {(['English', 'Spanish'] as const).map((l) => (
          <button
            key={l}
            type="button"
            aria-pressed={lang === l}
            onClick={() => selectLang(l)}
            className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
              lang === l ? 'bg-emerald-500 text-slate-950' : 'text-slate-300 hover:text-white'
            }`}
          >
            {UI[l].code}
          </button>
        ))}
      </div>

      <button
        onClick={() => explainTheCall(lang)}
        disabled={streaming}
        className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-60"
      >
        {streaming ? t.explaining : t.explain}
      </button>

      {/* Pre-registered aria-live region: the screen reader speaks the verdict, mutated in
          place. lang switches the voice (en/es) for the spoken explanation. */}
      <div
        ref={liveRef}
        aria-live="assertive"
        aria-atomic="true"
        role="status"
        lang={t.bcp47}
        className="sr-only"
      >
        {explanation}
      </div>

      {/* Dual-use offside visualization: decorative, hidden from the screen reader. */}
      {geo && (
        <figure aria-hidden="true" className="w-full max-w-2xl">
          <OffsidePitch geo={geo} />
          <figcaption className="mt-2 text-sm text-slate-400" lang={t.bcp47}>
            {t.caption(geo.margin_meters.toFixed(2), geo.is_offside)}
          </figcaption>
        </figure>
      )}

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
        <p aria-hidden="true" lang={t.bcp47} className="max-w-2xl text-lg text-emerald-200">
          {explanation}
        </p>
      )}
    </main>
  )
}
