# Screen-reader language switching: the honest reality, and VARSITY's dual-path

VARSITY narrates in five languages (English, Spanish, French, Portuguese, German). For a blind
fan, the narration is the product, so it must actually be *spoken in the right voice* when they
switch language. The uncomfortable truth: **correct markup does not guarantee that.**

## The gap: WCAG conformance ≠ the screen reader switching voice

WCAG 2.2 SC 3.1.2 "Language of Parts" requires that the language of each passage be
**programmatically determinable** — the `lang` attribute is the sufficient technique. We meet it:
the `<html>` element's `lang` is kept in sync with the selected language (SC 3.1.1), and the
live-region announcement node carries its own `lang`. But the W3C Understanding document is explicit
that meeting 3.1.2 does **not** require the assistive technology to actually switch voice — gaps
there "are caused by limitations of user agents and assistive technologies [and] they don't fail
the requirements of this success criterion." Conformance is necessary, not sufficient.

## Assistive-technology compatibility matrix (verified 2026-06-03; honesty-marked)

Does the AT switch voice from the HTML `lang` attribute on **dynamically-updated / live-region**
content?

| Screen reader + browser | Honors `lang` on a live update? | Notes |
|---|---|---|
| **NVDA** + Firefox/Chrome/Edge (Windows) | **No** (on live updates) | The live-region update is not spoken in the node's `lang`. **NVDA #4396**, open since 2014-08-15: *"subsequently tabbing to that element produces the correct pronunciation."* The focus trick is the documented fix. |
| **VoiceOver** + Safari (iOS) | **Yes** | iOS VoiceOver auto-switches voice from `lang`. |
| **VoiceOver** + Safari (macOS) | **No** | macOS VoiceOver ignores `lang` and uses its own "Detect Languages" auto-detection — a genuine macOS-vs-iOS divergence. |
| **JAWS** + Chrome (Windows) | Static: yes; live region: **UNVERIFIED** | JAWS loads the phonetic engine from markup for static content; its behavior on dynamically-updated live regions is not confirmed by a primary source. |
| **Android TalkBack** | **UNVERIFIED** | No authoritative source confirms TalkBack honors HTML `lang` to auto-switch voice on dynamic web content. Test on-device before relying on it. |

Sources: [NVDA #4396](https://github.com/nvaccess/nvda/issues/4396) · [w3c/aria #1346](https://github.com/w3c/aria/issues/1346) ("precious little documentation" on `lang` + live regions; still open) · [Adrian Roselli, "On use of the lang attribute"](https://adrianroselli.com/2015/01/on-use-of-lang-attribute.html) · [W3C Understanding SC 3.1.2](https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html) · [AppleVis: VoiceOver language detection macOS vs iOS](https://www.applevis.com/forum/braille-ios-and-mac-os-x/voiceover-language-detection-macos-vs-ios).

## VARSITY's dual-path (so the switch is actually heard)

1. **Markup, done right (conformance floor).** `<html lang>` tracks the selected language (3.1.1); the
   live-region announcement node carries its own `lang` (3.1.2); the English IFAB Law text keeps its
   own `lang="en"`. Necessary, and forward-compatible as AT improves — but not sufficient today.
2. **The NVDA focus-trick, exposed as a feature.** A **"🔊 Re-announce"** button (`reAnnounce()` in
   `apps/web/src/Demo.tsx`) is localized into each language and, on activation, moves focus to the
   live-region node. Per NVDA #4396, focusing the node makes NVDA re-pronounce the current text in
   the node's `lang` — turning a 12-year-old bug into a one-tap fix. The node is `tabIndex={-1}` and
   `sr-only` so it is focusable without disturbing the visual layout.
3. **A bundled-TTS fallback (the only hard guarantee).** Because macOS VoiceOver language-detects and
   TalkBack support is unverified, the only mechanism that *guarantees* the chosen language is spoken
   is an app-bundled TTS. VARSITY already ships one: the Read-aloud path (`apps/web/src/tts.ts`, Web
   Speech with a BCP-47 voice, plus on-device Kokoro for English), ducked under the user's own screen
   reader. It is supplementary and never auto-plays.

## Honest scope

- This matrix reflects what is verifiable from primary sources as of 2026-06-03; JAWS-live-region and
  TalkBack behavior are marked **UNVERIFIED** rather than asserted.
- Per-run mixed-script handling is shipped (`apps/web/src/mixedScript.tsx`): a non-Latin team or
  player name (e.g. المغرب, 대한민국, Россия) is split by Unicode script and each non-Latin run is
  wrapped in its own element tagged `lang="und-<Script>"` (undetermined language, known script, the
  honest tag since one script serves several languages), so the screen reader switches pronunciation
  for that run. Latin content passes through unchanged. Automatic phonetic TRANSLITERATION (a Latin
  spelling) is deliberately omitted: a correct one needs a per-script ICU table we do not bundle, and
  a wrong transliteration would mislead.
- The bundled-TTS path is Web Speech for non-English (Kokoro is English-first), so non-English premium
  voice quality depends on the OS voices installed.
