import { afterEach, describe, expect, it, vi } from 'vitest'
import { graniteSpeechEnabled, recognitionLang } from './voice'

describe('voice recognitionLang', () => {
  it('maps each narration BCP-47 code to the ASR language name', () => {
    expect(recognitionLang('en')).toBe('english')
    expect(recognitionLang('es')).toBe('spanish')
    expect(recognitionLang('fr')).toBe('french')
    expect(recognitionLang('pt')).toBe('portuguese')
    expect(recognitionLang('de')).toBe('german')
  })

  it('tolerates a full BCP-47 tag and defaults to English for the unknown', () => {
    expect(recognitionLang('es-ES')).toBe('spanish')
    expect(recognitionLang('pt-BR')).toBe('portuguese')
    expect(recognitionLang('zz')).toBe('english')
  })
})

describe('graniteSpeechEnabled: the all-IBM voice opt-in (off by default)', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('is off when neither the flag nor the query param is set', () => {
    vi.stubGlobal('window', { location: { search: '' }, localStorage: { getItem: () => null } })
    expect(graniteSpeechEnabled()).toBe(false)
  })
  it('is on via the localStorage flag', () => {
    vi.stubGlobal('window', {
      location: { search: '' },
      localStorage: { getItem: (k: string) => (k === 'varsity-granite-speech' ? '1' : null) },
    })
    expect(graniteSpeechEnabled()).toBe(true)
  })
  it('is on via the query param', () => {
    vi.stubGlobal('window', { location: { search: '?graniteSpeech=1' }, localStorage: { getItem: () => null } })
    expect(graniteSpeechEnabled()).toBe(true)
  })
})
