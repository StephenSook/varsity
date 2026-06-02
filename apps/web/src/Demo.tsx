import { useRef, useState } from 'react'
import { OffsidePitch, type Geometry } from './OffsidePitch'
import { playOffsideChord } from './sonify'
import { readAloud } from './tts'

// Backend SSE base. Override with VITE_BACKEND_URL for a deployed backend.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'

const STAGES = ['trigger', 'geometry', 'law', 'granite', 'guardian', 'verdict'] as const

type Stage = { stage: string; [key: string]: unknown }
type Lang = 'English' | 'Spanish'

// Granite is multilingual (EN/DE/ES/FR/PT); VARSITY ships the World Cup pair EN/ES.
const UI: Record<
  Lang,
  {
    code: string
    bcp47: string
    langLabel: string
    explain: string
    explaining: string
    caption: (m: string, off: boolean) => string
  }
> = {
  English: {
    code: 'EN',
    bcp47: 'en',
    langLabel: 'Explanation language',
    explain: 'Explain the call',
    explaining: 'Explaining…',
    caption: (m, off) =>
      `Offside line at the second-to-last defender · attacker ${m} m ${off ? 'ahead' : 'behind'}`,
  },
  Spanish: {
    code: 'ES',
    bcp47: 'es',
    langLabel: 'Idioma de la explicación',
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

// Haptic cue (Vibration API): a third sensory channel for the offside moment, in
// direct response to a blind fan's feedback about tactile match feedback. Offside is
// a longer buzz scaled by how far past the line; onside is a short tap. Mobile/Android
// only; a graceful no-op on desktop. Gesture-gated by the Explain click.
function triggerHaptic(g: { is_offside: boolean; margin_meters: number }) {
  const nav = navigator as Navigator & { vibrate?: (p: number | number[]) => boolean }
  if (typeof nav.vibrate !== 'function') return
  const pattern: number[] = g.is_offside
    ? [Math.round(Math.min(450, 120 + Math.abs(g.margin_meters) * 60))]
    : [90]
  nav.vibrate(pattern)
  ;(window as unknown as { __varsityHaptic?: number[] }).__varsityHaptic = pattern
}

export function Demo() {
  const [explanation, setExplanation] = useState('')
  const [stages, setStages] = useState<Stage[]>([])
  const [geo, setGeo] = useState<Geometry | null>(null)
  const [lawText, setLawText] = useState('')
  const [detail, setDetail] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [lang, setLang] = useState<Lang>('English')
  const [soundOn, setSoundOn] = useState(true)
  const [offlineSource, setOfflineSource] = useState<string | null>(null)
  const [offlineStatus, setOfflineStatus] = useState('')
  const liveRef = useRef<HTMLDivElement>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)

  function explainTheCall(language: Lang) {
    if (soundOn) {
      audioCtxRef.current ??= new AudioContext()
      void audioCtxRef.current.resume()
    }
    sourceRef.current?.close()
    setStages([])
    setExplanation('')
    setGeo(null)
    setLawText('')
    setOfflineSource(null)
    setStreaming(true)
    const url = `${BACKEND}/stream/canned?language=${encodeURIComponent(language)}`
    const source = new EventSource(url)
    sourceRef.current = source
    for (const name of STAGES) {
      source.addEventListener(name, (event) => {
        const data = JSON.parse((event as MessageEvent).data) as Stage
        setStages((prev) => [...prev, data])
        if (name === 'geometry') {
          const g = data as unknown as Geometry
          setGeo(g)
          const ctx = audioCtxRef.current
          if (ctx) {
            void playOffsideChord(ctx, g)
              .then((plan) => {
                const w = window as unknown as { __varsitySonification?: unknown }
                w.__varsitySonification = plan
              })
              .catch(() => {})
          }
        }
        if (name === 'law') {
          setLawText(String(data.text ?? ''))
        }
        if (name === 'verdict') {
          setExplanation(String(data.text ?? ''))
          if (data.law_text) setLawText(String(data.law_text))
          triggerHaptic(data as unknown as Geometry)
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

  // Airplane mode: explain entirely on-device, with NO backend call.
  async function explainOffline() {
    sourceRef.current?.close()
    setStages([])
    setExplanation('')
    setGeo(null)
    setLawText('')
    setOfflineSource(null)
    setOfflineStatus('')
    setStreaming(true)
    if (soundOn) {
      audioCtxRef.current ??= new AudioContext()
      void audioCtxRef.current.resume()
    }
    const { generateOffline } = await import('./offline')
    const res = await generateOffline({ onStatus: setOfflineStatus })
    setGeo(res.geo)
    const ctx = audioCtxRef.current
    if (ctx) {
      void playOffsideChord(ctx, res.geo)
        .then((plan) => {
          const w = window as unknown as { __varsitySonification?: unknown }
          w.__varsitySonification = plan
        })
        .catch(() => {})
    }
    setExplanation(res.text)
    setLawText(res.lawText)
    triggerHaptic(res.geo)
    setOfflineSource(res.source)
    setStreaming(false)
  }

  function selectLang(l: Lang) {
    setLang(l)
    if (explanation || streaming || geo) {
      explainTheCall(l)
    }
  }

  const t = UI[lang]
  const segBtn = (active: boolean) =>
    `rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
      active ? 'bg-emerald-500 text-slate-950' : 'text-slate-300 hover:text-white'
    }`

  return (
    <div className="flex w-full flex-col items-center gap-6 text-center">
      <div className="flex flex-wrap items-center justify-center gap-3">
        <div
          role="group"
          aria-label={t.langLabel}
          className="inline-flex rounded-full bg-slate-800/60 p-1"
        >
          {(['English', 'Spanish'] as const).map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} onClick={() => selectLang(l)} className={segBtn(lang === l)}>
              {UI[l].code}
            </button>
          ))}
        </div>
        <button
          type="button"
          aria-pressed={soundOn}
          aria-label="Spatial audio cue"
          onClick={() => setSoundOn((s) => !s)}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            soundOn ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800/60 text-slate-300 hover:text-white'
          }`}
        >
          {soundOn ? 'Sound on' : 'Sound off'}
        </button>
        <button
          type="button"
          aria-pressed={detail}
          onClick={() => setDetail((d) => !d)}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            detail ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800/60 text-slate-300 hover:text-white'
          }`}
        >
          {detail ? 'Detailed' : 'Plain'}
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => explainTheCall(lang)}
          disabled={streaming}
          className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-60"
        >
          {streaming ? t.explaining : t.explain}
        </button>
        <button
          onClick={() => void explainOffline()}
          disabled={streaming}
          className="rounded-full border border-emerald-500/60 px-6 py-3 font-medium text-emerald-300 transition-colors hover:bg-emerald-500/10 disabled:opacity-60"
        >
          Offline mode (on-device)
        </button>
        <button
          onClick={() => void readAloud(explanation, { lang: t.bcp47 })}
          disabled={streaming || !explanation}
          className="rounded-full border border-slate-500/60 px-6 py-3 font-medium text-slate-300 transition-colors hover:bg-slate-500/10 disabled:opacity-40"
        >
          Read aloud
        </button>
      </div>

      {offlineSource && (
        <p aria-hidden="true" data-testid="offline-source" className="text-xs text-emerald-400/80">
          {offlineSource === 'granite-nano-webgpu'
            ? 'Explained on-device by Granite Nano (WebGPU), no network.'
            : 'Explained on-device (deterministic, no network).'}
          {offlineStatus ? ` ${offlineStatus}` : ''}
        </p>
      )}

      {/* Pre-registered aria-live region: the screen reader speaks the verdict in place. */}
      <div ref={liveRef} aria-live="assertive" aria-atomic="true" role="status" lang={t.bcp47} className="sr-only">
        {explanation}
      </div>

      {detail && geo && (
        <section
          aria-label="Decision detail"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-slate-700/50"
        >
          <h3 className="text-sm font-semibold text-emerald-300">How this was decided</h3>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm text-slate-300">
            <dt className="text-slate-400">Verdict</dt>
            <dd>{geo.is_offside ? 'Offside' : 'Onside'}</dd>
            <dt className="text-slate-400">Margin past the offside line</dt>
            <dd>{Math.abs(geo.margin_meters).toFixed(2)} m</dd>
            <dt className="text-slate-400">How clear-cut</dt>
            <dd data-testid="confidence">{geo.confidence ?? 'n/a'}</dd>
          </dl>
          {lawText && (
            <>
              <h4 className="mt-3 text-sm font-semibold text-emerald-300">The Law</h4>
              <p lang="en" data-testid="law-text" className="mt-1 text-sm leading-relaxed text-slate-300">
                {lawText}
              </p>
            </>
          )}
        </section>
      )}

      {geo && (
        <figure aria-hidden="true" className="w-full max-w-2xl">
          <OffsidePitch geo={geo} />
          <figcaption className="mt-2 text-sm text-slate-400" lang={t.bcp47}>
            {t.caption(geo.margin_meters.toFixed(2), geo.is_offside)}
          </figcaption>
        </figure>
      )}

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
    </div>
  )
}
