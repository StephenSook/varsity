import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import { BroadcastTicker } from './BroadcastTicker'
import { verbalizeForSpeech } from './speech'
import { graniteSpeechEnabled, listen, onDeviceAsrAvailable } from './voice'
import { LANGS, useLang, type Lang } from './i18n'
import { announceText, type Verbosity } from './announce'
import { MixedScriptText } from './mixedScript'
import { DiagnosticsPanel } from './DiagnosticsPanel'
import { PipelineWaterfall } from './PipelineWaterfall'
import { KeyboardHelp } from './KeyboardHelp'
import { OffsidePitch, type Geometry } from './OffsidePitch'
import { LazyBoundary } from './LazyBoundary'
import { usePrefersReducedMotion } from './useReducedMotion'

// The 3D pitch is heavy + decorative, so it is code-split and only mounted when motion
// is allowed; the SVG is the reduced-motion fallback (and the Suspense fallback while
// the chunk loads).
const OffsidePitch3D = lazy(() => import('./OffsidePitch3D'))
import { shareExplanation } from './share'
import {
  detectDefaultSpatialMode,
  playBuildUp,
  playMarginChord,
  playOffsideChord,
  playSpatialScan,
  type SpatialMode,
  vizAnalyser,
} from './sonify'
import { VerdictViz } from './VerdictViz'
import { StageScrubber } from './StageScrubber'
import { playPitchCorrectedSpearcon, readAloud, synthesizeClip } from './tts'

// Backend SSE base. Override with VITE_BACKEND_URL for a deployed backend.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'

const STAGES = ['trigger', 'screen', 'decision', 'geometry', 'uncertainty_budget', 'geometry_descriptors', 'discourse', 'signal', 'proof', 'verbalizer', 'parallax', 'causal', 'critical_questions', 'law', 'granite', 'guardian', 'verification', 'completeness', 'provenance', 'citation_metrics', 'verdict'] as const

// Law-11 sub-clauses as spearcon-able rule shortcuts (Walker et al., Human Factors 2013).
const LAW11_SPEARCONS = [
  'In the opponents half',
  'Beyond the second-to-last defender',
  'Nearer the goal line than the ball',
  'Interfering with play',
  'Interfering with an opponent',
  'Gaining an advantage',
  'Deliberate play by a defender',
  'Received from a goal kick',
  'Received from a throw-in',
  'Received from a corner',
] as const

type Stage = { stage: string; [key: string]: unknown }
// The verdict SSE payload, named so a typo in the spoken-field reads (the verdict + margin a blind
// fan HEARS) is a compile error, not a silent '0 m'. The wire is still loosely produced upstream,
// so the reads keep their Number/Boolean/String coercion as a defensive guard.
type VerdictData = {
  text?: string
  decision_type?: string
  is_offside?: boolean
  margin_meters?: number
  confidence?: string
  law_text?: string
  sigma_meters?: number
  p_verdict?: number
  likelihood?: string
  uncertainty_note?: string
  counterfactual_meters?: number
}

// Granite is multilingual (EN/DE/ES/FR/PT); VARSITY ships all five World Cup languages.
const UI: Record<
  Lang,
  {
    code: string
    bcp47: string
    langLabel: string
    explain: string
    explaining: string
    error: string
    reannounce: string
    caption: (m: string, off: boolean) => string
  }
> = {
  English: {
    code: 'EN',
    bcp47: 'en',
    langLabel: 'Explanation language',
    explain: 'Explain the call',
    explaining: 'Explaining...',
    error: 'Sorry, the explanation could not load. On a first visit the backend may be waking up; please wait about 30 seconds and try again.',
    reannounce: 'Re-announce in English',
    caption: (m, off) =>
      `Offside line at the second-to-last defender · attacker ${m} m ${off ? 'ahead' : 'behind'}`,
  },
  Spanish: {
    code: 'ES',
    bcp47: 'es',
    langLabel: 'Idioma de la explicación',
    explain: 'Explicar la jugada',
    explaining: 'Explicando...',
    error: 'No se pudo cargar la explicación. En la primera visita el servidor puede estar activándose; espera unos 30 segundos e inténtalo de nuevo.',
    reannounce: 'Volver a anunciar en español',
    caption: (m, off) =>
      `Línea de fuera de juego en el penúltimo defensor · atacante ${m} m ${off ? 'por delante' : 'por detrás'}`,
  },
  French: {
    code: 'FR',
    bcp47: 'fr',
    langLabel: "Langue de l'explication",
    explain: "Expliquer l'action",
    explaining: 'Explication...',
    error: "Impossible de charger l'explication. Lors d'une première visite le serveur peut être en train de démarrer; patientez environ 30 secondes et réessayez.",
    reannounce: 'Réannoncer en français',
    caption: (m, off) =>
      `Ligne de hors-jeu au niveau de l'avant-dernier défenseur · attaquant ${m} m ${off ? 'devant' : 'derrière'}`,
  },
  Portuguese: {
    code: 'PT',
    bcp47: 'pt',
    langLabel: 'Idioma da explicação',
    explain: 'Explicar o lance',
    explaining: 'Explicando...',
    error: 'Não foi possível carregar a explicação. Na primeira visita o servidor pode estar inicializando; aguarde cerca de 30 segundos e tente novamente.',
    reannounce: 'Anunciar novamente em português',
    caption: (m, off) =>
      `Linha de impedimento no penúltimo defensor · atacante ${m} m ${off ? 'à frente' : 'atrás'}`,
  },
  German: {
    code: 'DE',
    bcp47: 'de',
    langLabel: 'Sprache der Erklärung',
    explain: 'Die Szene erklären',
    explaining: 'Erkläre...',
    error: 'Die Erklärung konnte nicht geladen werden. Beim ersten Besuch startet der Server möglicherweise gerade; bitte warte etwa 30 Sekunden und versuche es erneut.',
    reannounce: 'Erneut auf Deutsch ansagen',
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
      return ` · ${String(s.source)}`
    case 'geometry':
      return ` · margin ${String(s.margin_meters)}m, ${s.is_offside ? 'offside' : 'onside'}`
    case 'uncertainty_budget':
      return ` · ±${String(s.expanded_uncertainty_m)}m at 95% GUM coverage, ${String(s.entropy_bits)} bits`
    case 'geometry_descriptors': {
      const z = s.lateral_zone as { channel?: string } | undefined
      const where = z?.channel ? `, ${z.channel} channel` : ''
      return ` · line tilt ${String(s.tilt_deg)}°, ${String(s.thickness_m)}m deep, ${String(s.free_space_behind_line_m2)}m² free behind the line${where}`
    }
    case 'discourse':
      return s.connective
        ? ` · ${String(s.connective)}`
        : ` · ${String(s.decisions_seen)} decision(s) seen this match`
    case 'law':
      return ` · Law ${String(s.law)} (${String(s.title)})`
    case 'granite':
      return ` · ${String(s.model)}`
    case 'guardian':
      return ` · Granite Guardian: risk=${String(s.answer) || 'n/a'} -> ${s.safe ? 'SAFE' : 'flagged'}, cites Law: ${String(s.cites_law)}`
    case 'decision':
      return ` · ${String(s.outcome)}`
    case 'signal':
      return ` · referee signal (Law ${String(s.law)})`
    case 'proof':
      return ' · Law 11 rule proof'
    case 'verbalizer':
      return ` · faithful proof prose (${String(s.verdict)})`
    case 'parallax':
      return ` · camera parallax ~${String(s.apparent_shift_cm)} cm`
    case 'causal':
      return ` · ${String(s.fact)} rather than ${String(s.foil)}`
    case 'critical_questions':
      return ' · critical questions answered'
    case 'verification':
      return ` · ${String(s.passed)}/${String(s.total)} critics passed`
    case 'completeness':
      return ` · ${String(s.disclosed)}/${String(s.total)} disclosures`
    case 'provenance':
      return ` · ${String(s.link_count)} grounded claims${s.guardian_model ? ` · Guardian ${String(s.guardian_model)}` : ''}`
    case 'citation_metrics':
      return ` · citation precision ${String(s.precision)}, recall ${String(s.recall)}`
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

const VERBOSITY_ORDER: Verbosity[] = ['minimal', 'standard', 'coach']

export function Demo() {
  const [explanation, setExplanation] = useState('')
  const [liveMessage, setLiveMessage] = useState('')
  const [stages, setStages] = useState<Stage[]>([])
  const [geo, setGeo] = useState<Geometry | null>(null)
  // The deterministic GUM spoken line (coverage interval + IPCC hedge with its numeric range),
  // captured from the uncertainty_budget stage and appended to the spoken verdict so the blind
  // fan HEARS the honest uncertainty, not just sees it in the trace.
  const budgetSpokenRef = useRef('')
  // The discourse lead-in (references decisions already explained earlier in this match), captured
  // from the discourse stage and prepended to the spoken verdict.
  const discourseRef = useRef('')
  // The deterministic spatial line (which channel/wing + metres to the nearer touchline), captured
  // from the geometry_descriptors stage, so a blind fan HEARS where on the pitch it happened, not
  // only the margin. Spoken at standard/coach verbosity; withheld at minimal (kept terse).
  const spatialSpokenRef = useRef('')
  const [lawText, setLawText] = useState('')
  const [detail, setDetail] = useState(false)
  const [streaming, setStreaming] = useState(false)
  // A visible, role=alert error message for a stream/parse failure. The sr-only verdict region
  // stays for verdicts only; routing errors here gives a sighted judge a visible signal AND lets
  // assistive tech announce it once (role=alert) without the verdict region double-speaking.
  const [errorMsg, setErrorMsg] = useState('')
  const { lang, setLang } = useLang()
  const [scenario, setScenario] = useState<Scenario>('offside')
  const [moment, setMoment] = useState<Moment>(null)
  const [decision, setDecision] = useState<DecisionCard>(null)
  const [signalCard, setSignalCard] = useState<{ text: string; law: string } | null>(null)
  const [proof, setProof] = useState<{
    steps: { key: string; claim: string; status: string; law: string; role: string }[]
    consistent: boolean
    conclusion: string
  } | null>(null)
  const [verification, setVerification] = useState<{
    verified: boolean
    hardPassed: number
    hardTotal: number
    advisoryPassed: number
    advisoryTotal: number
    critics: { name: string; passed: boolean; detail: string; kind: string }[]
  } | null>(null)
  const [parallax, setParallax] = useState<{
    distanceM: number
    angleDeg: number
    shiftCm: number
    note: string
  } | null>(null)
  const [causal, setCausal] = useState<{
    fact: string
    foil: string
    narration: string
  } | null>(null)
  const [criticalQuestions, setCriticalQuestions] = useState<{
    scheme: string
    questions: { q: string; a: string }[]
  } | null>(null)
  const [completeness, setCompleteness] = useState<{
    score: number
    complete: boolean
    disclosures: { name: string; disclosed: boolean; detail: string }[]
  } | null>(null)
  const [provenance, setProvenance] = useState<{
    hash: string
    grounded: boolean
    proofConsistent: boolean
    verified: boolean
    links: { claim: string; law_clause: string; source: string }[]
  } | null>(null)
  const [varsityCall, setVarsityCall] = useState<{
    marginM: number
    sigmaM: number
    band: string
    p: number
    likelihood: string
    note: string
    counterfactualM: number
    isOffside: boolean
  } | null>(null)
  const [question, setQuestion] = useState('')
  const [askedQuestion, setAskedQuestion] = useState('')
  const [voiceStatus, setVoiceStatus] = useState('')
  const [soundOn, setSoundOn] = useState(true)
  const [buildUp, setBuildUp] = useState(false)
  const [offlineSource, setOfflineSource] = useState<string | null>(null)
  const [offlineRetrieval, setOfflineRetrieval] = useState<'orama-bm25' | 'bundled' | null>(null)
  const [offlineStatus, setOfflineStatus] = useState('')
  // Opt into the high-accuracy on-device tier (Granite 4.0 1B, a ~1.5 GB one-time download).
  const [highAccuracyOffline, setHighAccuracyOffline] = useState(false)
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [showHelp, setShowHelp] = useState(false)
  const [showDiag, setShowDiag] = useState(false)
  const [shareStatus, setShareStatus] = useState('')
  const [live, setLive] = useState(false)
  const [reviewing, setReviewing] = useState<{
    source: string
    detail: string
    minute: number | null
  } | null>(null)
  const [verbosity, setVerbosity] = useState<Verbosity>(() => {
    const v = typeof localStorage !== 'undefined' && localStorage.getItem('varsity-verbosity')
    return v === 'minimal' || v === 'coach' ? v : 'standard'
  })
  const [audioPrefs, setAudioPrefs] = useState<{
    preamble: boolean
    volume: number
    rate: number
    mode: SpatialMode
  }>(() => {
    try {
      const raw = typeof localStorage !== 'undefined' && localStorage.getItem('varsity-audio')
      if (raw) {
        const p = JSON.parse(raw)
        return {
          preamble: p.preamble !== false,
          volume: typeof p.volume === 'number' ? p.volume : 1,
          rate: typeof p.rate === 'number' ? p.rate : 1,
          mode:
            p.mode === 'stereo' || p.mode === 'mono' || p.mode === 'hrtf'
              ? p.mode
              : detectDefaultSpatialMode(),
        }
      }
    } catch {
      // ignore a malformed pref
    }
    return { preamble: true, volume: 1, rate: 1, mode: detectDefaultSpatialMode() }
  })
  const updateAudioPrefs = (patch: Partial<typeof audioPrefs>) =>
    setAudioPrefs((p) => {
      const next = { ...p, ...patch }
      try {
        localStorage.setItem('varsity-audio', JSON.stringify(next))
      } catch {
        // ignore
      }
      return next
    })
  const liveRef = useRef<HTMLDivElement>(null)
  const sourceRef = useRef<EventSource | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const [audioActive, setAudioActive] = useState(false)
  // The all-IBM Granite Speech voice-input opt-in (experimental; falls back to Whisper on any error).
  const [graniteSpeech, setGraniteSpeech] = useState(() => graniteSpeechEnabled())
  // A visible running log of everything the screen reader announced, so a SIGHTED judge can read
  // exactly what a blind fan hears (the screen-reader-native experience made visible).
  const [transcript, setTranscript] = useState<string[]>([])
  const [showTranscript, setShowTranscript] = useState(false)
  const [showTiming, setShowTiming] = useState(false)
  const nbspRef = useRef(false)

  // Set the live-region message, alternating a trailing non-breaking space so an
  // identical re-announcement still produces a textContent diff: Safari + VoiceOver
  // will not re-speak an unchanged string (WordPress core trac #36853).
  function announce(message: string) {
    nbspRef.current = !nbspRef.current
    setLiveMessage(verbalizeForSpeech(message, UI[lang].bcp47) + (nbspRef.current ?' ' : ''))
    if (message.trim()) setTranscript((prev) => [...prev.slice(-29), message.trim()])
  }

  // Screen-reader language dual-path. Markup conformance (per-node + page `lang`, WCAG 3.1.2)
  // does NOT guarantee the AT switches voice on a live update: NVDA #4396 (open since 2014)
  // does not speak an aria-live change in the node's `lang`, and macOS VoiceOver ignores `lang`
  // entirely (it language-detects). The documented NVDA fix is to FOCUS the node, which makes it
  // re-pronounce correctly. We expose that as a button so a language switch is actually heard in
  // the new voice; the bundled Read-aloud (tts.ts) is the only hard cross-AT guarantee.
  function reAnnounce() {
    announce(liveMessage.replace(/\s+$/, ''))
    liveRef.current?.focus()
  }

  // Keep the page language in sync so the whole UI is programmatically the chosen language
  // (WCAG 3.1.1 Language of Page); the English IFAB Law text keeps its own lang="en".
  useEffect(() => {
    if (typeof document !== 'undefined') document.documentElement.lang = UI[lang].bcp47
  }, [lang])

  // Close any in-flight stream + the audio context on unmount, so a route change or a dev
  // double-mount never leaks an open EventSource connection or an AudioContext.
  useEffect(() => {
    return () => {
      sourceRef.current?.close()
      const ctx = audioCtxRef.current
      if (ctx && ctx.state !== 'closed') void ctx.close()
    }
  }, [])

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
  const audioOpts = (band?: string) => ({
    band,
    preamble: audioPrefs.preamble,
    gain: 0.12 * audioPrefs.volume,
    mode: audioPrefs.mode,
  })

  function sonifyGeometry(ctx: AudioContext, g: Geometry) {
    // Prime the decorative spectrum analyser on the output bus, then mark audio active so the
    // aria-hidden verdict visualization animates while the chord plays.
    vizAnalyser(ctx)
    setAudioActive(true)
    window.setTimeout(() => setAudioActive(false), buildUp ? 4200 : 2600)
    const w = window as unknown as { __varsitySonification?: unknown }
    const chord = () =>
      playOffsideChord(ctx, g, audioOpts(g.confidence))
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
    // The Plomp-Levelt margin chord follows the spatial verdict chord: the listener hears the
    // call's closeness as roughness (a knife-edge call beats; a clear call is consonant).
    try {
      playMarginChord(ctx, g, 0.1 * audioPrefs.volume, buildUp ? 3.4 : 1.8)
    } catch {
      /* WebAudio unavailable */
    }
  }

  // Onboarding tutorial: walk a blind listener through the earcon vocabulary, one labelled
  // sound at a time, so the spatial + bouba/kiki cues are learnable before a live call.
  async function runTutorial() {
    audioCtxRef.current ??= new AudioContext()
    const ctx = audioCtxRef.current
    await ctx.resume()
    const tGeo = (attacker_x: number, offside_line_x: number, is_offside: boolean): Geometry => ({
      attacker_x,
      offside_line_x,
      is_offside,
      margin_meters: Math.round((attacker_x - offside_line_x) * 0.9144 * 100) / 100,
      players: [{ x: offside_line_x - 8, y: 40, teammate: true, actor: true }],
      pitch: { length: 120, width: 80 },
    })
    const steps: { label: string; geo: Geometry; band: string }[] = [
      { label: 'A clear offside, well beyond the line.', geo: tGeo(112, 100, true), band: 'clear' },
      {
        label: 'A tight, knife-edge offside, right on the line.',
        geo: tGeo(100.3, 100, true),
        band: 'very tight',
      },
      { label: 'An onside call, behind the line.', geo: tGeo(96, 100, false), band: 'clear' },
    ]
    for (const s of steps) {
      announce(s.label)
      await playOffsideChord(ctx, s.geo, audioOpts(s.band)).catch(() => {})
    }
    announce('End of sound tutorial.')
  }

  function explainTheCall(language: Lang, scenarioOverride?: Scenario) {
    if (soundOn) {
      audioCtxRef.current ??= new AudioContext()
      void audioCtxRef.current.resume()
    }
    sourceRef.current?.close()
    spatialSpokenRef.current = ''
    budgetSpokenRef.current = ''
    discourseRef.current = ''
    setErrorMsg('')
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
    setVarsityCall(null)
    setProof(null)
    setVerification(null)
    setParallax(null)
    setCausal(null)
    setCriticalQuestions(null)
    setCompleteness(null)
    setProvenance(null)
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
    // Recover from any stream/parse failure: a SyntaxError thrown inside an SSE listener does NOT
    // fire onerror, so without this a malformed frame would leave the Explain button locked forever.
    // Use the `language` param, not the closure `lang` state, so a switch-then-stream (selectLang
    // calls setLang then explainTheCall(l) synchronously) shows the error in the requested language.
    const recover = () => {
      setStreaming(false)
      source.close()
      setErrorMsg(UI[language].error)
    }
    const guard =
      (fn: (e: MessageEvent) => void) =>
      (event: Event) => {
        try {
          fn(event as MessageEvent)
        } catch {
          recover()
        }
      }
    source.addEventListener('stream_error', recover)
    source.addEventListener(
      'reviewing',
      guard((event) => {
        const data = JSON.parse(event.data) as {
          source: string
          detail: string
          minute: number | null
        }
        setReviewing({ ...data, minute: typeof data.minute === 'number' ? data.minute : null })
      }),
    )
    for (const name of STAGES) {
      source.addEventListener(name, guard((event) => {
        const data = JSON.parse(event.data) as Stage
        // arrival time of this stage since the request started, for the observability waterfall
        data._arrivedMs = Math.round(performance.now() - startRef.current)
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
        if (name === 'proof') {
          setProof({
            steps:
              (data.steps as {
                key: string
                claim: string
                status: string
                law: string
                role: string
              }[]) ?? [],
            consistent: Boolean(data.consistent),
            conclusion: String(data.conclusion ?? ''),
          })
        }
        if (name === 'parallax') {
          setParallax({
            distanceM: Number(data.camera_distance_m ?? 0),
            angleDeg: Number(data.residual_angle_deg ?? 0),
            shiftCm: Number(data.apparent_shift_cm ?? 0),
            note: String(data.note ?? ''),
          })
        }
        if (name === 'causal') {
          setCausal({
            fact: String(data.fact ?? ''),
            foil: String(data.foil ?? ''),
            narration: String(data.narration ?? ''),
          })
        }
        if (name === 'critical_questions') {
          setCriticalQuestions({
            scheme: String(data.scheme ?? ''),
            questions: (data.questions as { q: string; a: string }[]) ?? [],
          })
        }
        if (name === 'completeness') {
          setCompleteness({
            score: Number(data.score ?? 0),
            complete: Boolean(data.complete),
            disclosures:
              (data.disclosures as {
                name: string
                disclosed: boolean
                detail: string
              }[]) ?? [],
          })
        }
        if (name === 'provenance') {
          setProvenance({
            hash: String(data.manifest_hash ?? ''),
            grounded: Boolean(data.grounded),
            proofConsistent: Boolean(data.proof_consistent),
            verified: Boolean(data.verified),
            links:
              (data.links as { claim: string; law_clause: string; source: string }[]) ?? [],
          })
        }
        if (name === 'verification') {
          setVerification({
            verified: Boolean(data.verified),
            hardPassed: Number(data.hard_passed ?? 0),
            hardTotal: Number(data.hard_total ?? 0),
            advisoryPassed: Number(data.advisory_passed ?? 0),
            advisoryTotal: Number(data.advisory_total ?? 0),
            critics:
              (data.critics as {
                name: string
                passed: boolean
                detail: string
                kind: string
              }[]) ?? [],
          })
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
        if (name === 'uncertainty_budget') {
          budgetSpokenRef.current = String(data.spoken ?? '')
        }
        if (name === 'geometry_descriptors') {
          const z = data.lateral_zone as { phrase?: string } | undefined
          spatialSpokenRef.current = String(z?.phrase ?? '')
        }
        if (name === 'discourse') {
          discourseRef.current = String(data.connective ?? '')
        }
        if (name === 'verdict') {
          const v = data as unknown as VerdictData
          const text = String(v.text ?? '')
          setExplanation(text)
          const isDecision = Boolean(v.decision_type)
          const spoken = isDecision
            ? text
            : announceText(verbosity, {
                text,
                isOffside: Boolean(v.is_offside),
                marginM: Number(v.margin_meters ?? 0),
                confidence: v.confidence ? String(v.confidence) : undefined,
              })
          const lead =
            !isDecision && discourseRef.current
              ? `${discourseRef.current.charAt(0).toUpperCase()}${discourseRef.current.slice(1)}. `
              : ''
          const spatial =
            !isDecision && verbosity !== 'minimal' && spatialSpokenRef.current
              ? ` The incident was ${spatialSpokenRef.current}.`
              : ''
          const tail = !isDecision && budgetSpokenRef.current ? ` ${budgetSpokenRef.current}` : ''
          announce(`${lead}${spoken}${spatial}${tail}`)
          if (v.law_text) setLawText(String(v.law_text))
          if (!isDecision) {
            triggerHaptic({
              is_offside: Boolean(v.is_offside),
              margin_meters: Number(v.margin_meters ?? 0),
            })
            setVarsityCall({
              marginM: Number(v.margin_meters ?? 0),
              sigmaM: Number(v.sigma_meters ?? 0),
              band: String(v.confidence ?? ''),
              p: Number(v.p_verdict ?? 0),
              likelihood: String(v.likelihood ?? ''),
              note: String(v.uncertainty_note ?? ''),
              counterfactualM: Number(v.counterfactual_meters ?? 0),
              isOffside: Boolean(v.is_offside),
            })
          }
          setLatencyMs(performance.now() - startRef.current)
          setStreaming(false)
          source.close()
        }
      }))
    }
    // The verdict handler closes the source on success, so onerror means a genuine stream failure
    // (or a cold-start drop): the role=alert banner surfaces it visibly + to assistive tech.
    source.onerror = recover
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
    setErrorMsg('')
    setReviewing(null) // clear a stale 'VAR is reviewing' card from a prior live run
    setMoment(null)
    setDecision(null)
    setSignalCard(null)
    setVarsityCall(null)
    setProof(null)
    setVerification(null)
    setParallax(null)
    setCausal(null)
    setCriticalQuestions(null)
    setCompleteness(null)
    setProvenance(null)
    setLatencyMs(null)
    startRef.current = performance.now()
    setStreaming(true)
    if (soundOn) {
      audioCtxRef.current ??= new AudioContext()
      void audioCtxRef.current.resume()
    }
    try {
      const { generateOffline, setOfflineTier } = await import('./offline')
      setOfflineTier(highAccuracyOffline ? 'granite-1b' : 'nano')
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
    } catch {
      // The on-device model (WebGPU chunk fetch, model load) can fail; never leave the blind
      // fan with a silently-hung button. Surface the error visibly + to assistive tech.
      setOfflineStatus('')
      setErrorMsg(UI[lang].error)
    } finally {
      setStreaming(false)
    }
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
    setVarsityCall(null)
    setProof(null)
    setVerification(null)
    setParallax(null)
    setCausal(null)
    setCriticalQuestions(null)
    setCompleteness(null)
    setProvenance(null)
    setAskedQuestion(asked)
    setErrorMsg('')
    startRef.current = performance.now()
    setStreaming(true)
    const url = `${BACKEND}/stream/ask?q=${encodeURIComponent(asked)}&language=${encodeURIComponent(lang)}`
    const source = new EventSource(url)
    sourceRef.current = source
    const recover = () => {
      setStreaming(false)
      source.close()
      setErrorMsg(UI[lang].error)
    }
    const guard =
      (fn: (e: MessageEvent) => void) =>
      (event: Event) => {
        try {
          fn(event as MessageEvent)
        } catch {
          recover()
        }
      }
    source.addEventListener('stream_error', recover)
    for (const name of STAGES) {
      source.addEventListener(name, guard((event) => {
        const data = JSON.parse(event.data) as Stage
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
      }))
    }
    source.onerror = recover
  }

  // Optional voice input for the oracle, two tiers. Tier 1 (premium): on-device ASR (Whisper in
  // Transformers.js + WebGPU) - the audio is transcribed in the browser and never leaves the
  // device. Tier 2 (floor): the Web Speech API (zero download; on-device only in recent Chrome,
  // otherwise the browser's speech service). Either way the transcript feeds the same oracle, and
  // a graceful no-op where neither is available; the text input is always there.
  async function startVoiceInput() {
    setVoiceStatus('')
    if (await onDeviceAsrAvailable()) {
      try {
        const { transcript } = listen(UI[lang].bcp47, { onStatus: setVoiceStatus })
        const said = await transcript
        setVoiceStatus('')
        if (said) {
          setQuestion(said)
          askQuestion(said)
        }
        return
      } catch {
        setVoiceStatus('') // fall through to the Web Speech floor
      }
    }
    const w = window as unknown as {
      webkitSpeechRecognition?: new () => SpeechRecognitionLike
      SpeechRecognition?: new () => SpeechRecognitionLike
    }
    const Rec = w.SpeechRecognition ?? w.webkitSpeechRecognition
    if (!Rec) {
      setVoiceStatus('Voice input is not available in this browser; use the text box.')
      return
    }
    const rec = new Rec()
    rec.lang = UI[lang].bcp47
    rec.interimResults = false
    rec.maxAlternatives = 1
    setVoiceStatus('Listening...')
    rec.onresult = (e: SpeechRecognitionEventLike) => {
      const said = e.results?.[0]?.[0]?.transcript ?? ''
      setVoiceStatus('')
      if (said) {
        setQuestion(said)
        askQuestion(said)
      }
    }
    rec.start()
  }

  async function shareCurrent() {
    if (!explanation) return
    setShareStatus('Preparing clip...')
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
  // A ref to the latest key actions + state, so the single keydown listener (mounted once) always
  // calls the current handlers, never a stale closure (e.g. Explain after the user changed audio or
  // verbosity settings), without re-binding the listener on every render.
  const keyActions = useRef({
    explainTheCall,
    explainOffline,
    shareCurrent,
    cycleVerbosity,
    selectLang,
    lang,
    streaming,
    explanation,
    rate: audioPrefs.rate,
  })
  keyActions.current = {
    explainTheCall,
    explainOffline,
    shareCurrent,
    cycleVerbosity,
    selectLang,
    lang,
    streaming,
    explanation,
    rate: audioPrefs.rate,
  }
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.ctrlKey || e.metaKey || e.altKey) return
      const tag = (e.target as HTMLElement | null)?.tagName ?? ''
      if (/^(INPUT|TEXTAREA|SELECT)$/.test(tag)) return
      const a = keyActions.current
      const langs = LANGS
      const k = e.key.toLowerCase()
      if (k === 'e') {
        if (!a.streaming) a.explainTheCall(a.lang)
      } else if (k === 'o') {
        if (!a.streaming) void a.explainOffline()
      } else if (k === 'r') {
        if (a.explanation && !a.streaming)
          void readAloud(a.explanation, { lang: UI[a.lang].bcp47, rate: a.rate })
      } else if (k === 'c') {
        if (a.explanation && !a.streaming) void a.shareCurrent()
      } else if (k === 's') {
        setSoundOn((s) => !s)
      } else if (k === 'b') {
        setBuildUp((b) => !b)
      } else if (k === 'd') {
        setDetail((d) => !d)
      } else if (k === 'l') {
        setLive((v) => !v)
      } else if (k === 'v') {
        a.cycleVerbosity()
      } else if (e.key === '?') {
        setShowHelp((h) => !h)
      } else if (k >= '1' && k <= '5') {
        a.selectLang(langs[Number(k) - 1])
      } else {
        return
      }
      e.preventDefault()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

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
    (('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) ||
      (!!navigator.mediaDevices?.getUserMedia && 'gpu' in navigator))
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
          {LANGS.map((l) => (
            <button key={l} type="button" aria-pressed={lang === l} aria-label={l} onClick={() => selectLang(l)} className={segBtn(lang === l)}>
              {UI[l].code}
            </button>
          ))}
        </div>
        {(explanation || liveMessage) && (
          <button
            type="button"
            lang={t.bcp47}
            aria-label={t.reannounce}
            title={t.reannounce}
            onClick={reAnnounce}
            className="rounded-full bg-slate-800/60 px-4 py-1.5 text-sm font-medium text-slate-300 transition-colors hover:text-white"
          >
            🔊 {t.code}
          </button>
        )}
        <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-slate-900/40 px-2 py-1 ring-1 ring-slate-700/40">
        <button
          type="button"
          aria-pressed={soundOn}
          aria-label="Spatial audio cue"
          aria-keyshortcuts="S"
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
          aria-keyshortcuts="B"
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
          aria-label="Decision detail"
          aria-keyshortcuts="D"
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
          aria-keyshortcuts="L"
          onClick={() => setLive((v) => !v)}
          className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
            live ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800/60 text-slate-300 hover:text-white'
          }`}
        >
          {live ? 'Live feed' : 'Replay'}
        </button>
        </div>
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
            {moment.competition ?? 'FIFA World Cup 2022'} · <MixedScriptText text={moment.matchName} />
            {typeof moment.minute === 'number' ? ` · ${moment.minute}'` : ''}
          </p>
        )}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-3">
        <button
          id="explain-cta"
          onClick={() => explainTheCall(lang)}
          disabled={streaming}
          aria-keyshortcuts="E"
          className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400 disabled:opacity-60"
        >
          {streaming ? t.explaining : t.explain}
        </button>
        <button
          onClick={() => void explainOffline()}
          disabled={streaming}
          aria-keyshortcuts="O"
          className="rounded-full border border-emerald-500/60 px-6 py-3 font-medium text-emerald-300 transition-colors hover:bg-emerald-500/10 disabled:opacity-60"
        >
          Offline mode (on-device)
        </button>
        <label className="flex items-center gap-2 text-xs text-slate-400">
          <input
            type="checkbox"
            checked={highAccuracyOffline}
            onChange={(e) => setHighAccuracyOffline(e.target.checked)}
            disabled={streaming}
            className="accent-emerald-500"
          />
          High-accuracy on-device model (Granite 4.0 1B, ~1.5 GB download)
        </label>
        <button
          onClick={() => geo && playSpatialScan(geo)}
          disabled={streaming || !geo}
          aria-label="Play a spatial-audio scan of the freeze-frame over headphones"
          className="rounded-full border border-sky-500/60 px-6 py-3 font-medium text-sky-300 transition-colors hover:bg-sky-500/10 disabled:opacity-40"
        >
          Spatial scan (headphones)
        </button>
        <button
          onClick={() => void readAloud(explanation, { lang: t.bcp47, rate: audioPrefs.rate })}
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

      {errorMsg && (
        <p role="alert" className="max-w-2xl text-sm font-medium text-red-400">
          {errorMsg}
        </p>
      )}

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
          className="min-w-0 flex-1 rounded-full bg-slate-800/60 px-5 py-3 text-sm text-slate-100 placeholder:text-slate-400 ring-1 ring-slate-700/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/60"
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

      {voiceStatus && (
        <p role="status" aria-live="polite" className="max-w-2xl text-sm text-emerald-200">
          {voiceStatus}
        </p>
      )}

      {askedQuestion && (
        <p className="max-w-2xl text-sm text-slate-400">
          You asked: <span className="text-slate-200">{askedQuestion}</span>
        </p>
      )}

      {/* Spearcon rule shortcuts: fast time-compressed speech of each Law-11 sub-clause, an
          audible glossary a power screen-reader user can learn by ear (Walker et al. 2013). */}
      <section
        aria-label="Law 11 rule shortcuts, spoken fast"
        className="w-full max-w-2xl rounded-xl bg-slate-900/40 p-3 text-left ring-1 ring-slate-700/40"
      >
        <p className="font-mono text-xs uppercase tracking-wider text-slate-400">
          Rule shortcuts · spearcons
        </p>
        <div className="mt-2 flex flex-wrap gap-2">
          {LAW11_SPEARCONS.map((fragment) => (
            <button
              key={fragment}
              type="button"
              aria-label={`Play rule shortcut: ${fragment}`}
              onClick={() => void playPitchCorrectedSpearcon(fragment, { lang: UI[lang].bcp47 })}
              className="rounded-full border border-slate-600/60 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:bg-slate-600/20"
            >
              {fragment}
            </button>
          ))}
        </div>
      </section>

      {reviewing && (
        <div
          role="status"
          aria-live="polite"
          className="glass w-full max-w-md rounded-xl p-3 text-left"
        >
          <p className="text-sm font-medium text-emerald-200">
            {typeof reviewing.minute === 'number' ? `Minute ${reviewing.minute}: ` : ''}VAR is
            reviewing. {reviewing.detail}.
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
          {offlineSource === 'granite-1b-webgpu'
            ? 'Explained on-device by Granite 4.0 1B (WebGPU), no network.'
            : offlineSource === 'granite-nano-webgpu'
              ? 'Explained on-device by Granite Nano (WebGPU), no network.'
              : 'Explained on-device (deterministic, no network).'}
          {offlineRetrieval === 'orama-bm25' ? ' Law retrieved on-device (Orama BM25).' : ''}
          {offlineStatus ? ` ${offlineStatus}` : ''}
        </p>
      )}

      {/* Pre-registered aria-live region: the screen reader speaks the verdict in place,
          at the chosen verbosity, with a re-announce-safe trailing space. */}
      <div ref={liveRef} tabIndex={-1} aria-live="assertive" aria-atomic="true" role="status" lang={t.bcp47} className="sr-only">
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

      {proof && (
        <section
          aria-label="Law 11 rule proof"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Rule proof · Law 11 {proof.consistent ? '· consistent' : '· official trusted'}
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {proof.steps.map((s) => (
              <li key={s.key} className="flex items-start gap-2 text-slate-300">
                <span
                  aria-hidden="true"
                  className={
                    s.status === 'pass'
                      ? 'text-emerald-400'
                      : s.status === 'fail'
                        ? 'text-amber-400'
                        : 'text-slate-400'
                  }
                >
                  {s.status === 'pass' ? '✓' : s.status === 'fail' ? '✗' : '○'}
                </span>
                <span>
                  <span className="sr-only">
                    {s.status === 'pass' ? 'Met. ' : s.status === 'fail' ? 'Not met. ' : 'Not applicable. '}
                  </span>
                  {s.claim} <span className="font-mono text-xs text-slate-400">Law {s.law}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-sm font-medium text-emerald-200">{proof.conclusion}</p>
        </section>
      )}

      {parallax && (
        <section
          aria-label="Why broadcast offside can look wrong: camera parallax"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Why TV looks wrong · camera parallax
          </p>
          <p className="mt-1 text-sm text-slate-200">
            A ~{parallax.angleDeg}° residual camera angle, ~{parallax.distanceM} m from this
            incident, moves the apparent offside line by ~{parallax.shiftCm} cm.
          </p>
          <p className="mt-1 text-sm text-slate-400">{parallax.note}</p>
        </section>
      )}

      {causal && (
        <section
          aria-label={`Why ${causal.fact} rather than ${causal.foil}: the decisive cause`}
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Why {causal.fact} · rather than {causal.foil}
          </p>
          <p className="mt-1 text-sm text-slate-200">{causal.narration}</p>
        </section>
      )}

      {criticalQuestions && (
        <section
          aria-label="Critical questions a skeptic would ask, answered from the evidence"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Critical questions · {criticalQuestions.scheme}
          </p>
          <dl className="mt-2 space-y-2 text-sm">
            {criticalQuestions.questions.map((item) => (
              <div key={item.q}>
                <dt className="font-medium text-slate-200">{item.q}</dt>
                <dd className="text-slate-400">{item.a}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {varsityCall && (
        <section
          aria-label="VARSITY's Call: how clear-cut, with measurement uncertainty"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            VARSITY&apos;s Call · {varsityCall.band}
          </p>
          <p className="mt-1 text-sm text-slate-200">
            {Math.abs(varsityCall.marginM).toFixed(2)} m ± {varsityCall.sigmaM.toFixed(2)} m ·{' '}
            {varsityCall.likelihood} {varsityCall.isOffside ? 'offside' : 'onside'} (
            {Math.round(varsityCall.p * 100)}% on the geometry)
          </p>
          <p className="mt-1 text-sm text-slate-400">{varsityCall.note}</p>
          <p className="mt-1 text-sm text-slate-400">
            {varsityCall.isOffside
              ? `Onside if the attacker had been about ${varsityCall.counterfactualM} m further back.`
              : `Offside if the attacker had been about ${varsityCall.counterfactualM} m further forward.`}
          </p>
        </section>
      )}

      {verification && (
        <section
          aria-label="Faithfulness verification"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Verification · {verification.verified ? 'verified' : 'flagged'} ·{' '}
            {verification.hardPassed}/{verification.hardTotal} hard checks ·{' '}
            {verification.advisoryPassed}/{verification.advisoryTotal} advisory
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {verification.critics.map((critic) => (
              <li key={critic.name} className="flex items-start gap-2 text-slate-300">
                <span
                  aria-hidden="true"
                  className={critic.passed ? 'text-emerald-400' : 'text-amber-400'}
                >
                  {critic.passed ? '✓' : '✗'}
                </span>
                <span>
                  <span className="sr-only">{critic.passed ? 'Passed. ' : 'Flagged. '}</span>
                  {critic.detail}
                  {critic.kind === 'advisory' && (
                    <span className="ml-1 font-mono text-xs text-slate-400">· advisory</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {completeness && (
        <section
          aria-label="Argumentative completeness: does the explanation disclose enough for a blind fan"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Completeness · {completeness.complete ? 'complete' : 'partial'} ·{' '}
            {Math.round(completeness.score * 100)}% disclosed
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {completeness.disclosures.map((d) => (
              <li key={d.name} className="flex items-start gap-2 text-slate-300">
                <span
                  aria-hidden="true"
                  className={d.disclosed ? 'text-emerald-400' : 'text-amber-400'}
                >
                  {d.disclosed ? '✓' : '✗'}
                </span>
                <span>
                  <span className="sr-only">{d.disclosed ? 'Disclosed. ' : 'Missing. '}</span>
                  {d.detail}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {provenance && (
        <section
          aria-label="Chain of grounding: every claim traced to an IFAB clause and its source"
          className="w-full max-w-2xl rounded-xl bg-slate-900/60 p-4 text-left ring-1 ring-emerald-500/20"
        >
          <p className="font-mono text-xs uppercase tracking-wider text-emerald-300/80">
            Provenance · chain of grounding · {provenance.links.length} claims
          </p>
          <p className="mt-1 text-sm text-slate-400">
            Every claim traced to an IFAB clause and its evidence.{' '}
            {provenance.grounded ? 'Grounded' : 'Not grounded'} ·{' '}
            {provenance.proofConsistent ? 'proof-consistent' : 'proof conflict'} ·{' '}
            {provenance.verified ? 'verified' : 'flagged'}.
          </p>
          <ul className="mt-2 space-y-1 text-sm">
            {provenance.links.map((link, i) => (
              <li key={i} className="flex items-start gap-2 text-slate-300">
                <span aria-hidden="true" className="text-emerald-400">
                  ▸
                </span>
                <span>
                  {link.claim}{' '}
                  <span className="font-mono text-xs text-emerald-300/80">{link.law_clause}</span>{' '}
                  <span className="text-xs text-slate-400">· {link.source}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-2 font-mono text-xs text-slate-400" aria-label="Manifest hash">
            <span className="sr-only">Tamper-evident manifest hash: </span>
            {provenance.hash}
          </p>
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

      {streaming && !geo && (
        // Sighted-only placeholder for the ~1-2s before the first stage streams in, so the canvas
        // area is not blank dead air. aria-hidden + no aria-live: the blind fan's announcements come
        // from the separate assertive region, never from here.
        <div aria-hidden="true" className="w-full max-w-2xl text-center">
          <div
            className={`h-48 w-full rounded-2xl bg-slate-800/40 ring-1 ring-slate-700/40 ${
              reducedMotion ? '' : 'animate-pulse'
            }`}
          />
          <p className="mt-2 text-sm text-slate-400">{t.explaining}</p>
        </div>
      )}

      {geo && (
        <figure aria-hidden="true" className="w-full max-w-2xl">
          {reducedMotion ? (
            <OffsidePitch geo={geo} />
          ) : (
            <LazyBoundary fallback={<OffsidePitch geo={geo} />}>
              <Suspense fallback={<OffsidePitch geo={geo} />}>
                <OffsidePitch3D geo={geo} />
              </Suspense>
            </LazyBoundary>
          )}
          <figcaption className="mt-2 text-sm text-slate-400" lang={t.bcp47}>
            {t.caption(geo.margin_meters.toFixed(2), geo.is_offside)}
          </figcaption>
          <div className="mt-3 flex justify-center">
            <VerdictViz
              getAnalyser={() => (audioCtxRef.current ? vizAnalyser(audioCtxRef.current) : null)}
              active={audioActive}
            />
          </div>
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
          className="inline-flex min-h-6 items-center text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          Keyboard shortcuts (press ?)
        </button>
        <button
          type="button"
          aria-pressed={showDiag}
          onClick={() => setShowDiag((d) => !d)}
          className="inline-flex min-h-6 items-center text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          {showDiag ? 'Hide diagnostics' : 'On-device diagnostics'}
        </button>
        <button
          type="button"
          aria-pressed={showTranscript}
          onClick={() => setShowTranscript((s) => !s)}
          className="inline-flex min-h-6 items-center text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          {showTranscript ? 'Hide transcript' : 'Screen-reader transcript'}
        </button>
        <button
          type="button"
          aria-pressed={showTiming}
          onClick={() => setShowTiming((s) => !s)}
          className="inline-flex min-h-6 items-center text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
        >
          {showTiming ? 'Hide timing' : 'Pipeline timing'}
        </button>
      </div>

      <section
        aria-label="Audio settings and sound tutorial"
        className="flex w-full max-w-2xl flex-wrap items-center justify-center gap-4 rounded-xl bg-slate-900/40 p-3 ring-1 ring-slate-700/40"
      >
        <p className="font-mono text-xs uppercase tracking-wider text-slate-400">Audio</p>
        <label className="flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={audioPrefs.preamble}
            onChange={(e) => updateAudioPrefs({ preamble: e.target.checked })}
          />
          Preamble cue
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-300">
          <input
            type="checkbox"
            checked={graniteSpeech}
            onChange={(e) => {
              const on = e.target.checked
              setGraniteSpeech(on)
              try {
                localStorage.setItem('varsity-granite-speech', on ? '1' : '0')
              } catch {
                /* storage unavailable */
              }
            }}
          />
          All-IBM voice (Granite Speech, experimental)
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-300">
          Volume
          <input
            type="range"
            min={0}
            max={1}
            step={0.1}
            value={audioPrefs.volume}
            aria-label="Sound volume"
            aria-valuetext={`${Math.round(audioPrefs.volume * 100)} percent`}
            onChange={(e) => updateAudioPrefs({ volume: Number(e.target.value) })}
          />
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-300">
          Read-aloud speed
          <input
            type="range"
            min={0.5}
            max={2}
            step={0.1}
            value={audioPrefs.rate}
            aria-label="Read-aloud speech speed"
            aria-valuetext={`${audioPrefs.rate.toFixed(1)} times speed`}
            onChange={(e) => updateAudioPrefs({ rate: Number(e.target.value) })}
          />
        </label>
        <label className="flex items-center gap-2 text-xs text-slate-300">
          Spatial
          <select
            value={audioPrefs.mode}
            aria-label="Spatial audio mode"
            onChange={(e) => updateAudioPrefs({ mode: e.target.value as SpatialMode })}
            className="rounded bg-slate-800/60 px-2 py-1 text-slate-100 ring-1 ring-slate-700/50"
          >
            <option value="hrtf">3D (headphones)</option>
            <option value="stereo">Stereo (speakers)</option>
            <option value="mono">Mono</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => void runTutorial()}
          disabled={streaming}
          className="rounded-full border border-emerald-500/50 px-4 py-1.5 text-xs text-emerald-200 transition-colors hover:bg-emerald-500/10 disabled:opacity-40"
        >
          Sound tutorial
        </button>
      </section>
      <KeyboardHelp open={showHelp} />
      {showDiag && <DiagnosticsPanel />}
      {showTiming && <PipelineWaterfall stages={stages} />}
      {showTranscript && (
        <section
          aria-label="Screen-reader transcript"
          className="mt-4 rounded-2xl bg-slate-900/60 p-5 text-left ring-1 ring-slate-700/50"
        >
          <h3 className="text-sm font-semibold text-emerald-300">Screen-reader transcript</h3>
          <p className="mt-1 text-xs text-slate-400">
            Exactly what a blind fan hears: every aria-live announcement, in order.
          </p>
          {transcript.length === 0 ? (
            <p className="mt-3 text-sm text-slate-400">
              Nothing announced yet. Press Explain, and the spoken verdict appears here.
            </p>
          ) : (
            <ol className="mt-3 space-y-2">
              {transcript.map((line, i) => (
                <li key={i} className="flex gap-3 text-sm text-slate-200">
                  <span aria-hidden="true" className="font-mono text-xs text-slate-400">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span lang={UI[lang].bcp47}>{line}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </div>
  )
}
