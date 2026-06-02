import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import gsap from 'gsap'
import { OffsidePitch, type Geometry } from './OffsidePitch'
import { playOffsideChord } from './sonify'
import { readAloud } from './tts'
import { usePrefersReducedMotion } from './useReducedMotion'

// The 3D hero is heavy and purely decorative, so it is code-split and only loaded
// when motion is allowed (keeps the core fast and accessible).
const Hero3D = lazy(() => import('./Hero3D'))

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

export default function App() {
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
  const heroRef = useRef<HTMLDivElement>(null)
  const reducedMotion = usePrefersReducedMotion()

  // GSAP intro: a staggered rise of the hero content on load. The text is already
  // in the DOM (the screen reader reads it immediately); GSAP only animates
  // opacity/transform, and only when motion is allowed.
  useEffect(() => {
    if (reducedMotion || !heroRef.current) return
    const items = heroRef.current.querySelectorAll('[data-hero-item]')
    const anim = gsap.from(items, {
      y: 24,
      opacity: 0,
      duration: 0.7,
      ease: 'power3.out',
      stagger: 0.12,
    })
    return () => {
      anim.kill()
    }
  }, [reducedMotion])

  // The button is the deliberate user gesture that opens the stream AND unlocks
  // audio for the spatial-audio cue. Language is passed explicitly so re-narrating
  // on a language toggle does not race the lang state update.
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
          // Spatial-audio cue: a ~500ms HRTF chord of the three key players,
          // heard before the spoken explanation. Supplement, not a replacement.
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

  // Airplane mode: explain entirely on-device, with NO backend call. Geometry and
  // the Law text are bundled; Granite Nano (WebGPU) phrases it when available, else a
  // deterministic Law-grounded floor. Proves the explanation survives a cut network.
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
    // Re-narrate the same call in the new language if one is already showing.
    if (explanation || streaming || geo) {
      explainTheCall(l)
    }
  }

  const t = UI[lang]

  return (
    <>
      {/* Decorative 3D broadcast pitch behind the hero. aria-hidden, non-interactive,
          and only mounted when motion is allowed. */}
      {!reducedMotion && (
        <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0">
          <Suspense fallback={null}>
            <Hero3D />
          </Suspense>
        </div>
      )}

      <main
        ref={heroRef}
        className="relative z-10 min-h-screen flex flex-col items-center justify-center gap-8 px-6 py-16 text-center"
      >
        <h1 data-hero-item className="text-4xl sm:text-6xl font-semibold tracking-tight">
          VARSITY
        </h1>
        <p data-hero-item className="max-w-xl text-balance text-slate-300" lang={t.bcp47}>
          {t.sub}
        </p>

        <div data-hero-item className="flex flex-wrap items-center justify-center gap-3">
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

        {/* Spatial-audio cue toggle. The cue supplements the spoken explanation. */}
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

        {/* Detail / Plain toggle. Detailed surfaces the full Law text + the geometry
            breakdown, in direct response to a blind fan asking for rule information. */}
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

      <div data-hero-item className="flex flex-wrap items-center justify-center gap-3">
        <button
          onClick={() => explainTheCall(lang)}
          disabled={streaming}
          className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-60"
        >
          {streaming ? t.explaining : t.explain}
        </button>

        {/* Airplane mode: explain on-device with no backend call. */}
        <button
          onClick={() => void explainOffline()}
          disabled={streaming}
          className="rounded-full border border-emerald-500/60 px-6 py-3 font-medium text-emerald-300 transition-colors hover:bg-emerald-500/10 disabled:opacity-60"
        >
          Offline mode (on-device)
        </button>

        {/* Read aloud (sighted track only): the accessibility path stays the user's
            own screen reader; this is a supplementary spoken readout. */}
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

      {/* Detail panel: the full Law text + geometry breakdown + how clear-cut the call
          is. Accessible (real headings), so a screen-reader user gets the rule detail a
          blind fan asked for. Shown on demand via the Detailed toggle. */}
      {detail && geo && (
        <section
          aria-label="Decision detail"
          className="w-full max-w-2xl rounded-lg bg-slate-900/60 p-4 text-left ring-1 ring-slate-700/50"
        >
          <h2 className="text-sm font-semibold text-emerald-300">How this was decided</h2>
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
              <h3 className="mt-3 text-sm font-semibold text-emerald-300">The Law</h3>
              <p lang="en" data-testid="law-text" className="mt-1 text-sm leading-relaxed text-slate-300">
                {lawText}
              </p>
            </>
          )}
        </section>
      )}

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
    </>
  )
}
