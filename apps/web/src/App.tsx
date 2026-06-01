import { useRef, useState } from 'react'

// The screen-reader-native core seed. Phase 1 replaces the canned text with the
// Granite + Law-11 RAG pipeline output delivered over SSE. The aria-live region
// stays mounted at all times and is mutated in place, never destroyed/recreated.
export default function App() {
  const [explanation, setExplanation] = useState('')
  const liveRef = useRef<HTMLDivElement>(null)

  function announce() {
    setExplanation(
      'Play stopped for offside review. Under Law 11, an attacker is offside if any ' +
        'part of the body they can score with is ahead of both the ball and the ' +
        'second-to-last defender when the ball is played.',
    )
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-8 px-6 text-center">
      <h1 className="text-4xl sm:text-6xl font-semibold tracking-tight">VARSITY</h1>
      <p className="max-w-xl text-balance text-slate-300">
        Real-time, screen-reader-native explanations of VAR and offside decisions.
      </p>
      <button
        onClick={announce}
        className="rounded-full bg-emerald-500 px-6 py-3 font-medium text-slate-950 transition-colors hover:bg-emerald-400"
      >
        Explain the call
      </button>

      <div
        ref={liveRef}
        aria-live="assertive"
        aria-atomic="true"
        role="status"
        className="sr-only"
      >
        {explanation}
      </div>

      {explanation && (
        <p aria-hidden="true" className="max-w-2xl text-lg text-emerald-200">
          {explanation}
        </p>
      )}
    </main>
  )
}
