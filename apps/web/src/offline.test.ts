import { afterEach, describe, expect, it } from 'vitest'
import { getOfflineTier, setOfflineTier } from './offline'

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
