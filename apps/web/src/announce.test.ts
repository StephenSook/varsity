import { describe, expect, it } from 'vitest'
import { announceText } from './announce'

describe('announceText (the exact spoken verdict a blind fan hears)', () => {
  const offside = { text: 'The attacker was offside, grounded in Law 11.', isOffside: true, marginM: 5.69 }
  const onside = { text: 'The attacker was onside.', isOffside: false, marginM: -3.01 }

  it('minimal speaks the offside headline with the abs, 2dp margin', () => {
    expect(announceText('minimal', offside)).toBe('Offside, by 5.69 metres.')
  })

  it('minimal speaks a bare Onside without a margin', () => {
    expect(announceText('minimal', onside)).toBe('Onside.')
  })

  it('does not invert the offside/onside polarity', () => {
    expect(announceText('minimal', offside)).toMatch(/^Offside/)
    expect(announceText('minimal', onside)).toBe('Onside.')
  })

  it('standard returns the full explanation verbatim', () => {
    expect(announceText('standard', offside)).toBe(offside.text)
  })

  it('coach appends the confidence band when present, else just the text', () => {
    expect(announceText('coach', { ...offside, confidence: 'clear' })).toBe(
      'The attacker was offside, grounded in Law 11. How clear-cut: clear.',
    )
    expect(announceText('coach', offside)).toBe(offside.text)
  })

  it('abs() and 2dp the margin so a negative or noisy value never speaks a minus sign', () => {
    expect(announceText('minimal', { text: '', isOffside: true, marginM: -0.123 })).toBe(
      'Offside, by 0.12 metres.',
    )
  })
})
