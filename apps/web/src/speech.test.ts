import { describe, expect, it } from 'vitest'
import { verbalizeForSpeech } from './speech'

describe('verbalizeForSpeech', () => {
  it('speaks an English decimal margin digit-by-digit with the unit in full', () => {
    const out = verbalizeForSpeech('The attacker was offside by 5.69 metres.', 'en')
    expect(out).toContain('five point six nine metres')
    expect(out).not.toContain('5.69')
  })

  it('expands a bare abbreviation (m, cm) to the spoken unit word', () => {
    expect(verbalizeForSpeech('5.69 m', 'en')).toBe('five point six nine metres')
    expect(verbalizeForSpeech('13 cm of noise', 'en')).toBe('thirteen centimetres of noise')
  })

  it('handles a leading-zero decimal', () => {
    expect(verbalizeForSpeech('0.02 m', 'en-GB')).toBe('zero point zero two metres')
  })

  it('leaves a bare number (a Law citation) untouched', () => {
    expect(verbalizeForSpeech('Under Law 11.1, offside.', 'en')).toBe('Under Law 11.1, offside.')
  })

  it('verbalizes per language with the right point word and unit', () => {
    expect(verbalizeForSpeech('5.69 m', 'es')).toContain('cinco coma seis nueve metros')
    expect(verbalizeForSpeech('5,69 m', 'pt')).toContain('cinco vírgula seis nove metros')
    expect(verbalizeForSpeech('5 mètres', 'fr')).toBe('cinq mètres')
    expect(verbalizeForSpeech('13 cm', 'de')).toBe('dreizehn Zentimeter')
  })

  it('is idempotent (re-running on verbalized text changes nothing)', () => {
    const once = verbalizeForSpeech('offside by 5.69 m', 'en')
    expect(verbalizeForSpeech(once, 'en')).toBe(once)
  })
})
