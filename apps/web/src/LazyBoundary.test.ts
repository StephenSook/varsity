import { describe, expect, it } from 'vitest'
import { LazyBoundary } from './LazyBoundary'

// The boundary exists so a code-split chunk that 404s after a deploy degrades to a fallback
// instead of throwing past Suspense to the React root and blanking the whole page. We test the
// error-boundary contract directly (no DOM renderer needed): getDerivedStateFromError flips the
// state, and render() returns the fallback only once failed. This locks the behavior in CI; the
// live blank-on-stale-chunk regression cannot return without failing here.
describe('LazyBoundary', () => {
  it('flips to the failed state when a child throws', () => {
    expect(LazyBoundary.getDerivedStateFromError()).toEqual({ failed: true })
  })

  it('renders children while healthy', () => {
    const b = new LazyBoundary({ fallback: 'FALLBACK', children: 'CHILDREN' })
    b.state = { failed: false }
    expect(b.render()).toBe('CHILDREN')
  })

  it('renders the fallback after a failure', () => {
    const b = new LazyBoundary({ fallback: 'FALLBACK', children: 'CHILDREN' })
    b.state = { failed: true }
    expect(b.render()).toBe('FALLBACK')
  })
})
