import type { Geometry } from './OffsidePitch'

export type Voice = {
  role: 'defender' | 'attacker' | 'ball'
  freq: number
  azimuthDeg: number // front-hemisphere azimuth: 0 = centre, + = right (beyond the line), - = left
}

// --- Spatial preamble: a cited, front-hemisphere azimuth transform ---------------------------
// The blind listener stands ON the offside line facing the field. The second-to-last defender is
// the fixed centre reference; the attacker is placed by the REAL geometry margin so a clearly
// audible left/right arc encodes how far beyond the line they were. Generic (non-individualized)
// HRTF is reliable for LEFT/RIGHT only, so the pan is constrained to the FRONT hemisphere with a
// conservative azimuth ceiling, and we claim only binary left/right: the pan REINFORCES the verbal
// and earcon cue, it is not a navigation-grade spatial map (Shafique et al., Front. Neurosci.
// 19:1660373, 2025: binaural description alone did not improve a spatial-reconstruction task). It
// encodes the GEOMETRY of a received decision; it never adjudicates. See docs/SPATIAL-AUDIO.md.
//
// Cited parameters:
// - MAX_AZIMUTH_DEG 50 (hard ceiling 60): generic-HRTF speech stays intelligible and usefully
//   localizable to this azimuth (Drullman & Bronkhorst 2000, JASA 107(4): no individualized-vs-
//   general 3-D display difference for intelligibility/recognition/localization; Begault & Wenzel
//   1993, Human Factors 35(2): usable azimuth from non-individualized-HRTF speech).
// - FRONT hemisphere only: avoids the ~40.7% mean front-back confusion of non-individualized HRTF
//   (Steadman et al., Sci. Rep. 9, 2019, doi:10.1038/s41598-019-54811-w).
// - MIN_SEPARATION_DEG 8: above the minimum audible angle (~1 deg at the front, Mills 1958;
//   ~5-10 deg practical floor for broadband generic-HRTF speech).
// - POSITION_RAMP_MS 30: ramp the pan into place so an instant placement does not click.
export const MAX_AZIMUTH_DEG = 50
export const MIN_SEPARATION_DEG = 8
export const POSITION_RAMP_MS = 30
const RADIUS = 2 // "in front" distance for the HRTF circle (Web Audio faces -Z)
const MARGIN_SPAN_M = 1.9 // |margin| in metres that maps to the full +/- MAX_AZIMUTH_DEG
const METERS_PER_UNIT = 0.9144 // StatsBomb's 120x80 grid is in yards (see services/app/geometry.py)

const clamp = (v: number, lo: number, hi: number): number => Math.max(lo, Math.min(hi, v))

// Map a normalized lateral position (-1 = full left, +1 = full right) to an azimuth in degrees,
// clamped to the cited front-hemisphere ceiling. Pure + testable: the single source of truth for
// "where" in the spatial preamble.
export function pitchToAzimuth(normalized: number, maxAzimuthDeg = MAX_AZIMUTH_DEG): number {
  return clamp(normalized, -1, 1) * maxAzimuthDeg
}

// The signed offside margin (metres beyond the line) as a normalized lateral position.
export function marginToNormalized(marginMeters: number): number {
  return clamp(marginMeters / MARGIN_SPAN_M, -1, 1)
}

const marginMeters = (geo: Geometry): number =>
  (geo.attacker_x - geo.offside_line_x) * METERS_PER_UNIT

const azToPan = (azDeg: number): number => Math.sin((azDeg * Math.PI) / 180)
const azToX = (azDeg: number): number => Math.sin((azDeg * Math.PI) / 180) * RADIUS
const azToZ = (azDeg: number): number => -Math.cos((azDeg * Math.PI) / 180) * RADIUS

export function sonificationPlan(geo: Geometry): Voice[] {
  const lineX = geo.offside_line_x
  const actor = geo.players.find((p) => p.actor)
  const ballX = actor ? actor.x : lineX
  const ballM = (ballX - lineX) * METERS_PER_UNIT
  return [
    { role: 'defender', freq: 196, azimuthDeg: 0 }, // the line: centred, low (G3)
    { role: 'attacker', freq: 587, azimuthDeg: pitchToAzimuth(marginToNormalized(marginMeters(geo))) },
    { role: 'ball', freq: 392, azimuthDeg: pitchToAzimuth(marginToNormalized(ballM)) },
  ]
}

// The three accessibility audio modes the listener can choose: HRTF (best with headphones),
// stereo (better on speakers), and mono (no spatialization, for the widest compatibility).
export type SpatialMode = 'hrtf' | 'stereo' | 'mono'

// The azimuth of the line-proximity preamble blips: the attacker's margin-based azimuth, so the
// proximity blips come from WHERE the attacker is. Pure + testable.
export function preambleBlipAzimuth(geo: Geometry): number {
  return pitchToAzimuth(marginToNormalized(marginMeters(geo)))
}

// One spatializer abstraction for the three modes, working in AZIMUTH degrees (front hemisphere),
// so the preamble blips and the spatial chord are panned (or not) consistently with the mode.
function makeSpatial(ctx: AudioContext, mode: SpatialMode) {
  if (mode === 'mono') {
    const node = ctx.createGain()
    return {
      node,
      setAz: (_az: number) => {},
      rampAz: (_a: number, _b: number, _t0: number, _t1: number) => {},
    }
  }
  if (mode === 'stereo') {
    const p = ctx.createStereoPanner()
    return {
      node: p,
      setAz: (az: number) => {
        p.pan.value = azToPan(az)
      },
      rampAz: (a: number, b: number, t0: number, t1: number) => {
        p.pan.setValueAtTime(azToPan(a), t0)
        p.pan.linearRampToValueAtTime(azToPan(b), t1)
      },
    }
  }
  const p = ctx.createPanner()
  p.panningModel = 'HRTF'
  p.distanceModel = 'inverse'
  p.positionY.value = 0
  return {
    node: p,
    setAz: (az: number) => {
      p.positionX.value = azToX(az)
      p.positionZ.value = azToZ(az)
    },
    rampAz: (a: number, b: number, t0: number, t1: number) => {
      p.positionX.setValueAtTime(azToX(a), t0)
      p.positionZ.setValueAtTime(azToZ(a), t0)
      p.positionX.linearRampToValueAtTime(azToX(b), t1)
      p.positionZ.linearRampToValueAtTime(azToZ(b), t1)
    },
  }
}

// Verdict earcon: a consonant major triad reads as "allowed / onside"; a minor triad
// with a tritone reads as "denied / wrong / offside" (Brewster & Blattner earcon
// theory; Western listeners decode the tritone as tension/negation). Played centred
// after the spatial sweep so the verdict is unmistakable before any words arrive.
export function verdictChord(isOffside: boolean): number[] {
  return isOffside
    ? [261.63, 311.13, 369.99] // C4 minor + tritone (C, Eb, F#) = offside
    : [261.63, 329.63, 392.0] // C4 major triad (C, E, G) = onside
}

// Couple the verdict earcon's roughness to how clear-cut the call is (the uncertainty band).
// A clear call is a pure triad; a tight call adds slow beating (a few Hz) from a detuned
// partner tone; a very-tight ("VARSITY's Call" / umpire's-call) result adds stronger beating
// plus one rough neighbour tone. A blind listener HEARS the uncertainty a sighted fan would
// read off the margin. Beating-as-roughness is psychoacoustically grounded (Plomp & Levelt
// critical-band roughness; the closer two tones, the rougher/less-resolved they sound).
export function confidenceTexture(band?: string): { detuneCents: number; roughness: boolean } {
  if (band === 'very tight') return { detuneCents: 35, roughness: true }
  if (band === 'tight') return { detuneCents: 14, roughness: false }
  return { detuneCents: 0, roughness: false } // clear (or unknown) = pure, confident
}

// Richer confidence-earcon parameters, layered on the beating texture above. Two cited cross-modal
// findings drive them: LOUDNESS is the audio channel listeners most prefer for probability, so
// confidence scales loudness (Vriend, Hagele & Weiskopf, Audio Mostly 2025, arXiv 2505.14379); and
// ROUGHNESS / broadband NOISE maps to visual BLUR - a pure clean tone reads as sharp/certain,
// broadband noise as blurry/uncertain (Ferguson & Brewster, CHI 2018 doi:10.1145/3173574.3174185;
// ICMI 2017 doi:10.1145/3136755.3136783). So a clear call is LOUD, PURE, SHARP-attack; a too-close
// call is QUIETER, NOISIER, TREMOLO'd, SOFT-attack. Pure + testable. See docs/SPATIAL-AUDIO.md.
export type ConfidenceEarcon = {
  loudnessScale: number // confidence up -> louder (Vriend 2025: loudness most-preferred for probability)
  noiseMix: number // confidence down -> more broadband noise / blur (Ferguson & Brewster)
  tremoloDepth: number // confidence down -> deeper amplitude tremolo
  tremoloHz: number
  attackMs: number // confidence down -> softer attack
}

export function confidenceEarcon(band?: string): ConfidenceEarcon {
  if (band === 'very tight')
    return { loudnessScale: 0.5, noiseMix: 0.3, tremoloDepth: 0.3, tremoloHz: 4, attackMs: 80 }
  if (band === 'tight')
    return { loudnessScale: 0.71, noiseMix: 0.1, tremoloDepth: 0.1, tremoloHz: 4, attackMs: 30 }
  return { loudnessScale: 1, noiseMix: 0, tremoloDepth: 0, tremoloHz: 0, attackMs: 5 } // clear/unknown
}

const detuneHz = (f: number, cents: number): number => f * Math.pow(2, cents / 1200)

// Pre-verbal line-proximity preamble (the Action Audio pattern): BEFORE the verdict, a short
// burst of blips whose COUNT encodes how close the attacker was to the offside line (3 = right on
// the line / very tight, 1 = clear), and whose PITCH encodes beyond-the-line (offside = high) vs
// behind-the-line (onside = low). The pitch-height cross-modal correspondence is universal and
// pre-linguistic (Spence 2011; Loconsole et al., Science 2026). It gives a blind fan a ~600 ms
// spatial cue before any words, in a distinct timbre with a gap before the speech (Bregman ASA).
export function lineProximityPreamble(
  band: string | undefined,
  isOffside: boolean,
): { blips: number; freq: number } {
  const blips = band === 'very tight' ? 3 : band === 'tight' ? 2 : 1
  const freq = isOffside ? 880 : 330 // beyond the line = high (A5); behind = low (E4)
  return { blips, freq }
}

// Phase A of the preamble: a short downward glissando = "the offside line is being drawn",
// played centred BEFORE the proximity blips (a pitch glide is the strongest auditory-stream
// "line" cue, Bregman ASA). Pure + testable.
export function lineSweepSpec(): { fromHz: number; toHz: number; durMs: number } {
  return { fromHz: 660, toHz: 440, durMs: 150 }
}

// Bouba/kiki verdict timbre: a CLEAR call is a rounded "bouba" (sine through a gentle lowpass);
// a tight/very-tight call is a sharp "kiki" (sawtooth through a bright bandpass). The
// rounded-vs-spiky sound-to-shape mapping is pre-linguistic and species-general (Loconsole,
// Benavides-Varela & Regolin, Science 2026; Spence 2011). Pure + testable.
export function verdictTimbre(band?: string): {
  waveform: OscillatorType
  filterType: BiquadFilterType
  filterHz: number
} {
  const tight = band === 'tight' || band === 'very tight'
  return tight
    ? { waveform: 'sawtooth', filterType: 'bandpass', filterHz: 3000 } // kiki: sharp, spiky
    : { waveform: 'sine', filterType: 'lowpass', filterHz: 800 } // bouba: rounded, gentle
}

export type SonifyOptions = {
  durationMs?: number
  gain?: number
  verdict?: boolean
  band?: string
  preamble?: boolean
  mode?: SpatialMode
}

// Play a short HRTF-panned chord of the three key players, then a semantic verdict
// earcon. The attacker tone is ANIMATED from the line outward to its final azimuth,
// so the listener hears it cross (offside) or not cross (onside) the line as motion,
// not a static pan. Must be called from a user gesture (the caller creates/resumes the
// AudioContext). Returns the plan it played, so it can be asserted.
export async function playOffsideChord(
  ctx: AudioContext,
  geo: Geometry,
  opts: SonifyOptions = {},
): Promise<Voice[]> {
  const durationMs = opts.durationMs ?? 500
  const peak = opts.gain ?? 0.12
  const mode = opts.mode ?? 'hrtf'
  const plan = sonificationPlan(geo)
  const t0 = ctx.currentTime
  const ramp = POSITION_RAMP_MS / 1000

  // Phase A: a centred line-sweep glissando ("the offside line is being drawn") before the blips.
  let phaseA = 0
  if (opts.preamble !== false) {
    const sweep = lineSweepSpec()
    const sweepDur = sweep.durMs / 1000
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(sweep.fromHz, t0)
    osc.frequency.linearRampToValueAtTime(sweep.toHz, t0 + sweepDur)
    const g = ctx.createGain()
    g.gain.setValueAtTime(0, t0)
    g.gain.linearRampToValueAtTime(peak * 0.6, t0 + 0.02)
    g.gain.linearRampToValueAtTime(0, t0 + sweepDur)
    osc.connect(g).connect(ctx.destination)
    osc.start(t0)
    osc.stop(t0 + sweepDur + 0.02)
    phaseA = sweepDur + 0.05 // a small gap after the sweep
  }

  // Phase B: line-proximity preamble - blip count = closeness to the line, pitch = beyond/behind.
  const pre =
    opts.preamble === false
      ? { blips: 0, freq: 0 }
      : lineProximityPreamble(opts.band, geo.is_offside)
  const blipGap = 0.12
  const blipDur = 0.07
  const blipAz = preambleBlipAzimuth(geo) // the blips come from where the attacker is
  for (let i = 0; i < pre.blips; i++) {
    const start = t0 + phaseA + i * blipGap
    const osc = ctx.createOscillator()
    osc.type = 'square'
    osc.frequency.value = pre.freq
    const g = ctx.createGain()
    g.gain.setValueAtTime(0, start)
    g.gain.linearRampToValueAtTime(peak * 0.5, start + 0.01)
    g.gain.linearRampToValueAtTime(0, start + blipDur)
    const sp = makeSpatial(ctx, mode)
    sp.rampAz(0, blipAz, start, start + ramp) // 30 ms ramp into place: no click on the jump
    osc.connect(g).connect(sp.node).connect(ctx.destination)
    osc.start(start)
    osc.stop(start + blipDur + 0.02)
  }
  const preDur = phaseA + (pre.blips > 0 ? pre.blips * blipGap + 0.12 : 0)

  const now = t0 + preDur // the spatial sweep + verdict follow the preamble
  const dur = durationMs / 1000

  for (const v of plan) {
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.value = v.freq

    const sp = makeSpatial(ctx, mode)
    if (v.role === 'attacker') {
      // Ramp from the line (azimuth 0) out to the final azimuth so the cross is heard as motion.
      sp.rampAz(0, v.azimuthDeg, now, now + dur)
    } else {
      sp.setAz(v.azimuthDeg)
    }

    const gain = ctx.createGain()
    gain.gain.setValueAtTime(0, now)
    gain.gain.linearRampToValueAtTime(peak, now + 0.04)
    gain.gain.linearRampToValueAtTime(0, now + dur)

    osc.connect(gain).connect(sp.node).connect(ctx.destination)
    osc.start(now)
    osc.stop(now + dur + 0.02)
  }

  if (opts.verdict !== false) {
    const vStart = now + dur + 0.06
    const vDur = 0.45
    const tex = confidenceTexture(opts.band)
    const tim = verdictTimbre(opts.band) // bouba (clear) vs kiki (tight): waveform + filter
    const ce = confidenceEarcon(opts.band) // loudness + noise + tremolo + attack, cited
    const ePeak = peak * ce.loudnessScale // confidence -> loudness (Vriend 2025)
    const attack = ce.attackMs / 1000
    const tone = (freq: number, g: number) => {
      const osc = ctx.createOscillator()
      osc.type = tim.waveform
      osc.frequency.value = freq
      const filter = ctx.createBiquadFilter()
      filter.type = tim.filterType
      filter.frequency.value = tim.filterHz
      const gain = ctx.createGain()
      gain.gain.setValueAtTime(0, vStart)
      gain.gain.linearRampToValueAtTime(ePeak * g, vStart + attack)
      gain.gain.linearRampToValueAtTime(0, vStart + vDur)
      osc.connect(filter).connect(gain)
      let out: AudioNode = gain
      if (ce.tremoloDepth > 0) {
        // amplitude tremolo: an LFO oscillates the gain between (1 - 2*depth) and 1.
        const trem = ctx.createGain()
        trem.gain.value = 1 - ce.tremoloDepth
        const lfo = ctx.createOscillator()
        lfo.type = 'sine'
        lfo.frequency.value = ce.tremoloHz
        const lfoGain = ctx.createGain()
        lfoGain.gain.value = ce.tremoloDepth
        lfo.connect(lfoGain).connect(trem.gain)
        lfo.start(vStart)
        lfo.stop(vStart + vDur + 0.02)
        gain.connect(trem)
        out = trem
      }
      out.connect(ctx.destination)
      osc.start(vStart)
      osc.stop(vStart + vDur + 0.02)
    }
    const freqs = verdictChord(geo.is_offside)
    for (const f of freqs) {
      tone(f, 0.9)
      if (tex.detuneCents > 0) tone(detuneHz(f, tex.detuneCents), 0.5) // beating partner
    }
    if (tex.roughness) tone(detuneHz(freqs[0], 100), 0.4) // a rough neighbour (~semitone)

    // Broadband-noise "blur" layer: confidence down -> audible noise (Ferguson & Brewster).
    if (ce.noiseMix > 0) {
      const len = Math.max(1, Math.ceil(vDur * ctx.sampleRate))
      const buf = ctx.createBuffer(1, len, ctx.sampleRate)
      const data = buf.getChannelData(0)
      for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1
      const src = ctx.createBufferSource()
      src.buffer = buf
      const bp = ctx.createBiquadFilter()
      bp.type = 'bandpass'
      bp.frequency.value = 1500
      bp.Q.value = 0.5 // a gentle band so it reads as roughness/blur, not harsh hiss
      const ng = ctx.createGain()
      ng.gain.setValueAtTime(0, vStart)
      ng.gain.linearRampToValueAtTime(ePeak * ce.noiseMix, vStart + attack)
      ng.gain.linearRampToValueAtTime(0, vStart + vDur)
      src.connect(bp).connect(ng).connect(ctx.destination)
      src.start(vStart)
      src.stop(vStart + vDur + 0.02)
    }
  }

  await new Promise((resolve) => setTimeout(resolve, durationMs + 600 + Math.round(preDur * 1000)))
  return plan
}

export type BuildUpStep = { t: number; gapMeters: number; azimuthDeg: number }

// The "gasp moment": sonify the seconds BEFORE the call, not just the verdict. We only
// have the single freeze-frame, so this RECONSTRUCTS a plausible approach: the attacker
// runs from ~6m behind the offside line to their real freeze-frame position, while the
// second-to-last defender holds the line. It is illustrative, grounded in the real final
// margin (the end point is the measured value), not measured tracking data.
export function buildUpTrajectory(geo: Geometry, steps = 24): BuildUpStep[] {
  const finalGap = marginMeters(geo)
  const startGap = Math.min(-6, finalGap - 6) // at least a 6 m run-up to the line
  const out: BuildUpStep[] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const eased = t * t // ease-in: the run accelerates toward the line
    const gapMeters = startGap + (finalGap - startGap) * eased
    out.push({ t, gapMeters, azimuthDeg: pitchToAzimuth(marginToNormalized(gapMeters)) })
  }
  return out
}

// --- Phase C: psychoacoustics harvest (the audio-perception research report) -----------------

// Brewster, Wright & Edwards (1995) earcon guidelines + McGookin & Brewster (2004): a 300 ms
// onset-to-onset gap so a listener can segregate and identify successive spatialized pings.
export const BREWSTER = {
  pitchLoHz: 125,
  pitchHiHz: 5000,
  minNoteMs: 82.5, // 0.0825 s minimum note length
  serialGapMs: 100,
  onsetGapMs: 300,
} as const

// The Plomp & Levelt (1965) "offside chord": map the MARGIN (not the confidence) to critical-band
// roughness. Near a 500 Hz reference the Bark critical bandwidth (Zwicker 1961) is ~100 Hz, and
// maximum roughness sits at ~1/4 of it. A knife-edge margin detunes the partner tone ~25 Hz into
// the rough zone (audible beating); a clear margin widens it past a critical band into consonance;
// the sign of the margin puts the partner above (offside) or below (onside) the reference. This is
// the margin's VALUE made audible, distinct from confidenceTexture (which maps the band).
export const CHORD_REF_HZ = 500
const CRITICAL_BAND_HZ = 100

export function marginChord(marginMeters: number): {
  refHz: number
  partnerHz: number
  deltaHz: number
  rough: boolean
} {
  const m = Math.abs(marginMeters)
  const deltaHz = Math.round(25 + 175 * Math.tanh(m / 0.5))
  const partnerHz = marginMeters >= 0 ? CHORD_REF_HZ + deltaHz : CHORD_REF_HZ - deltaHz
  return { refHz: CHORD_REF_HZ, partnerHz, deltaHz, rough: deltaHz < CRITICAL_BAND_HZ }
}

// A player's lateral position (y, 0-80 yards) as a front-hemisphere azimuth (left to right).
export function lateralAzimuth(yYards: number): number {
  return pitchToAzimuth(clamp((yYards - 40) / 40, -1, 1))
}

export type ScanVoice = {
  role: 'defender' | 'attacker' | 'line'
  azimuthDeg: number
  freq: number
  onsetMs: number
}

// A full HRTF spatial SCAN of the freeze-frame: each visible player pinged at its lateral
// position, defenders (darker, 440 Hz) then attackers (brighter, 660 Hz), then the offside line
// (centred, 523 Hz), each onset separated by Brewster's 300 ms gap so a blind fan can "scan" the
// geometry with their ears. Pure + testable; the WebAudio playback is manual-verified.
export function spatialScanPlan(geo: Geometry): ScanVoice[] {
  const defenders = geo.players.filter((p) => !p.teammate && !p.keeper)
  const attackers = geo.players.filter((p) => p.teammate && !p.actor)
  const out: ScanVoice[] = []
  let t = 0
  for (const d of defenders) {
    out.push({ role: 'defender', azimuthDeg: lateralAzimuth(d.y), freq: 440, onsetMs: t })
    t += BREWSTER.onsetGapMs
  }
  for (const a of attackers) {
    out.push({ role: 'attacker', azimuthDeg: lateralAzimuth(a.y), freq: 660, onsetMs: t })
    t += BREWSTER.onsetGapMs
  }
  out.push({ role: 'line', azimuthDeg: 0, freq: 523, onsetMs: t })
  return out
}

// Play the spatial scan over the chosen mode (HRTF / stereo / mono). Manual-verified (WebAudio is
// not observable in headless Playwright); the plan above is the unit-tested core.
export function playSpatialScan(geo: Geometry, mode: SpatialMode = 'hrtf'): void {
  const ctx = new AudioContext()
  for (const v of spatialScanPlan(geo)) {
    const t0 = ctx.currentTime + v.onsetMs / 1000
    const sp = makeSpatial(ctx, mode)
    sp.setAz(v.azimuthDeg)
    const osc = new OscillatorNode(ctx, {
      type: v.role === 'attacker' ? 'sawtooth' : v.role === 'line' ? 'sine' : 'triangle',
      frequency: v.freq,
    })
    const env = new GainNode(ctx, { gain: 0 })
    env.gain.setValueAtTime(0, t0)
    env.gain.linearRampToValueAtTime(0.22, t0 + 0.02)
    env.gain.exponentialRampToValueAtTime(0.001, t0 + 0.25)
    osc.connect(env).connect(sp.node).connect(ctx.destination)
    osc.start(t0)
    osc.stop(t0 + 0.3)
  }
}

// Play the Plomp-Levelt margin chord at the verdict moment: a 500 Hz reference + a partner tone
// detuned by the margin. A knife-edge call detunes inside the critical band, so the listener HEARS
// the closeness as roughness/beating; a clear call is a smooth, consonant dyad. Manual-verified.
export function playMarginChord(ctx: AudioContext, geo: Geometry, gain = 0.1, delaySec = 0): void {
  const { refHz, partnerHz } = marginChord(marginMeters(geo))
  const t0 = ctx.currentTime + delaySec
  const mix = new GainNode(ctx, { gain: 0 })
  mix.gain.setValueAtTime(0, t0)
  mix.gain.linearRampToValueAtTime(gain, t0 + 0.05)
  mix.gain.setValueAtTime(gain, t0 + 1.0)
  mix.gain.exponentialRampToValueAtTime(0.001, t0 + 1.4)
  mix.connect(ctx.destination)
  for (const hz of [refHz, partnerHz]) {
    const osc = new OscillatorNode(ctx, { type: 'sine', frequency: hz })
    osc.connect(mix)
    osc.start(t0)
    osc.stop(t0 + 1.4)
  }
}

// Play the build-up: a Geiger-counter click track that accelerates as the attacker
// nears the offside line, a rising attacker tone that pans from behind the line toward
// (and across, if offside) it, over a faint centred defender-line reference. ~3.5s, then
// hand off to playOffsideChord for the spatial chord + verdict earcon.
export async function playBuildUp(
  ctx: AudioContext,
  geo: Geometry,
  opts: { durationMs?: number; gain?: number } = {},
): Promise<BuildUpStep[]> {
  const durationMs = opts.durationMs ?? 3500
  const peak = opts.gain ?? 0.1
  const traj = buildUpTrajectory(geo)
  const now = ctx.currentTime
  const dur = durationMs / 1000

  // Faint, steady defender-line reference (low, centred).
  const ref = ctx.createOscillator()
  ref.type = 'sine'
  ref.frequency.value = 98 // G2
  const refGain = ctx.createGain()
  refGain.gain.setValueAtTime(0, now)
  refGain.gain.linearRampToValueAtTime(peak * 0.4, now + 0.3)
  refGain.gain.setValueAtTime(peak * 0.4, now + dur - 0.3)
  refGain.gain.linearRampToValueAtTime(0, now + dur)
  ref.connect(refGain).connect(ctx.destination)
  ref.start(now)
  ref.stop(now + dur + 0.02)

  // Rising attacker tone, panned along the reconstructed approach (front-hemisphere azimuth).
  const att = ctx.createOscillator()
  att.type = 'sawtooth'
  att.frequency.setValueAtTime(300, now)
  att.frequency.linearRampToValueAtTime(680, now + dur)
  const attPan = ctx.createPanner()
  attPan.panningModel = 'HRTF'
  attPan.positionY.value = 0
  attPan.positionX.setValueAtTime(azToX(traj[0].azimuthDeg), now)
  attPan.positionZ.setValueAtTime(azToZ(traj[0].azimuthDeg), now)
  for (const s of traj) {
    attPan.positionX.linearRampToValueAtTime(azToX(s.azimuthDeg), now + s.t * dur)
    attPan.positionZ.linearRampToValueAtTime(azToZ(s.azimuthDeg), now + s.t * dur)
  }
  const attGain = ctx.createGain()
  attGain.gain.setValueAtTime(0, now)
  attGain.gain.linearRampToValueAtTime(peak * 0.5, now + dur * 0.6)
  attGain.gain.linearRampToValueAtTime(peak * 0.75, now + dur)
  att.connect(attGain).connect(attPan).connect(ctx.destination)
  att.start(now)
  att.stop(now + dur + 0.02)

  // Accelerating click track (tempo rises toward the line). Intervals shrink toward a
  // floor (~16 Hz) and are capped, so the loop always terminates.
  let click = 0
  let interval = 0.34
  for (let i = 0; i < 48 && click < dur - 0.05; i++) {
    const osc = ctx.createOscillator()
    osc.type = 'triangle'
    osc.frequency.value = 440 + 440 * (click / dur) // pitch rises with tension
    const g = ctx.createGain()
    g.gain.setValueAtTime(0, now + click)
    g.gain.linearRampToValueAtTime(peak * 0.6, now + click + 0.006)
    g.gain.exponentialRampToValueAtTime(0.0001, now + click + 0.05)
    osc.connect(g).connect(ctx.destination)
    osc.start(now + click)
    osc.stop(now + click + 0.06)
    click += interval
    interval = Math.max(0.065, interval * 0.9) // accelerate to a ~16 Hz floor
  }

  await new Promise((resolve) => setTimeout(resolve, durationMs))
  return traj
}
