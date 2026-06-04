# Spatial audio: the cited front-hemisphere azimuth transform

Before the spoken verdict, VARSITY plays a short audio preamble: a line-sweep glissando, then
proximity blips, then a spatial chord (the offside line centred, the attacker panned by the real
margin), then the verdict earcon. The "where" of that pan is computed by one cited transform,
`pitchToAzimuth` in `apps/web/src/sonify.ts`. This note documents the psychoacoustics behind it
and, honestly, what it does and does not claim.

## What it claims (and what it does not)

VARSITY claims only **binary left/right**: the attacker is heard to the right of the line when
beyond it, to the left when behind it, and the pan reinforces the verbal and earcon cue. It does
**not** claim a navigation-grade spatial map. Shafique et al. (2025, *Frontiers in Neuroscience*
19:1660373) found that binaural-spatialized audio description alone did **not** significantly improve
a spatial-reconstruction task (14 participants, 7 blind), so spatialization is treated as a
reinforcing cue layered with the earcon and the words, not a load-bearing channel on its own.

On **HRTF personalization** (to be precise rather than wave it away as "impossible"): a genuinely
*individualized* per-user HRTF is infeasible in a browser without measuring each user's ears, and
the Web Audio `PannerNode` HRTF set is fixed by the browser and cannot be swapped (SOFA loading is
the open WebAudio v2 request #17, blocked because SOFA is HDF5, not a web standard). A *modeled*
alternative (selectable presets, or an ITD/ILD head-size slider via `ConvolverNode` HRIR
convolution) is feasible, but it was considered and deliberately not built: for a `±50°`, front-
hemisphere, binary-left/right *reinforcing* cue, the product's own cited evidence (Drullman &
Bronkhorst 2000: no individualized-vs-general difference; Shafique 2025: spatialization alone did
not help) puts its marginal benefit near zero. So this is an honest engineering decision, not a
feasibility wall.

## The transform

```
azimuth = clamp(normalized, -1, +1) * MAX_AZIMUTH_DEG
```

where `normalized` is the signed offside margin scaled into `[-1, +1]`. The result is rendered in
the listener's chosen mode: HRTF (a position on a front-hemisphere circle, headphones), stereo
(an equal-power pan), or mono (no spatialization, widest compatibility).

## Cited parameters

| Parameter | Value | Source |
|---|---|---|
| Max azimuth | **±50°** (hard ceiling ±60°) | Generic (non-individualized) HRTF speech stays intelligible and usefully localizable to this azimuth. Drullman & Bronkhorst 2000, *JASA* 107(4):2224-2235: "no difference was found between the use of an individualized 3-D auditory display and a general display" for intelligibility, talker recognition, or localization. Begault & Wenzel 1993, *Human Factors* 35(2): usable azimuth from non-individualized-HRTF-filtered speech. |
| Front hemisphere only | azimuth within [-90°, +90°], used [-50°, +50°] | Avoids the ~**40.7%** mean front-back confusion of non-individualized HRTF. Steadman, Kim, Lestang, Goodman & Picinali 2019, *Scientific Reports* 9, doi:10.1038/s41598-019-54811-w: "The mean initial front-back confusion rate (40.7%) was also consistent with other studies using non-individualized HRTFs." |
| Min separation | **≥8°** | Above the minimum audible angle (~1° at the front, Mills 1958, *JASA* 30(4):237-246); a conservative ~5-10° practical floor for broadband generic-HRTF speech. |
| Position ramp | **30 ms** | An instant pan placement is ramped over 30 ms so it does not click. |

Headphones are recommended for the HRTF mode (binaural rendering relies on inter-aural isolation);
the stereo and mono modes are provided for speakers and the widest compatibility, and the spoken
explanation is fully intelligible in mono.

## Confidence earcon parameters

The verdict earcon's *texture* encodes how clear-cut the call is (the uncertainty band), so a blind
fan hears the confidence a sighted fan reads off the margin. Two cross-modal findings drive it:

- **Loudness encodes confidence.** Loudness is the audio channel listeners most prefer for
  representing probability (Vriend, Hägele & Weiskopf, *Audio Mostly* 2025, arXiv 2505.14379,
  doi:10.1145/3771594.3771604: "loudness was especially suitable for AV semiotics of uncertainty").
  A clear call is loud; a too-close call is quieter.
- **Broadband noise encodes blur/uncertainty.** A pure clean tone reads as sharp/certain and
  broadband noise as blurry/uncertain (Ferguson & Brewster, *CHI* 2018 doi:10.1145/3173574.3174185
  and *ICMI* 2017 doi:10.1145/3136755.3136783: "broadband noise at 0% and a pure clean tone at
  100%… the blur of an image being related to the roughness or noise content of a sound"). A clear
  call is a pure tone; a too-close call adds an audible noise layer.

| Parameter | clear | tight | too-close |
|---|---|---|---|
| Loudness scale | 1.0 | 0.71 (-3 dB) | 0.5 (-6 dB) |
| Broadband noise mix | 0% | 10% | 30% |
| Amplitude tremolo | none | 10% @ 4 Hz | 30% @ 4 Hz |
| Attack | sharp (5 ms) | medium (30 ms) | soft (80 ms) |

These layer on the existing beating texture (a detuned partner tone for a tight call, plus a rough
neighbour for a too-close one; Plomp & Levelt critical-band roughness) and the bouba/kiki timbre.
The mapping is a pure, unit-tested function (`confidenceEarcon` in `apps/web/src/sonify.ts`).

## In concept

The pan encodes the geometry of a received decision (how far beyond the line the attacker was). It
never adjudicates. The transform is a pure, unit-tested function (`apps/web/src/sonify.test.ts`).
