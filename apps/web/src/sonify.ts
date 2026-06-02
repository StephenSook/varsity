import type { Geometry } from './OffsidePitch'

export type Voice = {
  role: 'defender' | 'attacker' | 'ball'
  freq: number
  x: number
  y: number
  z: number
}

// Map the three players that matter onto a spatial chord. The offside line (the
// second-to-last defender) sits at the centre; the attacker is offset to the right
// by the margin, so a blind fan hears HOW FAR beyond the line the attacker was,
// before the words arrive. A supplement to the spoken explanation, never a
// replacement. (Precedent: Action Audio, Australian Open 2021-22.)
export function sonificationPlan(geo: Geometry): Voice[] {
  const k = 0.45 // pitch units -> audio left/right scale
  const z = -3 // place the voices in front of the listener (Web Audio faces -Z)
  const lineX = geo.offside_line_x
  const actor = geo.players.find((p) => p.actor)
  const ballX = actor ? actor.x : lineX
  return [
    { role: 'defender', freq: 196, x: 0, y: 0, z }, // the line: centred, low (G3)
    { role: 'attacker', freq: 587, x: (geo.attacker_x - lineX) * k, y: 0, z }, // high (D5), right = beyond
    { role: 'ball', freq: 392, x: (ballX - lineX) * k, y: 0, z }, // mid (G4)
  ]
}

export type SonifyOptions = { durationMs?: number; gain?: number }

// Play a short HRTF-panned chord of the three key players. Must be called from a
// user gesture (the AudioContext is created/resumed by the caller). Returns the
// plan it played, so it can be asserted.
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
    // Prefer the positionX/Y/Z AudioParams over the deprecated setPosition().
    panner.positionX.value = v.x
    panner.positionY.value = v.y
    panner.positionZ.value = v.z

    const gain = ctx.createGain()
    gain.gain.setValueAtTime(0, now)
    gain.gain.linearRampToValueAtTime(peak, now + 0.04)
    gain.gain.linearRampToValueAtTime(0, now + dur)

    osc.connect(gain).connect(panner).connect(ctx.destination)
    osc.start(now)
    osc.stop(now + dur + 0.02)
  }

  await new Promise((resolve) => setTimeout(resolve, durationMs + 60))
  return plan
}
