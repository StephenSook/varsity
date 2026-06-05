import { afterEach, describe, expect, it } from 'vitest'
import {
  computeOffsideLocal,
  deterministicExplanation,
  getOfflineTier,
  setOfflineTier,
} from './offline'

describe('on-device model tier', () => {
  afterEach(() => setOfflineTier('nano'))

  it('defaults to the light Granite Nano tier (no forced heavy download)', () => {
    expect(getOfflineTier()).toBe('nano')
  })

  it('opts into the high-accuracy Granite 4.0 1B tier on request', () => {
    setOfflineTier('granite-1b')
    expect(getOfflineTier()).toBe('granite-1b')
    setOfflineTier('nano')
    expect(getOfflineTier()).toBe('nano')
  })
})

describe('offline deterministic floor (the geometry + text that run with no WebGPU)', () => {
  it('computes the canned frame as offside with a positive margin', () => {
    const geo = computeOffsideLocal()
    expect(geo.is_offside).toBe(true)
    expect(geo.margin_meters).toBeGreaterThan(0)
    expect(geo.attacker_x).toBeGreaterThan(geo.offside_line_x)
    // Pin the yards-to-meters factor (0.9144): the canned offline frame must speak the same
    // 5.69 m the online geometry does, so the conversion can never silently drift back to 0.875.
    expect(geo.margin_meters).toBe(5.69)
  })

  it('explains an offside geo grounded in Law 11', () => {
    const text = deterministicExplanation(computeOffsideLocal())
    expect(text).toMatch(/Law 11/)
    expect(text.toLowerCase()).toContain('offside')
  })

  it('flips the wording to legal for an onside geo, and never speaks a minus sign', () => {
    const onside = { ...computeOffsideLocal(), is_offside: false, margin_meters: -3.01 }
    const text = deterministicExplanation(onside)
    expect(text.toLowerCase()).toContain('legal')
    expect(text).toMatch(/3\.01/)
    expect(text).not.toMatch(/-3\.01/)
  })
})
