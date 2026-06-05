// The spoken-string builder for the screen-reader verdict, extracted as a pure function so the
// exact words a blind fan hears are unit-tested (Demo.tsx only wires it to the aria-live region).
//
// Verbosity control fights announcement fatigue: a verdict every 30s in full prose exhausts a
// screen-reader listener. Minimal = headline only; Standard = the full explanation; Coach =
// explanation plus how clear-cut the call was. The full text always stays in the visible panel;
// this only gates what the live region speaks.

export type Verbosity = 'minimal' | 'standard' | 'coach'

export function announceText(
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
