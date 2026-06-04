import { describe, expect, it } from 'vitest'

import {
  BREWSTER,
  MAX_AZIMUTH_DEG,
  confidenceEarcon,
  confidenceTexture,
  confidenceVoice,
  iso226Gain,
  iso226Spl,
  lateralAzimuth,
  lineProximityPreamble,
  lineSweepSpec,
  marginChord,
  marginToNormalized,
  pitchToAzimuth,
  preambleBlipAzimuth,
  sonificationPlan,
  spatialScanPlan,
  verdictChord,
  verdictTimbre,
} from './sonify'

type Geo = Parameters<typeof sonificationPlan>[0]

const geo = (attacker_x: number, offside_line_x: number): Geo =>
  ({
    attacker_x,
    offside_line_x,
    is_offside: attacker_x > offside_line_x,
    players: [{ x: 50, y: 40, teammate: true, actor: true }],
  }) as unknown as Geo

describe('verdict earcon', () => {
  it('offside is a minor + tritone chord, onside a major triad', () => {
    expect(verdictChord(true)).toEqual([261.63, 311.13, 369.99])
    expect(verdictChord(false)).toEqual([261.63, 329.63, 392.0])
  })

  it('couples roughness to the uncertainty band', () => {
    expect(confidenceTexture('very tight')).toEqual({ detuneCents: 35, roughness: true })
    expect(confidenceTexture('tight')).toEqual({ detuneCents: 14, roughness: false })
    expect(confidenceTexture('clear')).toEqual({ detuneCents: 0, roughness: false })
    expect(confidenceTexture(undefined)).toEqual({ detuneCents: 0, roughness: false })
  })

  it('couples loudness, noise, tremolo and attack to confidence (Vriend; Ferguson & Brewster)', () => {
    const clear = confidenceEarcon('clear')
    const tight = confidenceEarcon('tight')
    const veryTight = confidenceEarcon('very tight')
    // a clear call is loud, pure, sharp; an unknown band defaults to clear
    expect(clear).toEqual({ loudnessScale: 1, noiseMix: 0, tremoloDepth: 0, tremoloHz: 0, attackMs: 5 })
    expect(confidenceEarcon(undefined).loudnessScale).toBe(1)
    // confidence down -> quieter, noisier (blur), deeper tremolo, softer attack
    expect(veryTight.loudnessScale).toBeLessThan(tight.loudnessScale)
    expect(tight.loudnessScale).toBeLessThan(clear.loudnessScale)
    expect(veryTight.noiseMix).toBeGreaterThan(tight.noiseMix)
    expect(tight.noiseMix).toBeGreaterThan(clear.noiseMix)
    expect(veryTight.attackMs).toBeGreaterThan(clear.attackMs)
    expect(veryTight.tremoloDepth).toBeGreaterThan(0)
  })

  it('uses a bouba timbre for clear calls and a kiki timbre for tight ones', () => {
    expect(verdictTimbre('clear')).toEqual({
      waveform: 'sine',
      filterType: 'lowpass',
      filterHz: 800,
    })
    expect(verdictTimbre(undefined)).toEqual({
      waveform: 'sine',
      filterType: 'lowpass',
      filterHz: 800,
    })
    expect(verdictTimbre('very tight')).toEqual({
      waveform: 'sawtooth',
      filterType: 'bandpass',
      filterHz: 3000,
    })
  })
})

describe('line-proximity preamble', () => {
  it('encodes closeness by blip count and beyond/behind by pitch', () => {
    expect(lineProximityPreamble('very tight', true)).toEqual({ blips: 3, freq: 880 })
    expect(lineProximityPreamble('tight', true)).toEqual({ blips: 2, freq: 880 })
    expect(lineProximityPreamble('clear', false)).toEqual({ blips: 1, freq: 330 })
  })

  it('the line-sweep glissando descends from 660 to 440 Hz', () => {
    expect(lineSweepSpec()).toEqual({ fromHz: 660, toHz: 440, durMs: 150 })
  })
})

describe('cited front-hemisphere azimuth transform', () => {
  it('maps a normalized position to a clamped azimuth, symmetric about centre', () => {
    expect(pitchToAzimuth(0)).toBe(0)
    expect(pitchToAzimuth(1)).toBe(MAX_AZIMUTH_DEG)
    expect(pitchToAzimuth(-1)).toBe(-MAX_AZIMUTH_DEG)
    expect(pitchToAzimuth(0.5)).toBeCloseTo(MAX_AZIMUTH_DEG / 2)
  })

  it('clamps beyond +/-1 to the front-hemisphere ceiling (never behind the listener)', () => {
    expect(pitchToAzimuth(5)).toBe(MAX_AZIMUTH_DEG)
    expect(pitchToAzimuth(-5)).toBe(-MAX_AZIMUTH_DEG)
    expect(Math.abs(pitchToAzimuth(99))).toBeLessThanOrEqual(60) // within the hard ceiling
  })

  it('honours an explicit max azimuth argument', () => {
    expect(pitchToAzimuth(1, 60)).toBe(60)
  })

  it('normalizes the offside margin into [-1, 1]', () => {
    expect(marginToNormalized(0)).toBe(0)
    expect(marginToNormalized(10)).toBe(1) // a large margin saturates, never wraps
    expect(marginToNormalized(-10)).toBe(-1)
  })
})

describe('spatial sonification plan', () => {
  it('centres the defender line and pans the attacker by the real margin', () => {
    const plan = sonificationPlan(geo(100, 98)) // beyond the line
    const defender = plan.find((v) => v.role === 'defender')!
    const attacker = plan.find((v) => v.role === 'attacker')!
    expect(defender.azimuthDeg).toBe(0)
    expect(attacker.azimuthDeg).toBeGreaterThan(0) // beyond the line -> azimuth to the right
    expect(attacker.azimuthDeg).toBeLessThanOrEqual(MAX_AZIMUTH_DEG) // never past the ceiling
  })

  it('pans an onside attacker to the left of the line', () => {
    const plan = sonificationPlan(geo(95, 98))
    const attacker = plan.find((v) => v.role === 'attacker')!
    expect(attacker.azimuthDeg).toBeLessThan(0)
  })

  it('spatialises the preamble blips at the attacker azimuth (right=beyond, left=behind)', () => {
    expect(preambleBlipAzimuth(geo(100, 98))).toBeGreaterThan(0)
    expect(preambleBlipAzimuth(geo(95, 98))).toBeLessThan(0)
  })
})

describe('Plomp-Levelt margin chord', () => {
  it('a knife-edge margin is rough (small detuning inside the critical band)', () => {
    const c = marginChord(0.0)
    expect(c.rough).toBe(true)
    expect(c.deltaHz).toBeLessThan(100) // inside the ~100 Hz Bark critical band near 500 Hz
  })

  it('a clear margin is consonant (detuning widens past a critical band)', () => {
    const c = marginChord(2.0)
    expect(c.rough).toBe(false)
    expect(c.deltaHz).toBeGreaterThan(100)
  })

  it('the sign of the margin puts the partner tone above (offside) or below (onside)', () => {
    expect(marginChord(1.5).partnerHz).toBeGreaterThan(500) // offside
    expect(marginChord(-1.5).partnerHz).toBeLessThan(500) // onside
  })
})

describe('HRTF spatial scan of the freeze-frame', () => {
  const scanGeo = {
    attacker_x: 100,
    offside_line_x: 98,
    is_offside: true,
    players: [
      { x: 50, y: 40, teammate: true, actor: true },
      { x: 100, y: 20, teammate: true }, // attacker, left
      { x: 98, y: 60, teammate: false }, // defender, right
      { x: 96, y: 30, teammate: false }, // defender, left-ish
      { x: 119, y: 40, teammate: false, keeper: true }, // keeper excluded from the line tone set
    ],
  } as unknown as Parameters<typeof spatialScanPlan>[0]

  it('lateral position maps to a front-hemisphere azimuth', () => {
    expect(lateralAzimuth(40)).toBe(0) // centre
    expect(lateralAzimuth(0)).toBeLessThan(0) // far left
    expect(lateralAzimuth(80)).toBeGreaterThan(0) // far right
  })

  it('scans defenders then attackers then the centred offside line, on the Brewster onset grid', () => {
    const plan = spatialScanPlan(scanGeo)
    const roles = plan.map((v) => v.role)
    expect(roles.slice(0, 2)).toEqual(['defender', 'defender'])
    expect(roles).toContain('attacker')
    expect(plan[plan.length - 1].role).toBe('line')
    expect(plan[plan.length - 1].azimuthDeg).toBe(0) // the line is centred
    // onsets are separated by Brewster's 300 ms gap
    expect(plan[1].onsetMs - plan[0].onsetMs).toBe(BREWSTER.onsetGapMs)
    // the keeper is not pinged as an outfield defender
    expect(plan.filter((v) => v.role === 'defender').length).toBe(2)
  })
})

describe('confidenceVoice: the timbre carries the confidence', () => {
  it('adds vibrato and inharmonicity as the call gets tighter', () => {
    const clear = confidenceVoice('clear')
    const tight = confidenceVoice('tight')
    const veryTight = confidenceVoice('very tight')
    // a clear call is a pure, steady tone; a knife-edge call wavers and grows inharmonic
    expect(clear.vibratoCents).toBe(0)
    expect(clear.inharmonicity).toBe(0)
    expect(tight.vibratoCents).toBeGreaterThan(clear.vibratoCents)
    expect(veryTight.vibratoCents).toBeGreaterThan(tight.vibratoCents)
    expect(veryTight.inharmonicity).toBeGreaterThan(tight.inharmonicity)
  })

  it('carries the base earcon fields through unchanged', () => {
    const v = confidenceVoice('clear')
    const e = confidenceEarcon('clear')
    expect(v.loudnessScale).toBe(e.loudnessScale)
    expect(v.noiseMix).toBe(e.noiseMix)
  })
})

describe('iso226Gain: ISO 226:2003 equal-loudness normalization', () => {
  it('is unity at 1 kHz (the contour anchor)', () => {
    // the 60-phon contour passes through 60 dB SPL at 1 kHz by definition
    expect(iso226Spl(1000, 60)).toBeCloseTo(60, 0)
    expect(iso226Gain(1000, 60)).toBeCloseTo(1, 2)
  })

  it('boosts a low frequency the ear is insensitive to', () => {
    // at ~125 Hz the ear is far less sensitive, so the tone needs more amplitude to match
    expect(iso226Gain(125)).toBeGreaterThan(1)
  })

  it('cuts the ~3-4 kHz band the ear is most sensitive to', () => {
    // the 60-phon contour dips below 60 dB near 3.5 kHz, so the gain there is < 1
    expect(iso226Gain(3500)).toBeLessThan(1)
  })

  it('stays inside its clamp for the whole audible range', () => {
    for (const f of [20, 200, 1000, 4000, 12500]) {
      const g = iso226Gain(f)
      expect(g).toBeGreaterThanOrEqual(0.25)
      expect(g).toBeLessThanOrEqual(4)
    }
  })
})
