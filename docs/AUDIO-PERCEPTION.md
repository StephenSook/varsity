# Audio perception: the spatial scan and the Plomp-Levelt margin chord

The audio is the product for a blind fan, so the perceptual layer (`apps/web/src/sonify.ts`) is
where VARSITY earns the most. This wave harvests the psychoacoustics research report. Every cue
works on data VARSITY already has (the freeze-frame `(x, y)` points and the computed margin);
none recompute the call. Pure-math mappings are unit-tested; the Web Audio playback is
manual-verified (WebAudio is not observable in headless Playwright).

## The Plomp-Levelt margin chord (`marginChord`)

Two simultaneous tones whose frequency separation falls within ~a quarter of the **critical
band** produce maximum **roughness** (audible beating); separated past one critical band they fuse
into a smooth, consonant dyad (Plomp & Levelt, "Tonal consonance and critical bandwidth",
*J. Acoust. Soc. Am.* 38(4):548-560, 1965). Near a 500 Hz reference the Bark critical bandwidth
(Zwicker 1961) is ~100 Hz.

VARSITY maps the **margin itself** (not the confidence band) to this dyad: a knife-edge margin
detunes the partner tone ~25 Hz into the rough zone (the listener *hears* a near call as
roughness), a clear margin widens the detuning past a critical band into consonance, and the
**sign** of the margin puts the partner tone above the reference (offside) or below it (onside).
This is the margin's value made audible, distinct from `confidenceTexture` (which maps the
uncertainty band's roughness).

## The HRTF spatial scan (`spatialScanPlan`, `playSpatialScan`)

A short headphone "scan" of the whole freeze-frame: each visible player is pinged at its lateral
position via the Web Audio `PannerNode` (`panningModel: 'HRTF'`), defenders first (darker
triangle timbre, 440 Hz) then attackers (brighter sawtooth, 660 Hz), then the offside line
(centred sine, 523 Hz). Each onset is separated by a **300 ms** gap so the listener can segregate
and identify successive pings (McGookin & Brewster, *ACM TAP* 1(2), 2004). Within ~2 seconds a
blind fan has a spatial map of the moment, a dimension current offside coverage never delivers.

## The Brewster earcon parameters (`BREWSTER`)

The earcon palette uses the experimentally-derived guidelines of Brewster, Wright & Edwards
("Experimentally Derived Guidelines for the Creation of Earcons", *BCS HCI'95*): pitch range
**125 Hz to 5 kHz**, **minimum note length 0.0825 s**, **0.1 s** gap between serial earcons. These
are exported as named constants so the timing is grounded, not guessed.

## Equal-loudness normalization (ISO 226:2003)

The ear is not equally sensitive across frequency: a 125 Hz tone and a 3.5 kHz tone at the same
amplitude are perceived at very different loudness, so an un-normalized earcon palette would let
the low spatial pings drown the high ones (or the reverse). `iso226Gain(freqHz)` corrects this. It
evaluates the ISO 226:2003 equal-loudness contour (the standard's analytic `af`/`Lu`/`Tf`
coefficient table, log-frequency interpolated) at a reference loudness of 60 phons, then returns
the gain `10^((Lp(f) - 60)/20)` that brings every tone to the same perceived loudness: a frequency
the ear is insensitive to is boosted, the most sensitive band (~3-4 kHz) is cut, and 1 kHz is
unity by construction (the contour passes through 60 dB SPL at 1 kHz). The coefficient table was
cross-checked digit-for-digit against ISO 226:2003 Table 1 and the canonical implementations, and
the 1 kHz self-consistency (60 phon round-trips to 60.01 dB SPL) is asserted in a unit test. The
spatial scan applies this per-player so every ping is equally loud regardless of its pitch.

## Confidence as timbre (`confidenceVoice`)

The verdict earcon already moves loudness, noise, tremolo and detune with the call's tightness.
`confidenceVoice` adds two more perceptual axes for the knife-edge band: **vibrato** (a slow pitch
wobble that grows from 0 on a clear call to 25 cents on a very-tight one) and **inharmonicity** (a
partial that drifts off the harmonic series, so the tone sounds unstable as the margin shrinks).
A clear call is a pure, steady tone; a too-close-to-call decision audibly wavers, so the listener
hears the uncertainty before the words arrive. Tests assert vibrato and inharmonicity rise
monotonically as confidence falls.

## What it surfaces in the demo

A "Spatial scan (headphones)" button plays the HRTF scan of the current freeze-frame; the margin
chord composes with the existing verdict earcon and the front-hemisphere spatial preamble. The
listener-centred HRTF, the front-pinna intelligibility clamp (azimuth capped at 50 degrees so
generic-HRTF speech stays clear), and the three audio modes (HRTF / stereo / mono) were already
in `sonify.ts`; this wave adds the full-scene scan and the margin-value roughness.

## Honest scope

The Web Audio `PannerNode` HRTF is a non-individualized composite (IRCAM LISTEN), so a small
fraction of listeners will have front-back errors; a visual and textual fallback is always
present. Roughness is reserved for the peak of a close call (it is fatiguing if held), and the
front-hemisphere azimuth clamp keeps speech intelligible. The cues describe the received decision;
they never adjudicate.
