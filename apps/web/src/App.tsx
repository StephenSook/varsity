import { Suspense, lazy, useEffect, useRef } from 'react'
import gsap from 'gsap'
import { Demo } from './Demo'
import { CHROME, useLang } from './i18n'
import { JudgesPanel } from './JudgesPanel'
import { LazyBoundary } from './LazyBoundary'
import { OnlineBadge } from './OnlineBadge'
import { Reveal } from './Reveal'
import { useLenis } from './useLenis'
import { usePrefersReducedMotion } from './useReducedMotion'
import { HeroBackdrop } from './HeroBackdrop'

// The 3D hero is heavy and purely decorative, so it is code-split and only loaded
// when motion is allowed (keeps the core fast and accessible).
const Hero3D = lazy(() => import('./Hero3D'))

const serif = { fontFamily: "'Instrument Serif', Georgia, serif" } as const

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
  const { lang } = useLang()
  const c = CHROME[lang]
  useLenis()

  // Warm the free-tier backend on page load so a judge's first Explain / ask / Run-it-now
  // does not hit a ~30s cold start.
  useEffect(() => {
    const backend = (import.meta.env as Record<string, string | undefined>).VITE_BACKEND_URL
    if (backend) void fetch(`${backend}/health`).catch(() => {})
  }, [])

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
      <a
        href="#demo"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-emerald-500 focus:px-4 focus:py-2 focus:font-semibold focus:text-slate-950"
      >
        {c.skipToContent}
      </a>
      <OnlineBadge />
      <main>
      {/* HERO */}
      <section
        aria-label={c.heroKicker}
        className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center"
      >
        {reducedMotion ? (
          <HeroBackdrop />
        ) : (
          <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-0">
            <LazyBoundary fallback={<HeroBackdrop />}>
              <Suspense fallback={<HeroBackdrop />}>
                <Hero3D />
              </Suspense>
            </LazyBoundary>
          </div>
        )}
        <div className="pointer-events-none absolute inset-0 z-0 bg-gradient-to-b from-[#0a0f1c]/40 via-transparent to-[#0a0f1c]" />
        <div ref={heroRef} className="relative z-10 flex flex-col items-center gap-6">
          <p data-hero-item className="font-mono text-xs uppercase tracking-[0.34em] text-emerald-400">
            {c.heroKicker}
          </p>
          <h1 data-hero-item style={serif} className="text-6xl leading-none text-slate-50 sm:text-8xl">
            VARSITY
          </h1>
          <p data-hero-item className="max-w-xl text-balance text-lg text-slate-300 sm:text-2xl">
            {c.tagline}
          </p>
          <div data-hero-item className="mt-2 flex flex-wrap items-center justify-center gap-3">
            <a
              href="#demo"
              onClick={() => {
                // The verb "Hear" must be deliverable, not just a scroll: after the smooth scroll
                // settles, move focus to the Explain control so one keypress actually plays the
                // call. preventScroll keeps it from fighting the in-flight scroll; never auto-click
                // (the audio gesture-gate stays with the user).
                window.setTimeout(
                  () => document.getElementById('explain-cta')?.focus({ preventScroll: true }),
                  700,
                )
              }}
              className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400"
            >
              {c.ctaHear}
            </a>
            <a
              href="#problem"
              className="rounded-full border border-slate-500/60 px-6 py-3 font-medium text-slate-200 transition-colors hover:bg-slate-500/10"
            >
              {c.ctaWhy}
            </a>
          </div>
        </div>
        <a
          href="#problem"
          aria-label={c.ctaWhy}
          className="absolute bottom-8 z-10 font-mono text-xs uppercase tracking-widest text-slate-400 hover:text-emerald-300"
        >
          {c.scroll}
        </a>
      </section>

      {/* THE PROBLEM */}
      <Section id="problem" label={c.problemEyebrow}>
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">{c.problemEyebrow}</p>
          <h2 style={serif} className="mt-3 text-4xl text-slate-50 sm:text-6xl">
            {c.problemH2}
          </h2>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">{c.problemIntro}</p>
        </Reveal>
        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {c.cards.map((card) => (
            <Reveal key={card.h} className="glass rounded-2xl p-6 text-left">
              <h3 className="text-sm font-semibold text-emerald-300">{card.h}</h3>
              <p className="mt-2 text-slate-300">{card.p}</p>
            </Reveal>
          ))}
        </div>
      </Section>

      {/* THE DEMO */}
      <Section id="demo" label={c.demoEyebrow}>
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">{c.demoEyebrow}</p>
          <h2 style={serif} className="mt-3 text-center text-4xl text-slate-50 sm:text-6xl">
            {c.demoH2}
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-center text-lg text-slate-300">{c.demoIntro}</p>
        </Reveal>
        <div className="mt-12">
          <Demo />
        </div>
      </Section>

      {/* THE PIPELINE */}
      <Section id="pipeline" label={c.pipelineEyebrow}>
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">{c.pipelineEyebrow}</p>
          <h2 style={serif} className="mt-3 text-4xl text-slate-50 sm:text-6xl">
            {c.pipelineH2}
          </h2>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">{c.pipelineIntro}</p>
        </Reveal>
        <ol className="mt-12 grid list-none gap-4 sm:grid-cols-3">
          {c.pipeline.map((s, i) => (
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
      <Section id="judges" label={c.judgesEyebrow}>
        <Reveal>
          <p className="font-mono text-xs uppercase tracking-[0.3em] text-emerald-400">{c.judgesEyebrow}</p>
          <h2 style={serif} className="mt-3 text-4xl text-slate-50 sm:text-6xl">
            {c.judgesH2}
          </h2>
          <p className="mt-5 max-w-2xl text-lg text-slate-300">{c.judgesIntro}</p>
        </Reveal>
        <JudgesPanel />
      </Section>

      </main>

      {/* CLOSE */}
      <footer className="relative z-10 mx-auto w-full max-w-5xl px-6 py-20 text-center">
        <Reveal>
          <h2 style={serif} className="text-3xl text-slate-100 sm:text-4xl">
            {c.footerH2}
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-400">{c.footerP}</p>
          <p className="mt-8 font-mono text-xs uppercase tracking-[0.3em] text-slate-400">
            IBM Granite · Granite Guardian · Context Forge · {c.footerWC}
          </p>
        </Reveal>
      </footer>
    </div>
  )
}
