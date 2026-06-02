import { useEffect } from 'react'
import Lenis from 'lenis'
import { usePrefersReducedMotion } from './useReducedMotion'

/**
 * Smooth (inertial) scrolling for the cinematic page. Disabled under
 * prefers-reduced-motion so the native scroll is preserved. Keyboard and wheel
 * scrolling still work either way.
 */
export function useLenis() {
  const reduced = usePrefersReducedMotion()
  useEffect(() => {
    if (reduced) return
    const lenis = new Lenis({ duration: 1.1, smoothWheel: true })
    let raf = 0
    const loop = (time: number) => {
      lenis.raf(time)
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => {
      cancelAnimationFrame(raf)
      lenis.destroy()
    }
  }, [reduced])
}
