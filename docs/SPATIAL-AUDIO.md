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
| Front hemisphere only | azimuth ⊂ [−90°, +90°], used [−50°, +50°] | Avoids the ~**40.7%** mean front-back confusion of non-individualized HRTF. Steadman, Kim, Lestang, Goodman & Picinali 2019, *Scientific Reports* 9, doi:10.1038/s41598-019-54811-w: "The mean initial front-back confusion rate (40.7%) was also consistent with other studies using non-individualized HRTFs." |
| Min separation | **≥8°** | Above the minimum audible angle (~1° at the front, Mills 1958, *JASA* 30(4):237-246); a conservative ~5-10° practical floor for broadband generic-HRTF speech. |
| Position ramp | **30 ms** | An instant pan placement is ramped over 30 ms so it does not click. |

Headphones are recommended for the HRTF mode (binaural rendering relies on inter-aural isolation);
the stereo and mono modes are provided for speakers and the widest compatibility, and the spoken
explanation is fully intelligible in mono.

## In concept

The pan encodes the geometry of a received decision (how far beyond the line the attacker was). It
never adjudicates. The transform is a pure, unit-tested function (`apps/web/src/sonify.test.ts`).
