import { afterEach, describe, expect, it } from 'vitest'
import {
  computeOffsideLocal,
  deterministicExplanation,
  getOfflineTier,
  groundNanoText,
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

describe('groundNanoText (grounds on-device generation in the retrieved Law)', () => {
  const LAW = "## Law 11\n\n## Offside\n\n## 1. Offside position\n\nIt is not an offence to be in an offside position."

  it('passes through output that already cites the Law', () => {
    const cited = 'Under Law 11, the attacker was ahead of the second-to-last defender.'
    expect(groundNanoText(cited, LAW)).toBe(cited)
  })

  it('prefixes the retrieval-sourced Law id when the model omits the citation (the real captured Nano output)', () => {
    // Verbatim Granite Nano 350m output captured live 2026-06-11: correct explanation,
    // no Law citation. The old guard rejected it and the Nano tier never surfaced.
    const raw =
      'Offside decision: The most advanced attacker was 5.69 meters ahead of the ' +
      'second-to-last defender when the ball was played. Verdict: Offside.'
    expect(groundNanoText(raw, LAW)).toBe(`Under Law 11: ${raw}`)
  })

  it('rejects empty or too-short output so the caller falls to the deterministic floor', () => {
    expect(groundNanoText(undefined, LAW)).toBeNull()
    expect(groundNanoText('', LAW)).toBeNull()
    expect(groundNanoText('Offside.', LAW)).toBeNull()
  })

  it('rejects uncited output when the retrieved text has no Law id to ground with', () => {
    const raw = 'The attacker was clearly ahead of the second-to-last defender at the pass.'
    expect(groundNanoText(raw, 'Some retrieved text without a law number.')).toBeNull()
  })

  it('grounded output always satisfies the cite-a-Law guardrail', () => {
    const raw = 'The attacker was clearly ahead of the second-to-last defender at the pass.'
    const text = groundNanoText(raw, LAW)
    expect(text).not.toBeNull()
    expect(text!).toMatch(/law/i)
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
