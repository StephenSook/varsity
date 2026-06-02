import { useEffect, useRef, useState } from 'react'
import { BroadcastTicker } from './BroadcastTicker'
import { KeyboardHelp } from './KeyboardHelp'
import { OffsidePitch, type Geometry } from './OffsidePitch'
import { shareExplanation } from './share'
import { playOffsideChord } from './sonify'
import { StageScrubber } from './StageScrubber'
import { readAloud, synthesizeClip } from './tts'

// Backend SSE base. Override with VITE_BACKEND_URL for a deployed backend.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'

const STAGES = ['trigger', 'geometry', 'law', 'granite', 'guardian', 'verdict'] as const

type Stage = { stage: string; [key: string]: unknown }
type Lang = 'English' | 'Spanish' | 'French' | 'Portuguese' | 'German'

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
  const [lang, setLang] = useState<Lang>('English')
  const [soundOn, setSoundOn] = useState(true)
  const [offlineSource, setOfflineSource] = useState<string | null>(null)
  const [offlineRetrieval, setOfflineRetrieval] = useState<'orama-bm25' | 'bundled' | null>(null)
  const [offlineStatus, setOfflineStatus] = useState('')
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [showHelp, setShowHelp] = useState(false)
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
    setLatencyMs(null)
    setReviewing(null)
    startRef.current = performance.now()
    setStreaming(true)
    // Live mode hits /stream/live, which first emits the transitional "VAR is
    // reviewing" announcement (from Sportmonks / API-Football, or the replay buffer
    // when there is no live match), then the same explanation pipeline.
    const endpoint = live ? 'live' : 'canned'
    const url = `${BACKEND}/stream/${endpoint}?language=${encodeURIComponent(language)}`
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
          const text = String(data.text ?? '')
          setExplanation(text)
          announce(
            announceText(verbosity, {
              text,
              isOffside: Boolean(data.is_offside),
              marginM: Number(data.margin_meters ?? 0),
              confidence: data.confidence ? String(data.confidence) : undefined,
            }),
          )
          if (data.law_text) setLawText(String(data.law_text))
          triggerHaptic(data as unknown as Geometry)
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
    if (ctx) {
      void playOffsideChord(ctx, res.geo)
        .then((plan) => {
          const w = window as unknown as { __varsitySonification?: unknown }
          w.__varsitySonification = plan
        })
        .catch(() => {})
    }
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

  function selectLang(l: Lang) {
    setLang(l)
    if (explanation || streaming || geo) {
      explainTheCall(l)
    }
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
  }, [lang, streaming, explanation, live])

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

      <BroadcastTicker latencyMs={latencyMs} />

      <StageScrubber stages={stages} describe={describe} />

      <button
        type="button"
        aria-pressed={showHelp}
        onClick={() => setShowHelp((h) => !h)}
        className="text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
      >
        Keyboard shortcuts (press ?)
      </button>
      <KeyboardHelp open={showHelp} />
    </div>
  )
}
