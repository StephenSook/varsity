import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { BroadcastTicker } from './BroadcastTicker'
import { useLang, type Lang } from './i18n'
import { DiagnosticsPanel } from './DiagnosticsPanel'
import { KeyboardHelp } from './KeyboardHelp'
import { OffsidePitch, type Geometry } from './OffsidePitch'
import { usePrefersReducedMotion } from './useReducedMotion'

// The 3D pitch is heavy + decorative, so it is code-split and only mounted when motion
// is allowed; the SVG is the reduced-motion fallback (and the Suspense fallback while
// the chunk loads).
const OffsidePitch3D = lazy(() => import('./OffsidePitch3D'))
import { shareExplanation } from './share'
import { playBuildUp, playOffsideChord } from './sonify'
import { StageScrubber } from './StageScrubber'
import { readAloud, synthesizeClip } from './tts'

// Backend SSE base. Override with VITE_BACKEND_URL for a deployed backend.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'

const STAGES = ['trigger', 'decision', 'geometry', 'signal', 'law', 'granite', 'guardian', 'verdict'] as const

type Stage = { stage: string; [key: string]: unknown }

// Granite is multilingual (EN/DE/ES/FR/PT); VARSITY ships all five World Cup languages.
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
  French: {
    code: 'FR',
    bcp47: 'fr',
    langLabel: "Langue de l'explication",
    explain: "Expliquer l'action",
    explaining: 'Explication…',
    caption: (m, off) =>
      `Ligne de hors-jeu au niveau de l'avant-dernier défenseur · attaquant ${m} m ${off ? 'devant' : 'derrière'}`,
  },
  Portuguese: {
    code: 'PT',
    bcp47: 'pt',
    langLabel: 'Idioma da explicação',
    explain: 'Explicar o lance',
    explaining: 'Explicando…',
    caption: (m, off) =>
      `Linha de impedimento no penúltimo defensor · atacante ${m} m ${off ? 'à frente' : 'atrás'}`,
  },
  German: {
    code: 'DE',
    bcp47: 'de',
    langLabel: 'Sprache der Erklärung',
    explain: 'Die Szene erklären',
    explaining: 'Erkläre…',
    caption: (m, off) =>
      `Abseitslinie beim vorletzten Verteidiger · Angreifer ${m} m ${off ? 'davor' : 'dahinter'}`,
  },
}

type Scenario = 'offside' | 'onside' | 'tight' | 'penalty' | 'handball'
type ScenarioKind = 'geometry' | 'decision'

// Offside/onside/tight are REAL World Cup 2022 freeze-frames (Canada vs Morocco) whose
// verdict the geometry decides. Penalty/handball run the SAME RAG + Granite + Guardian
// engine over Law 14 / Law 12 (illustrative incidents, no geometry), proving VARSITY
// explains any VAR call, not just offside.
const SCENARIOS: { id: Scenario; label: string; kind: ScenarioKind }[] = [
  { id: 'offside', label: 'Offside', kind: 'geometry' },
  { id: 'onside', label: 'Onside', kind: 'geometry' },
  { id: 'tight', label: 'Tight call', kind: 'geometry' },
  { id: 'penalty', label: 'Penalty', kind: 'decision' },
  { id: 'handball', label: 'Handball', kind: 'decision' },
]
const kindOf = (id: Scenario): ScenarioKind =>
  SCENARIOS.find((s) => s.id === id)?.kind ?? 'geometry'

type Moment = {
  competition?: string
  matchName?: string
  minute?: number
} | null

type DecisionCard = { decisionType: string; incident: string; outcome: string } | null

type SpeechRecognitionEventLike = { results?: Array<Array<{ transcript: string }>> }
type SpeechRecognitionLike = {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: (e: SpeechRecognitionEventLike) => void
  start: () => void
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
    case 'decision':
      return ` — ${String(s.outcome)}`
    case 'signal':
      return ` — referee signal (Law ${String(s.law)})`
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

type Verbosity = 'minimal' | 'standard' | 'coach'
const VERBOSITY_ORDER: Verbosity[] = ['minimal', 'standard', 'coach']

// Verbosity control fights sonification/announcement fatigue: a verdict every 30s in
// full prose exhausts a screen-reader listener. Minimal = headline only; Standard =
// the full explanation; Coach = explanation plus how clear-cut the call was. The full
// text always stays in the visible panel; this only gates what the live region speaks.
function announceText(
  v: Verbosity,
  d: { text: string; isOffside: boolean; marginM: number; confidence?: string },
): string {
  if (v === 'minimal') {
    return d.isOffside ? `Offside, by ${Math.abs(d.marginM).toFixed(2)} metres.` : 'Onside.'
  }
  if (v === 'coach') {
    return d.confidence ? `${d.text} How clear-cut: ${d.confidence}.` : d.text
  }
  return d.text
}

export function Demo() {
  const [explanation, setExplanation] = useState('')
  const [liveMessage, setLiveMessage] = useState('')
  const [stages, setStages] = useState<Stage[]>([])
  const [geo, setGeo] = useState<Geometry | null>(null)
  const [lawText, setLawText] = useState('')
  const [detail, setDetail] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const { lang, setLang } = useLang()
  const [scenario, setScenario] = useState<Scenario>('offside')
  const [moment, setMoment] = useState<Moment>(null)
  const [decision, setDecision] = useState<DecisionCard>(null)
  const [signalCard, setSignalCard] = useState<{ text: string; law: string } | null>(null)
  const [question, setQuestion] = useState('')
  const [askedQuestion, setAskedQuestion] = useState('')
  const [soundOn, setSoundOn] = useState(true)
  const [buildUp, setBuildUp] = useState(false)
  const [offlineSource, setOfflineSource] = useState<string | null>(null)
  const [offlineRetrieval, setOfflineRetrieval] = useState<'orama-bm25' | 'bundled' | null>(null)
  const [offlineStatus, setOfflineStatus] = useState('')
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [showHelp, setShowHelp] = useState(false)
  const [showDiag, setShowDiag] = useState(false)
  const [shareStatus, setShareStatus] = useState('')
  const [live, setLive] = useState(false)
  const [reviewing, setReviewing] = useState<{
    source: string
    detail: string
    minute: number
  } | null>(null)
  const [verbosity, setVerbosity] = useState<Verbosity>(() => {
    const v = typeof localStorage !== 'undefined' && localStorage.getItem('varsity-verbosity')
    return v === 'minimal' || v === 'coach' ? v : 'standard'
  })
  const liveRef = useRef<HTMLDivElement>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const nbspRef = useRef(false)

  // Set the live-region message, alternating a trailing non-breaking space so an
  // identical re-announcement still produces a textContent diff: Safari + VoiceOver
  // will not re-speak an unchanged string (WordPress core trac #36853).
  function announce(message: string) {
    nbspRef.current = !nbspRef.current
    setLiveMessage(message + (nbspRef.current ? ' ' : ''))
  }

  function applyVerbosity(next: Verbosity) {
    if (typeof localStorage !== 'undefined') localStorage.setItem('varsity-verbosity', next)
    setVerbosity(next)
  }

  function cycleVerbosity() {
    setVerbosity((cur) => {
      const next = VERBOSITY_ORDER[(VERBOSITY_ORDER.indexOf(cur) + 1) % VERBOSITY_ORDER.length]
      if (typeof localStorage !== 'undefined') localStorage.setItem('varsity-verbosity', next)
      return next
    })
  }
  const startRef = useRef(0)
  const reducedMotion = usePrefersReducedMotion()

  // Sonify the geometry: optionally the "gasp moment" build-up (the approach to the
  // line) first, then the spatial chord + verdict earcon.
  function sonifyGeometry(ctx: AudioContext, g: Geometry) {
    const w = window as unknown as { __varsitySonification?: unknown }
    const chord = () =>
      playOffsideChord(ctx, g)
        .then((plan) => {
          w.__varsitySonification = plan
        })
        .catch(() => {})
    if (buildUp) {
      void playBuildUp(ctx, g)
        .then(chord)
        .catch(() => {})
    } else {
      void chord()
    }
  }

  function explainTheCall(language: Lang, scenarioOverride?: Scenario) {
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
    setLatencyMs(null)
    setReviewing(null)
    setMoment(null)
    setDecision(null)
    setSignalCard(null)
    startRef.current = performance.now()
    setStreaming(true)
    // Geometry scenarios (offside/onside/tight) stream /stream/{canned,live}; rule
    // decisions (penalty/handball) stream /stream/decision over the SAME RAG + Granite +
    // Guardian engine. Live mode (geometry only) first emits the transitional "VAR is
    // reviewing" announcement, then the same explanation pipeline.
    const sc = scenarioOverride ?? scenario
    const langParam = encodeURIComponent(language)
    const url =
      kindOf(sc) === 'decision'
        ? `${BACKEND}/stream/decision?type=${sc}&language=${langParam}`
        : `${BACKEND}/stream/${live ? 'live' : 'canned'}?language=${langParam}&scenario=${sc}`
    const source = new EventSource(url)
    sourceRef.current = source
    source.addEventListener('reviewing', (event) => {
      const data = JSON.parse((event as MessageEvent).data) as {
        source: string
        detail: string
        minute: number
      }
      setReviewing(data)
    })
    for (const name of STAGES) {
      source.addEventListener(name, (event) => {
        const data = JSON.parse((event as MessageEvent).data) as Stage
        setStages((prev) => [...prev, data])
        if (name === 'trigger') {
          setMoment({
            competition: data.competition ? String(data.competition) : undefined,
            matchName: data.match_name ? String(data.match_name) : undefined,
            minute: typeof data.minute === 'number' ? data.minute : undefined,
          })
        }
        if (name === 'decision') {
          setDecision({
            decisionType: String(data.decision_type ?? ''),
            incident: String(data.incident ?? ''),
            outcome: String(data.outcome ?? ''),
          })
        }
        if (name === 'signal') {
          setSignalCard({ text: String(data.text ?? ''), law: String(data.law ?? '') })
        }
        if (name === 'geometry') {
          const g = data as unknown as Geometry
          setGeo(g)
          const ctx = audioCtxRef.current
          if (ctx) sonifyGeometry(ctx, g)
        }
        if (name === 'law') {
          setLawText(String(data.text ?? ''))
        }
        if (name === 'verdict') {
          const text = String(data.text ?? '')
          setExplanation(text)
          const isDecision = Boolean(data.decision_type)
          announce(
            isDecision
              ? text
              : announceText(verbosity, {
                  text,
                  isOffside: Boolean(data.is_offside),
                  marginM: Number(data.margin_meters ?? 0),
                  confidence: data.confidence ? String(data.confidence) : undefined,
                }),
          )
          if (data.law_text) setLawText(String(data.law_text))
          if (!isDecision) triggerHaptic(data as unknown as Geometry)
          setLatencyMs(performance.now() - startRef.current)
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
    setMoment(null)
    setDecision(null)
    setSignalCard(null)
    setLatencyMs(null)
    startRef.current = performance.now()
    setStreaming(true)
    if (soundOn) {
      audioCtxRef.current ??= new AudioContext()
      void audioCtxRef.current.resume()
    }
    const { generateOffline } = await import('./offline')
    const res = await generateOffline({ onStatus: setOfflineStatus })
    setGeo(res.geo)
    const ctx = audioCtxRef.current
    if (ctx) sonifyGeometry(ctx, res.geo)
    setExplanation(res.text)
    announce(
      announceText(verbosity, {
        text: res.text,
        isOffside: res.geo.is_offside,
        marginM: res.geo.margin_meters,
        confidence: res.geo.confidence,
      }),
    )
    setLawText(res.lawText)
    triggerHaptic(res.geo)
    setLatencyMs(performance.now() - startRef.current)
    setOfflineSource(res.source)
    setOfflineRetrieval(res.retrieval)
    setStreaming(false)
  }

  function selectScenario(s: Scenario) {
    setScenario(s)
    explainTheCall(lang, s)
  }

  function selectLang(l: Lang) {
    setLang(l)
    if (explanation || streaming || geo) {
      explainTheCall(l)
    }
  }

  // The "ask any rule" oracle: stream a free-text question through retrieve -> Granite
  // (grounded in the retrieved Law) -> Guardian -> aria-live, in the chosen language.
  function askQuestion(q: string) {
    const asked = q.trim()
    if (!asked || streaming) return
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
    setLatencyMs(null)
    setReviewing(null)
    setMoment(null)
    setDecision(null)
    setSignalCard(null)
    setAskedQuestion(asked)
    startRef.current = performance.now()
    setStreaming(true)
    const url = `${BACKEND}/stream/ask?q=${encodeURIComponent(asked)}&language=${encodeURIComponent(lang)}`
    const source = new EventSource(url)
    sourceRef.current = source
    for (const name of STAGES) {
      source.addEventListener(name, (event) => {
        const data = JSON.parse((event as MessageEvent).data) as Stage
        setStages((prev) => [...prev, data])
        if (name === 'law') setLawText(String(data.text ?? ''))
        if (name === 'verdict') {
          const text = String(data.text ?? '')
          setExplanation(text)
          announce(text)
          if (data.law_text) setLawText(String(data.law_text))
          setLatencyMs(performance.now() - startRef.current)
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

  // Optional voice input (Web Speech API): screen-reader-friendly + hands-free. A graceful
  // no-op where unsupported; the text input is always available.
  function startVoiceInput() {
    const w = window as unknown as {
      webkitSpeechRecognition?: new () => SpeechRecognitionLike
      SpeechRecognition?: new () => SpeechRecognitionLike
    }
    const Rec = w.SpeechRecognition ?? w.webkitSpeechRecognition
    if (!Rec) return
    const rec = new Rec()
    rec.lang = UI[lang].bcp47
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.onresult = (e: SpeechRecognitionEventLike) => {
      const said = e.results?.[0]?.[0]?.transcript ?? ''
      if (said) {
        setQuestion(said)
        askQuestion(said)
      }
    }
    rec.start()
  }

  async function shareCurrent() {
    if (!explanation) return
    setShareStatus('Preparing clip…')
    const clip = await synthesizeClip(explanation, { lang: UI[lang].bcp47 })
    const result = await shareExplanation(explanation, clip)
    const msg: Record<string, string> = {
      'shared-clip': 'Shared the audio clip.',
      'shared-text': 'Shared the explanation.',
      downloaded: 'Downloaded the audio clip.',
      copied: 'Copied the explanation to the clipboard.',
      cancelled: '',
      unavailable: 'Sharing is not available in this browser.',
    }
    setShareStatus(msg[result] ?? '')
  }

  // Keyboard power mode: every core action from one keypress (ignored while typing in
  // a field). The on-screen buttons stay tab-focusable; this is the power layer on top.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const tag = (e.target as HTMLElement | null)?.tagName ?? ''
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(tag)) return
      const langs = ['English', 'Spanish', 'French', 'Portuguese', 'German'] as const
      const k = e.key.toLowerCase()
      if (k === 'e') {
        if (!streaming) explainTheCall(lang)
      } else if (k === 'o') {
        if (!streaming) void explainOffline()
      } else if (k === 'r') {
        if (explanation && !streaming) void readAloud(explanation, { lang: UI[lang].bcp47 })
      } else if (k === 'c') {
        if (explanation && !streaming) void shareCurrent()
      } else if (k === 's') {
        setSoundOn((s) => !s)
      } else if (k === 'b') {
        setBuildUp((b) => !b)
      } else if (k === 'd') {
        setDetail((d) => !d)
      } else if (k === 'l') {
        setLive((v) => !v)
      } else if (k === 'v') {
        cycleVerbosity()
      } else if (e.key === '?') {
        setShowHelp((h) => !h)
      } else if (k >= '1' && k <= '5') {
        selectLang(langs[Number(k) - 1])
      } else {
        return
      }
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lang, streaming, explanation, live, scenario])

  // Re-announce the current verdict at the new level when verbosity changes.
  useEffect(() => {
    if (!explanation || !geo) return
    announce(
      announceText(verbosity, {
        text: explanation,
        isOffside: geo.is_offside,
        marginM: geo.margin_meters,
        confidence: geo.confidence,
      }),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verbosity])

  const t = UI[lang]
  const voiceSupported =
    typeof window !== 'undefined' &&
    ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)
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
          {(['English', 'Spanish', 'French', 'Portuguese', 'German'] as const).map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} aria-label={l} onClick={() => selectLang(l)} className={segBtn(lang === l)}>
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
          aria-pressed={buildUp}
          aria-label="Build-up sonification (illustrative approach to the line)"
          onClick={() => setBuildUp((b) => !b)}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            buildUp ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800/60 text-slate-300 hover:text-white'
          }`}
        >
          {buildUp ? 'Build-up on' : 'Build-up'}
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
        <button
          type="button"
          aria-pressed={live}
          aria-label="Live World Cup feed"
          onClick={() => setLive((v) => !v)}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            live ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800/60 text-slate-300 hover:text-white'
          }`}
        >
          {live ? 'Live feed' : 'Replay'}
        </button>
        <div
          role="group"
          aria-label="Announcement verbosity"
          className="inline-flex rounded-full bg-slate-800/60 p-1"
        >
          {VERBOSITY_ORDER.map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={verbosity === v}
              aria-label={`${v} verbosity`}
              onClick={() => applyVerbosity(v)}
              className={segBtn(verbosity === v)}
            >
              {v === 'minimal' ? 'Min' : v === 'standard' ? 'Std' : 'Coach'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col items-center gap-2">
        <div
          role="group"
          aria-label="Decision scenario (real World Cup 2022 frames)"
          className="inline-flex rounded-full bg-slate-800/60 p-1"
        >
          {SCENARIOS.map((s) => (
            <button
              key={s.id}
              type="button"
              aria-pressed={scenario === s.id}
              aria-label={`${s.label} scenario`}
              onClick={() => selectScenario(s.id)}
              className={segBtn(scenario === s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>
        {moment?.matchName && (
          <p data-testid="moment-byline" className="text-xs text-slate-400">
            {moment.competition ?? 'FIFA World Cup 2022'} · {moment.matchName}
            {typeof moment.minute === 'number' ? ` · ${moment.minute}'` : ''}
          </p>
        )}
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
        <button
          onClick={() => void shareCurrent()}
          disabled={streaming || !explanation}
          className="rounded-full border border-slate-500/60 px-6 py-3 font-medium text-slate-300 transition-colors hover:bg-slate-500/10 disabled:opacity-40"
        >
          Share clip
        </button>
      </div>

      {/* The rule oracle: ask any Laws-of-the-Game question, answered grounded in the
          retrieved Law (Granite + Guardian), spoken through the same aria-live region. */}
      <form
        onSubmit={(e) => {
          e.preventDefault()
          askQuestion(question)
        }}
        aria-label="Ask the Laws of the Game"
        className="flex w-full max-w-2xl flex-wrap items-center justify-center gap-2"
      >
        <label htmlFor="ask-input" className="sr-only">
          Ask any question about the Laws of the Game
        </label>
        <input
          id="ask-input"
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask any rule: why was that a red card?"
          className="min-w-0 flex-1 rounded-full bg-slate-800/60 px-5 py-3 text-sm text-slate-100 placeholder:text-slate-500 ring-1 ring-slate-700/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
        />
        <button
          type="submit"
          disabled={streaming || !question.trim()}
          className="rounded-full bg-sky-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-sky-400 disabled:opacity-50"
        >
          Ask
        </button>
        {voiceSupported && (
          <button
            type="button"
            onClick={startVoiceInput}
            disabled={streaming}
            aria-label="Ask by voice"
            className="rounded-full border border-slate-500/60 px-4 py-3 font-medium text-slate-300 transition-colors hover:bg-slate-500/10 disabled:opacity-40"
          >
            Voice
          </button>
        )}
      </form>

      {askedQuestion && (
        <p className="max-w-2xl text-sm text-slate-400">
          You asked: <span className="text-slate-200">{askedQuestion}</span>
        </p>
      )}

      {reviewing && (
        <div
          role="status"
          aria-live="polite"
          className="glass w-full max-w-md rounded-xl p-3 text-left"
        >
          <p className="text-sm font-medium text-emerald-200">
            Minute {reviewing.minute}: VAR is reviewing. {reviewing.detail}.
          </p>
          <p className="mt-0.5 font-mono text-xs text-slate-400">
            trigger source: {reviewing.source}
          </p>
        </div>
      )}

      {shareStatus && (
        <p role="status" aria-live="polite" className="text-xs text-slate-400">
          {shareStatus}
        </p>
      )}

      {offlineSource && (
        <p aria-hidden="true" data-testid="offline-source" className="text-xs text-emerald-400/80">
          {offlineSource === 'granite-nano-webgpu'
            ? 'Explained on-device by Granite Nano (WebGPU), no network.'
            : 'Explained on-device (deterministic, no network).'}
          {offlineRetrieval === 'orama-bm25' ? ' Law retrieved on-device (Orama BM25).' : ''}
          {offlineStatus ? ` ${offlineStatus}` : ''}
        </p>
      )}

      {/* Pre-registered aria-live region: the screen reader speaks the verdict in place,
          at the chosen verbosity, with a re-announce-safe trailing space. */}
      <div ref={liveRef} aria-live="assertive" aria-atomic="true" role="status" lang={t.bcp47} className="sr-only">
        {liveMessage}
      </div>

      {decision && (
        <section
          aria-label="Illustrative incident"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-amber-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-amber-300/80">
            Illustrative incident · {decision.decisionType}
          </p>
          <p className="mt-1 text-sm text-slate-300">{decision.incident}</p>
          <p className="mt-1 text-sm font-medium text-emerald-200">Outcome: {decision.outcome}</p>
        </section>
      )}

      {signalCard && (
        <section
          aria-label="Referee signal"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-3 text-left ring-1 ring-sky-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-sky-300/80">
            Referee signal · Law {signalCard.law}
          </p>
          <p className="mt-1 text-sm text-slate-300">{signalCard.text}</p>
        </section>
      )}

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
          {reducedMotion ? (
            <OffsidePitch geo={geo} />
          ) : (
            <Suspense fallback={<OffsidePitch geo={geo} />}>
              <OffsidePitch3D geo={geo} />
            </Suspense>
          )}
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

      <BroadcastTicker latencyMs={latencyMs} />

      <StageScrubber stages={stages} describe={describe} />

      <div className="flex flex-wrap items-center justify-center gap-4">
        <button
          type="button"
          aria-pressed={showHelp}
          onClick={() => setShowHelp((h) => !h)}
          className="text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          Keyboard shortcuts (press ?)
        </button>
        <button
          type="button"
          aria-pressed={showDiag}
          onClick={() => setShowDiag((d) => !d)}
          className="text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          {showDiag ? 'Hide diagnostics' : 'On-device diagnostics'}
        </button>
      </div>
      <KeyboardHelp open={showHelp} />
      {showDiag && <DiagnosticsPanel />}
    </div>
  )
}
