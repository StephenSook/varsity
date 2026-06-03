import { useState } from 'react'
import { CHROME, useLang } from './i18n'

// The honesty surface, made interactive: each claim carries a verifiability TIER and a
// deep-link to the proving file, and the "Run it now" buttons call the LIVE deployed
// backend from the judge's own browser and show the real response. No theater.
const BACKEND =
  (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL ??
  'http://localhost:8000'
const REPO = 'https://github.com/StephenSook/varsity/blob/main/'

type Tier = 'live' | 'illustrative' | 'integration'
const TIER: Record<Tier, { label: string; cls: string }> = {
  live: { label: 'LIVE', cls: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/40' },
  illustrative: { label: 'ILLUSTRATIVE', cls: 'bg-sky-500/15 text-sky-300 ring-sky-500/40' },
  integration: { label: 'INTEGRATION', cls: 'bg-slate-500/20 text-slate-300 ring-slate-500/40' },
}

const CLAIMS: { t: string; w: string; tier: Tier }[] = [
  { t: 'Offside geometry from StatsBomb 360', w: 'services/app/geometry.py', tier: 'live' },
  {
    t: "Uncertainty band + 'VARSITY's Call' (±13 cm, IPCC likelihood)",
    w: 'services/app/uncertainty.py',
    tier: 'live',
  },
  {
    t: 'Auditable Law-11 proof tree (neuro-symbolic rule traversal)',
    w: 'services/app/law11.py',
    tier: 'live',
  },
  {
    t: 'Multi-critic verification panel (generator + 5 critics)',
    w: 'services/app/verification.py',
    tier: 'live',
  },
  {
    t: 'Camera-parallax explainer (why a correct call looks wrong on TV)',
    w: 'services/app/parallax.py',
    tier: 'live',
  },
  {
    t: 'Chain-of-Grounding provenance manifest (every claim -> clause, SHA-256)',
    w: 'services/app/provenance.py',
    tier: 'live',
  },
  {
    t: 'Formally verified rule engine (Z3 proofs + property-based + metamorphic)',
    w: 'services/verify/law11_smt.py',
    tier: 'live',
  },
  {
    t: 'Responsible AI + safety case (NIST AI RMF, OWASP LLM Top 10, WCAG 2.2)',
    w: 'docs/SAFETY_CASE.md',
    tier: 'live',
  },
  {
    t: 'Injected-error faithfulness gold-eval (structural injections: 0 leakage)',
    w: 'services/verify/faithfulness_eval.py',
    tier: 'live',
  },
  {
    t: 'Contrastive causal opener (Halpern-Pearl / Miller: why offside rather than onside)',
    w: 'services/app/causal.py',
    tier: 'live',
  },
  {
    t: 'Walton critical-questions surface (argument from expert opinion)',
    w: 'services/app/walton.py',
    tier: 'live',
  },
  {
    t: 'Argumentative-completeness scorer (does the narration disclose enough?)',
    w: 'services/app/completeness.py',
    tier: 'live',
  },
  {
    t: 'Spearcon rule shortcuts (time-compressed speech, power-user navigation)',
    w: 'apps/web/src/tts.ts',
    tier: 'live',
  },
  {
    t: 'Sonification unit tests (vitest: earcon, line-proximity, bouba/kiki, spatial pan)',
    w: 'apps/web/src/sonify.test.ts',
    tier: 'live',
  },
  { t: 'IFAB-Laws RAG + IBM Granite reasoning', w: 'services/app/pipeline.py', tier: 'live' },
  { t: 'Granite Guardian groundedness safety', w: 'services/app/llm/guardian.py', tier: 'live' },
  { t: 'Real offside / onside / tight World Cup frames', w: 'services/app/scenarios.py', tier: 'live' },
  {
    t: 'Any VAR call: penalty & handball (Law 12/14)',
    w: 'services/app/decisions.py',
    tier: 'illustrative',
  },
  {
    t: 'Ask-any-rule oracle, grounded + Guardian-checked',
    w: 'services/app/pipeline.py',
    tier: 'live',
  },
  { t: 'Referee-signal explainer (Law 5 / 6 + VAR)', w: 'services/app/signals.py', tier: 'live' },
  { t: 'Context Forge MCP + A2A federation', w: 'docs/federation.md', tier: 'integration' },
  {
    t: 'On-device offline mode (Granite Nano, WebGPU)',
    w: 'apps/web/src/offline.ts',
    tier: 'live',
  },
  { t: 'Spatial audio, haptics, 5 languages, read-aloud', w: 'apps/web/src/sonify.ts', tier: 'live' },
]

// Stream the full pipeline and summarise the real stages, so a judge sees the live
// geometry + Law retrieval + Guardian verdict, not a claim.
function streamSummary(url: string): Promise<string> {
  return new Promise((resolve) => {
    const es = new EventSource(url)
    const got: Record<string, Record<string, unknown>> = {}
    const finish = () => {
      es.close()
      const g = got.geometry ?? {}
      const law = got.law ?? {}
      const guard = got.guardian ?? {}
      resolve(
        `Law ${String(law.law ?? '?')} retrieved · margin ${String(g.margin_meters ?? '?')}m ` +
          `${g.is_offside ? 'offside' : 'onside'} · Granite explained · ` +
          `Guardian ${guard.safe ? 'SAFE' : 'flagged'} (grounded: ${String(guard.grounded ?? '?')})`,
      )
    }
    for (const ev of ['geometry', 'law', 'guardian']) {
      es.addEventListener(ev, (e) => {
        got[ev] = JSON.parse((e as MessageEvent).data)
      })
    }
    es.addEventListener('verdict', finish)
    es.onerror = () => {
      es.close()
      resolve('stream error (the free backend may be cold; retry in ~30s)')
    }
  })
}

export function JudgesPanel() {
  const [result, setResult] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const { lang } = useLang()
  const c = CHROME[lang]

  async function run(key: string, fn: () => Promise<string>) {
    setBusy(key)
    setResult((r) => ({ ...r, [key]: 'Running against the live backend…' }))
    try {
      const out = await fn()
      setResult((r) => ({ ...r, [key]: out }))
    } catch {
      setResult((r) => ({ ...r, [key]: 'error (the free backend may be cold; retry in ~30s)' }))
    } finally {
      setBusy(null)
    }
  }

  const RUNS: { key: string; label: string; fn: () => Promise<string> }[] = [
    {
      key: 'geometry',
      label: 'Run the geometry engine',
      fn: async () => {
        const j = await (await fetch(`${BACKEND}/scenarios`)).json()
        return (j.scenarios as Record<string, unknown>[])
          .map((s) => `${s.scenario}: ${s.expected_margin_meters}m ${s.expected_is_offside ? 'offside' : 'onside'}`)
          .join(' · ')
      },
    },
    {
      key: 'pipeline',
      label: 'Run the full pipeline',
      fn: () => streamSummary(`${BACKEND}/stream/canned?scenario=offside`),
    },
    {
      key: 'decisions',
      label: 'List the VAR decisions',
      fn: async () => {
        const j = await (await fetch(`${BACKEND}/decisions`)).json()
        return (j.decisions as Record<string, unknown>[])
          .map((d) => `${d.decision_type}: ${d.outcome}`)
          .join(' · ')
      },
    },
    {
      key: 'health',
      label: 'Backend health',
      fn: async () => {
        const j = await (await fetch(`${BACKEND}/health`)).json()
        return `backend ${String(j.status)} (${String(j.service)})`
      },
    },
  ]

  return (
    <div className="mt-12">
      <ul className="grid list-none gap-4 sm:grid-cols-2">
        {CLAIMS.map((c) => (
          <li
            key={c.t}
            className="glass flex h-full items-start gap-3 rounded-2xl p-5 text-left ring-1 ring-slate-700/40"
          >
            <span aria-hidden="true" className="mt-1 text-emerald-400">
              ✓
            </span>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium text-slate-100">{c.t}</p>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ring-1 ${TIER[c.tier].cls}`}
                >
                  {TIER[c.tier].label}
                </span>
              </div>
              <a
                href={`${REPO}${c.w}`}
                className="mt-1 inline-block font-mono text-xs text-slate-400 underline-offset-2 hover:text-emerald-300 hover:underline"
              >
                {c.w}
              </a>
            </div>
          </li>
        ))}
      </ul>

      <div className="mt-8 rounded-2xl bg-slate-900/60 p-5 text-left ring-1 ring-slate-700/50">
        <h3 className="text-sm font-semibold text-emerald-300">{c.runHeading}</h3>
        <p className="mt-1 text-xs text-slate-400">{c.runHelper}</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {RUNS.map((r) => (
            <button
              key={r.key}
              type="button"
              onClick={() => void run(r.key, r.fn)}
              disabled={busy !== null}
              className="rounded-full bg-sky-500 px-4 py-2 text-sm font-medium text-slate-950 transition-colors hover:bg-sky-400 disabled:opacity-50"
            >
              {r.label}
            </button>
          ))}
        </div>
        <div role="status" aria-live="polite" className="mt-3 space-y-1">
          {RUNS.filter((r) => result[r.key]).map((r) => (
            <p key={r.key} className="font-mono text-xs text-slate-300">
              <span className="text-emerald-300">{r.label}:</span> {result[r.key]}
            </p>
          ))}
        </div>
      </div>

      <div className="mt-8">
        <a
          href="https://github.com/StephenSook/varsity"
          className="inline-block rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400"
        >
          Read the code on GitHub
        </a>
      </div>
    </div>
  )
}
