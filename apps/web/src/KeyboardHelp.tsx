export const SHORTCUTS: [string, string][] = [
  ['E', 'Explain the call'],
  ['O', 'Offline mode (on-device)'],
  ['R', 'Read aloud'],
  ['C', 'Share clip'],
  ['S', 'Toggle spatial sound'],
  ['D', 'Toggle detail / plain'],
  ['1-5', 'Language (EN / ES / FR / PT / DE)'],
  ['?', 'Toggle this shortcut list'],
]

// A keyboard-shortcut reference. The shortcuts make every core action operable from
// the keyboard alone (the buttons are already tab-focusable); this is the power layer.
export function KeyboardHelp({ open }: { open: boolean }) {
  if (!open) return null
  return (
    <section
      aria-label="Keyboard shortcuts"
      className="w-full max-w-md rounded-xl bg-slate-900/70 p-4 text-left ring-1 ring-slate-700/50"
    >
      <h3 className="text-sm font-semibold text-emerald-300">Keyboard shortcuts</h3>
      <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
        {SHORTCUTS.map(([key, desc]) => (
          <div key={key} className="contents">
            <dt>
              <kbd className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-xs text-emerald-200">
                {key}
              </kbd>
            </dt>
            <dd className="text-slate-300">{desc}</dd>
          </div>
        ))}
      </dl>
    </section>
  )
}
