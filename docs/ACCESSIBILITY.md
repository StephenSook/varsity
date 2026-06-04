# Accessibility

VARSITY is a screen-reader-native product: the spoken explanation is the primary
output, not an afterthought. Accessibility is enforced in CI, not just claimed.

## Conformance target

**WCAG 2.2 AA** (the current W3C Recommendation; 2.1 is superseded, 3.0 is still a
draft). The criteria the experience leans on most:

- **4.1.3 Status Messages**: the verdict is delivered through a pre-registered
  `aria-live` region that mutates in place, so it is announced without moving focus.
- **1.3.1 Info & Relationships**: a single `h1`, semantic sections, and real `<ol>`/
  `<li>` lists for the pipeline and verify panels.
- **2.1.1 Keyboard**: every action is reachable by keyboard, plus a one-keypress
  power mode and a keyboard-operable stage scrubber.
- **2.2.2 Pause, Stop, Hide**: the broadcast-delay ticker animation has a pause
  control; all decorative motion is gated behind `prefers-reduced-motion`.
- **1.4.3 Contrast**: AA contrast, enforced by axe-core in CI (zero serious/critical).
- **1.2.x Captions / audio description**: the demo video ships open + closed captions
  and an audio-description track (submission deliverable).

The three criteria **new in WCAG 2.2 AA** are addressed explicitly, not just claimed:

- **2.4.7 Focus Visible + 2.4.13 Focus Appearance**: a global `:focus-visible` ring (2px
  signal-green, 2px offset) on every interactive control, with a `forced-colors` variant
  using the system `Highlight` colour (`apps/web/src/index.css`).
- **2.4.11 Focus Not Obscured (Minimum)**: no sticky overlay hides a focused control; the
  one fixed element (the online badge) sits clear of the focus path, and a skip link jumps
  past it straight to the demo.
- **2.5.8 Target Size (Minimum)**: interactive controls meet the 24x24 CSS-px minimum; the
  CI axe gate (`tests/e2e/a11y.spec.ts`) and the live `/judges` check both run the
  `wcag22aa` tag, so this is enforced, not asserted.

Beyond AA, two low-vision affordances: **forced colors** (Windows High Contrast Mode gets
system-colour pane borders + focus rings) and **`prefers-contrast: more`** (firms up
secondary text and drops pane translucency), both gated so the default visuals are untouched.

## The `aria-live` decision (assertive vs polite)

The verdict region is **`aria-live="assertive"`**, deliberately. The common guidance is
"prefer polite," and the **"VAR is reviewing" heads-up is polite** (it is unsolicited
context). But the verdict itself is the result the fan **explicitly requested** and the
product's whole thesis is that it arrives *before the broadcast catches up*, delaying it
in a polite queue until the screen reader finishes an unrelated utterance would defeat the
point. Assertive is the correct choice for an explicitly-requested, time-critical result;
it is not unsolicited chatter. Two supporting details:

- The region is **pre-registered empty on page load** (verified in CI) so the first
  announcement is reliable.
- An **alternating trailing non-breaking space** is appended to each message so an
  identical repeat verdict still re-announces in Safari + VoiceOver (which will not
  re-speak an unchanged string; WordPress core trac #36853).
- A **verbosity control** (Minimal / Standard / Coach) lets the listener dial back the
  prose to fight fatigue from repeated full-sentence announcements.

## Screen-reader test matrix

| Combination | Status |
|---|---|
| axe-core automated audit (reduced motion) | Passing in CI, zero serious/critical (`apps/web/tests/e2e/a11y.spec.ts`) |
| Playwright: live region pre-registered + empty on load | Passing in CI |
| Playwright: keyboard shortcut wired; sections + demo reachable by role | Passing in CI |
| NVDA + Firefox | Manual pass pending |
| VoiceOver (macOS) + Safari | Manual pass pending |
| VoiceOver (iOS) + Safari | Manual pass pending |
| TalkBack + Chrome (Android) | Manual pass pending |

The automated layer (axe + Playwright) runs on every push. The manual NVDA/VoiceOver
passes are the one honest gap; they are the next accessibility task before submission and
are tracked as such rather than claimed as done.

## Dual-track design

Every decorative surface (the 3D hero, the SVG pitch, the spatial-audio visualization) is
`aria-hidden` and motion-gated, and runs **parallel to** an always-present screen-reader
layer that carries the real explanation. The core spoken experience works with the screen
off and every visual removed.

## Keyboard map

`E` explain · `O` offline · `R` read aloud · `C` share clip · `S` sound · `D` detail ·
`L` live/replay · `V` verbosity · `1`-`5` language · `?` shortcut help. The stage scrubber
re-narrates any pipeline step with arrow keys.
