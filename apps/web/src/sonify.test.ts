import { describe, expect, it } from 'vitest'

import {
  confidenceTexture,
  lineProximityPreamble,
  lineSweepSpec,
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

describe('spatial sonification plan', () => {
  it('centres the defender line and pans the attacker by the real margin', () => {
    const plan = sonificationPlan(geo(100, 98)) // ~1.75 m beyond the line
    const defender = plan.find((v) => v.role === 'defender')!
    const attacker = plan.find((v) => v.role === 'attacker')!
    expect(defender.x).toBe(0)
    expect(attacker.x).toBeGreaterThan(0) // beyond the line -> panned to the right
  })

  it('pans an onside attacker to the left of the line', () => {
    const plan = sonificationPlan(geo(95, 98))
    const attacker = plan.find((v) => v.role === 'attacker')!
    expect(attacker.x).toBeLessThan(0)
  })
})
