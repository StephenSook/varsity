// Per-run mixed-script lang tagging for the screen reader.
//
// When a team or player name is in a non-Latin script (e.g. a World Cup side written as المغرب,
// 대한민국, or Россия), a screen reader set to the page language mispronounces it. Wrapping each
// non-Latin run in its own element with a BCP-47 `lang` lets the AT switch to the correct
// pronunciation for that run. We tag by the SCRIPT we can detect from Unicode, not by language
// (Arabic script is used by Arabic, Persian, Urdu, so the honest tag is `und-Arab`: undetermined
// language, Arabic script). A run we cannot map to a known script is tagged plain `und`.
//
// Automatic phonetic TRANSLITERATION (a Latin spelling of the name) is deliberately NOT included:
// a correct transliteration needs a per-script ICU table we do not bundle, and a wrong one would
// mislead. Latin-script content passes through unchanged (a no-op), so this is safe everywhere.

import type { ReactElement } from 'react'

const SCRIPT_SUBTAG: [RegExp, string][] = [
  [/\p{Script=Arabic}/u, 'Arab'],
  [/\p{Script=Cyrillic}/u, 'Cyrl'],
  [/\p{Script=Han}/u, 'Hani'],
  [/\p{Script=Hangul}/u, 'Hang'],
  [/\p{Script=Hiragana}/u, 'Jpan'],
  [/\p{Script=Katakana}/u, 'Jpan'],
  [/\p{Script=Greek}/u, 'Grek'],
  [/\p{Script=Hebrew}/u, 'Hebr'],
  [/\p{Script=Devanagari}/u, 'Deva'],
  [/\p{Script=Thai}/u, 'Thai'],
]

// null = a Latin letter or a neutral char (digit/space/punct), which stays the page language.
// otherwise the BCP-47 tag for the non-Latin run, e.g. `und-Arab`.
function langOfLetter(ch: string): string | null {
  if (!/\p{L}/u.test(ch)) return null // neutral: joins the current run
  if (/\p{Script=Latin}/u.test(ch)) return null // Latin: the page language
  for (const [re, tag] of SCRIPT_SUBTAG) if (re.test(ch)) return `und-${tag}`
  return 'und' // a non-Latin letter whose script we do not map
}

export interface ScriptRun {
  text: string
  lang: string | null // null = render in the page language; otherwise a BCP-47 tag
}

/** Split text into maximal runs by script. Neutral characters join the current run, so a name like
 *  "Al Nassr النصر" yields a Latin run then an `und-Arab` run. All-Latin text returns one run. */
export function segmentByScript(text: string): ScriptRun[] {
  const runs: ScriptRun[] = []
  let cur: string | null | undefined
  let buf = ''
  const flush = () => {
    if (buf) runs.push({ text: buf, lang: cur ?? null })
    buf = ''
  }
  for (const ch of text) {
    const isLetter = /\p{L}/u.test(ch)
    const lang = langOfLetter(ch)
    if (!isLetter) {
      // neutral: stay in the current run (start one in the page language if none yet)
      if (cur === undefined) cur = null
      buf += ch
      continue
    }
    if (lang !== cur) {
      flush()
      cur = lang
    }
    buf += ch
  }
  flush()
  return runs
}

/** Render text with each non-Latin script run wrapped in a `lang`-tagged span for the screen
 *  reader. All-Latin text renders as a plain string (no wrapper). */
export function MixedScriptText({ text }: { text: string }): ReactElement {
  const runs = segmentByScript(text)
  if (runs.length <= 1 && (runs[0]?.lang ?? null) === null) {
    return <>{text}</>
  }
  return (
    <>
      {runs.map((r, i) =>
        r.lang === null ? <span key={i}>{r.text}</span> : (
          <span key={i} lang={r.lang}>
            {r.text}
          </span>
        ),
      )}
    </>
  )
}
