import type { Geometry } from './OffsidePitch'

export type Voice = {
  role: 'defender' | 'attacker' | 'ball'
  freq: number
  x: number
  y: number
  z: number
}

// Listener-centred coordinate transform. The blind listener stands ON the offside
// line facing the field: the second-to-last defender is the fixed near reference at
// centre, and the attacker is placed by the REAL geometry margin so a clearly audible
// left/right arc encodes how far beyond the line the attacker was. Mapping the literal
// 120x80m pitch into PannerNode metres would put players ~60m away and inaudible, so
// we normalise the margin into a small +/- arc the ear can resolve.
const Z = -2 // a comfortable "in front" distance (Web Audio faces -Z)
const METERS_PER_UNIT = 105 / 120
const ARC = 1.6 // audio metres of pan per real metre of margin
const MAX_X = 3

const clampX = (x: number): number => Math.max(-MAX_X, Math.min(MAX_X, x))

export function sonificationPlan(geo: Geometry): Voice[] {
  const lineX = geo.offside_line_x
  const actor = geo.players.find((p) => p.actor)
  const ballX = actor ? actor.x : lineX
  const marginM = (geo.attacker_x - lineX) * METERS_PER_UNIT // signed: + = beyond the line
  const ballM = (ballX - lineX) * METERS_PER_UNIT
  return [
    { role: 'defender', freq: 196, x: 0, y: 0, z: Z }, // the line: centred, low (G3)
    { role: 'attacker', freq: 587, x: clampX(marginM * ARC), y: 0, z: Z }, // high (D5), right = beyond
    { role: 'ball', freq: 392, x: clampX(ballM * ARC), y: 0, z: Z }, // mid (G4)
  ]
}

// The three accessibility audio modes the listener can choose: HRTF (best with headphones),
// stereo (better on speakers), and mono (no spatialization, for the widest compatibility).
export type SpatialMode = 'hrtf' | 'stereo' | 'mono'

// The pan position of the line-proximity preamble blips: at the attacker's margin-based
// position, so the proximity blips come from WHERE the attacker is. Pure + testable.
export function preambleBlipPan(geo: Geometry): number {
  const marginM = (geo.attacker_x - geo.offside_line_x) * METERS_PER_UNIT
  return clampX(marginM * ARC)
}

// One spatializer abstraction for the three modes, so the preamble blips and the spatial chord
// can be panned (or not) consistently with the listener's chosen mode.
function makeSpatial(ctx: AudioContext, mode: SpatialMode) {
  if (mode === 'mono') {
    const node = ctx.createGain()
    return { node, setX: (_x: number) => {}, rampX: (_a: number, _b: number, _t0: number, _t1: number) => {} }
  }
  if (mode === 'stereo') {
    const p = ctx.createStereoPanner()
    const pan = (x: number): number => Math.max(-1, Math.min(1, x / MAX_X))
    return {
      node: p,
      setX: (x: number) => {
        p.pan.value = pan(x)
      },
      rampX: (a: number, b: number, t0: number, t1: number) => {
        p.pan.setValueAtTime(pan(a), t0)
        p.pan.linearRampToValueAtTime(pan(b), t1)
      },
    }
  }
  const p = ctx.createPanner()
  p.panningModel = 'HRTF'
  p.distanceModel = 'inverse'
  p.positionY.value = 0
  p.positionZ.value = Z
  return {
    node: p,
    setX: (x: number) => {
      p.positionX.value = x
    },
    rampX: (a: number, b: number, t0: number, t1: number) => {
      p.positionX.setValueAtTime(a, t0)
      p.positionX.linearRampToValueAtTime(b, t1)
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
// earcon. The attacker tone is ANIMATED from the line outward to its final position,
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
  const blipPan = preambleBlipPan(geo) // the blips come from where the attacker is
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
    sp.setX(blipPan)
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
      // Ramp from the line (x=0) out to the final position so the cross is heard.
      sp.rampX(0, v.x, now, now + dur)
    } else {
      sp.setX(v.x)
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
    const tone = (freq: number, g: number) => {
      const osc = ctx.createOscillator()
      osc.type = tim.waveform
      osc.frequency.value = freq
      const filter = ctx.createBiquadFilter()
      filter.type = tim.filterType
      filter.frequency.value = tim.filterHz
      const gain = ctx.createGain()
      gain.gain.setValueAtTime(0, vStart)
      gain.gain.linearRampToValueAtTime(peak * g, vStart + 0.05)
      gain.gain.linearRampToValueAtTime(0, vStart + vDur)
      osc.connect(filter).connect(gain).connect(ctx.destination)
      osc.start(vStart)
      osc.stop(vStart + vDur + 0.02)
    }
    const freqs = verdictChord(geo.is_offside)
    for (const f of freqs) {
      tone(f, 0.9)
      if (tex.detuneCents > 0) tone(detuneHz(f, tex.detuneCents), 0.5) // beating partner
    }
    if (tex.roughness) tone(detuneHz(freqs[0], 100), 0.4) // a rough neighbour (~semitone)
  }

  await new Promise((resolve) => setTimeout(resolve, durationMs + 600 + Math.round(preDur * 1000)))
  return plan
}

export type BuildUpStep = { t: number; gapMeters: number; x: number }

// The "gasp moment": sonify the seconds BEFORE the call, not just the verdict. We only
// have the single freeze-frame, so this RECONSTRUCTS a plausible approach: the attacker
// runs from ~6m behind the offside line to their real freeze-frame position, while the
// second-to-last defender holds the line. It is illustrative, grounded in the real final
// margin (the end point is the measured value), not measured tracking data.
export function buildUpTrajectory(geo: Geometry, steps = 24): BuildUpStep[] {
  const finalGap = (geo.attacker_x - geo.offside_line_x) * METERS_PER_UNIT
  const startGap = Math.min(-6, finalGap - 6) // at least a 6 m run-up to the line
  const out: BuildUpStep[] = []
  for (let i = 0; i <= steps; i++) {
    const t = i / steps
    const eased = t * t // ease-in: the run accelerates toward the line
    const gapMeters = startGap + (finalGap - startGap) * eased
    out.push({ t, gapMeters, x: clampX(gapMeters * ARC) })
  }
  return out
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

  // Rising attacker tone, panned along the reconstructed approach.
  const att = ctx.createOscillator()
  att.type = 'sawtooth'
  att.frequency.setValueAtTime(300, now)
  att.frequency.linearRampToValueAtTime(680, now + dur)
  const attPan = ctx.createPanner()
  attPan.panningModel = 'HRTF'
  attPan.positionZ.value = -2
  attPan.positionX.setValueAtTime(traj[0].x, now)
  for (const s of traj) attPan.positionX.linearRampToValueAtTime(s.x, now + s.t * dur)
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
