import { describe, expect, it } from 'vitest'
import { segmentByScript } from './mixedScript'

describe('segmentByScript: per-run mixed-script lang tagging', () => {
  it('returns a single untagged run for all-Latin text (a no-op for our current content)', () => {
    const runs = segmentByScript('Canada vs Morocco')
    expect(runs).toHaveLength(1)
    expect(runs[0]).toEqual({ text: 'Canada vs Morocco', lang: null })
  })

  it('splits a Latin + Arabic name into a Latin run and an und-Arab run', () => {
    const runs = segmentByScript('Al Nassr النصر')
    expect(runs.map((r) => r.lang)).toEqual([null, 'und-Arab'])
    expect(runs[0].text).toBe('Al Nassr ')
    expect(runs[1].text).toBe('النصر')
  })

  it('tags Cyrillic, Hangul, and Han runs by their script', () => {
    expect(segmentByScript('Россия')[0].lang).toBe('und-Cyrl')
    expect(segmentByScript('대한민국')[0].lang).toBe('und-Hang')
    expect(segmentByScript('中国')[0].lang).toBe('und-Hani')
  })

  it('keeps neutral characters (spaces, digits) inside the surrounding run', () => {
    // a space between two Arabic words must not break the run back to the page language
    const runs = segmentByScript('النصر السعودي')
    expect(runs).toHaveLength(1)
    expect(runs[0].lang).toBe('und-Arab')
  })

  it('falls back to plain und for a non-Latin letter whose script we do not map', () => {
    // Armenian is a real script not in our subtag map; it must still be tagged non-page-language
    const runs = segmentByScript('Հայ')
    expect(runs[0].lang).toBe('und')
  })
})
