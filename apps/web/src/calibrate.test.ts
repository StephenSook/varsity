import { describe, expect, it } from 'vitest'

import { clampLineX, whatIfMarginMeters } from './calibrate'

describe('whatIfMarginMeters', () => {
  it('matches the backend canned WC2022 margin when the line is not moved', () => {
    // services/app/geometry.py over the real frame: attacker 72.20, line 65.98 -> 5.69 m.
    // If this drifts from GET /scenarios' offside margin, one of the two formulas changed.
    expect(whatIfMarginMeters(72.2, 65.98)).toBe(5.69)
  })

  it('is signed: behind the moved line is negative (the onside side)', () => {
    expect(whatIfMarginMeters(60, 65.98)).toBeLessThan(0)
  })

  it('reads 0.00 for a level attacker', () => {
    expect(whatIfMarginMeters(65.98, 65.98)).toBe(0)
  })

  it('converts with the international yard, not a 105 m pitch normalization', () => {
    expect(whatIfMarginMeters(1, 0)).toBe(0.91)
  })
})

describe('clampLineX', () => {
  it('clamps the line to the pitch', () => {
    expect(clampLineX(-3, 120)).toBe(0)
    expect(clampLineX(130.2, 120)).toBe(120)
    expect(clampLineX(60, 120)).toBe(60)
  })
})
