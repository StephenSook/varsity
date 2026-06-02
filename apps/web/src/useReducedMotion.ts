import { useEffect, useState } from 'react'

/**
 * True when the user prefers reduced motion. All decorative motion and the 3D
 * hero are gated on this being false (WCAG 2.3.3 Animation from Interactions).
 */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(true) // safe default: assume reduced until known
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const update = () => setReduced(mq.matches)
    update()
    mq.addEventListener('change', update)
    return () => mq.removeEventListener('change', update)
  }, [])
  return reduced
}
