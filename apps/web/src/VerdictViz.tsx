import { useEffect, useRef } from 'react'

// A decorative spectrum visualization of the verdict earcon, for sighted co-viewers. It is purely
// ornamental: aria-hidden (it conveys no information a screen reader needs, the spoken verdict and
// the earcon carry that) and gated behind prefers-reduced-motion. It taps the REAL audio via the
// shared output-bus AnalyserNode, so the bars move with the actual chord, not a fake animation.
export function VerdictViz({
  getAnalyser,
  active,
}: {
  getAnalyser: () => AnalyserNode | null
  active: boolean
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)

  useEffect(() => {
    if (!active) return
    const reduce =
      typeof window !== 'undefined' &&
      (window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches ?? false)
    if (reduce) return
    const canvas = canvasRef.current
    const an = getAnalyser()
    if (!canvas || !an) return
    const cctx = canvas.getContext('2d')
    if (!cctx) return
    const data = new Uint8Array(an.frequencyBinCount)
    let raf = 0
    const draw = () => {
      an.getByteFrequencyData(data)
      const { width, height } = canvas
      cctx.clearRect(0, 0, width, height)
      const barW = width / data.length
      for (let i = 0; i < data.length; i++) {
        const v = data[i] / 255
        const h = v * height
        cctx.fillStyle = `rgba(52, 211, 153, ${0.2 + v * 0.6})` // signal green
        cctx.fillRect(i * barW, height - h, barW * 0.8, h)
      }
      raf = requestAnimationFrame(draw)
    }
    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [active, getAnalyser])

  return (
    <canvas
      ref={canvasRef}
      width={320}
      height={48}
      aria-hidden="true"
      className="h-12 w-full max-w-xs rounded-md bg-slate-900/40 ring-1 ring-slate-700/40"
    />
  )
}
