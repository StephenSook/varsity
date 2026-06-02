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

// Verdict earcon: a consonant major triad reads as "allowed / onside"; a minor triad
// with a tritone reads as "denied / wrong / offside" (Brewster & Blattner earcon
// theory; Western listeners decode the tritone as tension/negation). Played centred
// after the spatial sweep so the verdict is unmistakable before any words arrive.
export function verdictChord(isOffside: boolean): number[] {
  return isOffside
    ? [261.63, 311.13, 369.99] // C4 minor + tritone (C, Eb, F#) = offside
    : [261.63, 329.63, 392.0] // C4 major triad (C, E, G) = onside
}

export type SonifyOptions = { durationMs?: number; gain?: number; verdict?: boolean }

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
  const plan = sonificationPlan(geo)
  const now = ctx.currentTime
  const dur = durationMs / 1000

  for (const v of plan) {
    const osc = ctx.createOscillator()
    osc.type = 'sine'
    osc.frequency.value = v.freq

    const panner = ctx.createPanner()
    panner.panningModel = 'HRTF'
    panner.distanceModel = 'inverse'
    panner.positionY.value = v.y
    panner.positionZ.value = v.z
    if (v.role === 'attacker') {
      // Ramp from the line (x=0) out to the final position so the cross is heard.
      panner.positionX.setValueAtTime(0, now)
      panner.positionX.linearRampToValueAtTime(v.x, now + dur)
    } else {
      panner.positionX.value = v.x
    }

    const gain = ctx.createGain()
    gain.gain.setValueAtTime(0, now)
    gain.gain.linearRampToValueAtTime(peak, now + 0.04)
    gain.gain.linearRampToValueAtTime(0, now + dur)

    osc.connect(gain).connect(panner).connect(ctx.destination)
    osc.start(now)
    osc.stop(now + dur + 0.02)
  }

  if (opts.verdict !== false) {
    const vStart = now + dur + 0.06
    const vDur = 0.45
    for (const f of verdictChord(geo.is_offside)) {
      const osc = ctx.createOscillator()
      osc.type = 'triangle'
      osc.frequency.value = f
      const gain = ctx.createGain()
      gain.gain.setValueAtTime(0, vStart)
      gain.gain.linearRampToValueAtTime(peak * 0.9, vStart + 0.05)
      gain.gain.linearRampToValueAtTime(0, vStart + vDur)
      osc.connect(gain).connect(ctx.destination)
      osc.start(vStart)
      osc.stop(vStart + vDur + 0.02)
    }
  }

  await new Promise((resolve) => setTimeout(resolve, durationMs + 600))
  return plan
}
