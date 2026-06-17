import { describe, it, expect } from 'vitest'
import { CHROME, LANGS } from './i18n'

// The "What this explanation cannot see" disclosure: a static, honest data-limits
// statement shown in the Detail panel (screen-reader reachable) for every language.
// It complements the per-call confidence band (uncertainty.py) with the constant
// limits of the data source, mirroring the field's strongest honesty posture.
describe('CHROME limits disclosure (what this explanation cannot see)', () => {
  it('every language has a heading and at least three concrete items', () => {
    for (const lang of LANGS) {
      const limits = CHROME[lang].limits
      expect(limits, `${lang} has limits`).toBeTruthy()
      expect(limits.heading.trim().length, `${lang} heading`).toBeGreaterThan(0)
      expect(limits.items.length, `${lang} item count`).toBeGreaterThanOrEqual(3)
      for (const item of limits.items) {
        expect(item.trim().length, `${lang} item non-empty`).toBeGreaterThan(0)
      }
    }
  })

  it('is genuinely localized, not English copied across languages', () => {
    expect(CHROME.English.limits.heading).not.toEqual(CHROME.Spanish.limits.heading)
    expect(CHROME.English.limits.heading).not.toEqual(CHROME.French.limits.heading)
    expect(CHROME.English.limits.items[0]).not.toEqual(CHROME.German.limits.items[0])
  })
})
