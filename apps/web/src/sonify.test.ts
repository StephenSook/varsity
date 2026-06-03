import { describe, expect, it } from 'vitest'

import {
  MAX_AZIMUTH_DEG,
  confidenceEarcon,
  confidenceTexture,
  lineProximityPreamble,
  lineSweepSpec,
  marginToNormalized,
  pitchToAzimuth,
  preambleBlipAzimuth,
  sonificationPlan,
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
