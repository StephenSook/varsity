import { describe, expect, it } from 'vitest'
import { recognitionLang } from './voice'

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
