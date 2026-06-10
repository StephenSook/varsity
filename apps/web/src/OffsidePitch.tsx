export type Player = {
  x: number
  y: number
  teammate: boolean
  actor?: boolean
  keeper?: boolean
}

export type Geometry = {
  players: Player[]
  offside_line_x: number
  attacker_x: number
  margin_meters: number
  is_offside: boolean
  confidence?: string
  pitch: { length: number; width: number }
}

/**
 * Top-down broadcast-style pitch. The offside line (the second-to-last defender)
 * sweeps in when motion is allowed and simply appears under prefers-reduced-motion.
 * The margin label is bound to the streamed geometry value, never hardcoded. The
 * whole SVG is decorative (aria-hidden); the screen reader speaks via aria-live.
 */
export function OffsidePitch({ geo, whatIfX }: { geo: Geometry; whatIfX?: number | null }) {
  const L = geo.pitch.length
  const W = geo.pitch.width
  const lineX = geo.offside_line_x
  const attX = geo.attacker_x
  const attacker = geo.players.find(
    (p) => p.teammate && !p.actor && Math.abs(p.x - attX) < 0.01,
  )
  const bracketY = attacker ? attacker.y : W / 2
  const labelX = Math.min(Math.max((lineX + attX) / 2, 12), L - 12)

  return (
    <svg
      viewBox={`0 0 ${L} ${W}`}
      role="presentation"
      aria-hidden="true"
      className="w-full rounded-lg bg-emerald-950/50 ring-1 ring-emerald-500/20"
    >
      {/* pitch markings */}
      <rect x={0.5} y={0.5} width={L - 1} height={W - 1} fill="none" stroke="rgba(16,185,129,0.25)" strokeWidth={0.4} />
      <line x1={L / 2} y1={0} x2={L / 2} y2={W} stroke="rgba(16,185,129,0.18)" strokeWidth={0.3} />
      <rect x={L - 18} y={W / 2 - 20} width={18} height={40} fill="none" stroke="rgba(16,185,129,0.18)" strokeWidth={0.3} />
      <rect x={L - 7} y={W / 2 - 11} width={7} height={22} fill="none" stroke="rgba(16,185,129,0.18)" strokeWidth={0.3} />

      {/* offside line at the second-to-last defender (sweeps in) */}
      <line x1={lineX} y1={0} x2={lineX} y2={W} stroke="rgb(52,211,153)" strokeWidth={0.7} className="offside-line" />

      {/* what-if calibrator line: dashed, amber, only while the user has moved it. The real
          line above never moves; the calibrator readout lives outside this aria-hidden SVG. */}
      {typeof whatIfX === 'number' && (
        <line
          x1={whatIfX}
          y1={0}
          x2={whatIfX}
          y2={W}
          stroke="rgb(251,191,36)"
          strokeWidth={0.5}
          strokeDasharray="2 1.4"
          data-testid="whatif-line"
        />
      )}

      {/* margin bracket + label, bound to the computed value */}
      <line x1={lineX} y1={bracketY} x2={attX} y2={bracketY} stroke="rgb(250,204,21)" strokeWidth={0.5} />
      <line x1={lineX} y1={bracketY - 1.5} x2={lineX} y2={bracketY + 1.5} stroke="rgb(250,204,21)" strokeWidth={0.5} />
      <line x1={attX} y1={bracketY - 1.5} x2={attX} y2={bracketY + 1.5} stroke="rgb(250,204,21)" strokeWidth={0.5} />
      <text
        x={labelX}
        y={bracketY - 2.5}
        fontSize={3.4}
        textAnchor="middle"
        fill="rgb(250,204,21)"
        data-testid="margin-label"
      >
        {geo.margin_meters.toFixed(2)} m
      </text>

      {/* players: attackers sky, defenders slate, keeper amber, actor ringed */}
      {geo.players.map((p, i) => (
        <circle
          key={i}
          cx={p.x}
          cy={p.y}
          r={p.actor ? 1.7 : 1.4}
          fill={p.teammate ? 'rgb(56,189,248)' : p.keeper ? 'rgb(251,146,60)' : 'rgb(226,232,240)'}
          stroke={p.actor ? 'rgb(250,204,21)' : 'rgba(2,6,23,0.6)'}
          strokeWidth={0.3}
        />
      ))}
    </svg>
  )
}
