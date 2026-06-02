import { Suspense, lazy, useEffect, useRef } from 'react'
import gsap from 'gsap'
import { Demo } from './Demo'
import { OnlineBadge } from './OnlineBadge'
import { Reveal } from './Reveal'
import { useLenis } from './useLenis'
import { usePrefersReducedMotion } from './useReducedMotion'

// The 3D hero is heavy and purely decorative, so it is code-split and only loaded
// when motion is allowed (keeps the core fast and accessible).
const Hero3D = lazy(() => import('./Hero3D'))

const serif = { fontFamily: "'Instrument Serif', Georgia, serif" } as const

const PIPELINE = [
  { k: 'Trigger', d: 'A VAR review fires (live feed or a StatsBomb 360 frame).' },
  { k: 'Geometry', d: 'The real offside margin in meters, from the freeze-frame.' },
  { k: 'IFAB Law', d: 'The governing Law of the Game, retrieved from the corpus.' },
  { k: 'IBM Granite', d: 'A plain explanation, coordinated through Context Forge.' },
  { k: 'Guardian', d: 'Granite Guardian checks it stays grounded in the Law.' },
  { k: 'Screen reader', d: 'Spoken in your language through your own screen reader.' },
]

const CLAIMS: { t: string; w: string }[] = [
  { t: 'Offside geometry from StatsBomb 360', w: 'services/app/geometry.py' },
  { t: 'IFAB-Laws retrieval + IBM Granite reasoning', w: 'services/app/rag, services/app/llm' },
  { t: 'Granite Guardian groundedness safety', w: 'services/app/llm/guardian.py' },
  { t: 'Context Forge MCP + A2A federation', w: 'services/app/federation.py, docs/federation.md' },
  { t: 'On-device offline mode (Granite Nano, WebGPU)', w: 'apps/web/src/offline.ts' },
  { t: 'Spatial audio, haptics, EN/ES, read-aloud', w: 'apps/web/src/sonify.ts, tts.ts' },
]

function Section({
  id,
  label,
  children,
}: {
  id?: string
  label: string
  children: React.ReactNode
}) {
  return (
    <section
      id={id}
      aria-label={label}
      className="relative z-10 mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-6 py-24"
    >
      {children}
    </section>
  )
}

export default function App() {
  const reducedMotion = usePrefersReducedMotion()
  const heroRef = useRef<HTMLDivElement>(null)
  useLenis()

  useEffect(() => {
    if (reducedMotion || !heroRef.current) return
    const items = heroRef.current.querySelectorAll('[data-hero-item]')
    const anim = gsap.from(items, { y: 26, opacity: 0, duration: 0.8, ease: 'power3.out', stagger: 0.12 })
    return () => {
      anim.kill()
    }
  }, [reducedMotion])

  return (
    <div className="relative">
      <OnlineBadge />
      {/* HERO */}
      <section
        aria-label="Introduction"
        className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center"
      >
        {!reducedMotion && (
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-0">
            <Suspense fallback={null}>
              <Hero3D />
            </Suspense>
          </div>
        )}
        <div className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-b from-[#0a0f1c]/40 via-transparent to-[#0a0f1c]" />
        <div ref={heroRef} className="relative z-10 flex flex-col items-center gap-6">
          <p
            data-hero-item
            className="font-mono text-xs uppercase tracking-[0.34em] text-emerald-400"
          >
            IFAB-grounded · screen-reader-native
          </p>
          <h1 data-hero-item style={serif} className="text-6xl leading-none text-slate-50 sm:text-8xl">
            VARSITY
          </h1>
          <p data-hero-item className="max-w-xl text-balance text-lg text-slate-300 sm:text-2xl">
            Hear the why behind every VAR call.
          </p>
          <div data-hero-item className="mt-2 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#demo"
              className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400"
            >
              Hear it explain a call
            </a>
            <a
              href="#problem"
              className="rounded-full border border-slate-500/60 px-6 py-3 font-medium text-slate-200 transition-colors hover:bg-slate-500/10"
            >
              Why it matters
            </a>
          </div>
        </div>
        <a
          href="#problem"
          aria-label="Scroll to learn more"
          className="absolute bottom-8 z-10 font-mono text-xs uppercase tracking-widest text-slate-400 hover:text-emerald-300"
        >
          scroll
        </a>
      </section>

      {/* THE PROBLEM */}
      <Section id="problem" label="The problem">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">The problem</p>
          <h2 style={serif} className="mt-3 text-4xl text-slate-50 sm:text-6xl">
            The last to know
          </h2>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            When a VAR review stops the match, a blind fan is often the last person in the room to
            understand the call. The decision data exists. It just never reaches them in real time.
          </p>
        </Reveal>
        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {[
            {
              h: 'The moment',
              p: 'The stadium goes quiet. Everyone stares at the big screen. You wait for someone to explain what just happened.',
            },
            {
              h: 'What fans told us',
              p: 'A blind supporter who follows the A-League told us the TV commentary leaves him with no idea what is happening on the pitch.',
            },
            {
              h: 'The gap',
              p: 'Audio description is improving, but even great commentary rarely gives the rule-grounded reason behind a contested call.',
            },
          ].map((c) => (
            <Reveal key={c.h} className="glass rounded-2xl p-6 text-left">
              <h3 className="text-sm font-semibold text-emerald-300">{c.h}</h3>
              <p className="mt-2 text-slate-300">{c.p}</p>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* THE DEMO */}
      <Section id="demo" label="Live demo">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">Live</p>
          <h2 style={serif} className="mt-3 text-center text-4xl text-slate-50 sm:text-6xl">
            Hear the call
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-center text-lg text-slate-300">
            A real 2022 World Cup offside, explained end to end. Press play and listen, or cut the
            network and run it on your own device.
          </p>
        </Reveal>
        <div className="mt-12">
          <Demo />
        </div>
      </Section>

      {/* THE PIPELINE */}
      <Section id="pipeline" label="How it works">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">Under the hood</p>
          <h2 style={serif} className="mt-3 text-4xl text-slate-50 sm:text-6xl">
            One event, fanned out
          </h2>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            Four backends coordinate through the IBM Context Forge gateway with Granite on top. One
            VAR event fans out across the services and returns a single, safe, rule-grounded answer.
            The live gateway recorded those tool calls at 100% success.
          </p>
        </Reveal>
        <ol className="mt-12 grid list-none gap-4 sm:grid-cols-3">
          {PIPELINE.map((s, i) => (
            <li key={s.k}>
              <Reveal className="glass h-full rounded-2xl p-5 text-left">
                <div className="flex items-baseline gap-3">
                  <span className="font-mono text-sm text-emerald-400">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <h3 className="font-semibold text-slate-100">{s.k}</h3>
                </div>
                <p className="mt-2 text-sm text-slate-300">{s.d}</p>
              </Reveal>
            </li>
          ))}
        </ol>
      </Section>

      {/* VERIFY / JUDGES */}
      <Section id="judges" label="Verify every claim">
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">For judges</p>
          <h2 style={serif} className="mt-3 text-4xl text-slate-50 sm:text-6xl">
            Every claim is verifiable
          </h2>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">
            No theater. Each capability below runs in this repository and is pointed at the exact
            file that proves it. Built on IBM Granite, Granite Guardian, Context Forge, and Docling.
          </p>
        </Reveal>
        <ul className="mt-12 grid list-none gap-4 sm:grid-cols-2">
          {CLAIMS.map((c) => (
            <li key={c.t}>
              <Reveal className="glass flex h-full items-start gap-3 rounded-2xl p-5 text-left">
                <span aria-hidden="true" className="mt-1 text-emerald-400">
                  ✓
                </span>
                <div>
                  <p className="font-medium text-slate-100">{c.t}</p>
                  <p className="mt-1 font-mono text-xs text-slate-400">{c.w}</p>
                </div>
              </Reveal>
            </li>
          ))}
        </ul>
        <Reveal className="mt-10">
          <a
            href="https://github.com/StephenSook/varsity"
            className="inline-block rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400"
          >
            Read the code on GitHub
          </a>
        </Reveal>
      </Section>

      {/* CLOSE */}
      <footer className="relative z-10 mx-auto w-full max-w-5xl px-6 py-20 text-center">
        <Reveal>
          <h2 style={serif} className="text-3xl text-slate-100 sm:text-4xl">
            For the fan who needs it most.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-400">
            VARSITY turns officials-only decision data into the first rule-grounded, accessible why.
            It complements the commentary you love, it does not replace it.
          </p>
          <p className="mt-8 font-mono text-xs uppercase tracking-[0.3em] text-slate-400">
            IBM Granite · Granite Guardian · Context Forge · World Cup 2026
          </p>
        </Reveal>
      </footer>
    </div>
  )
}
