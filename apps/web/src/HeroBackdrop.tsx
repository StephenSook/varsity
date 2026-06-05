/**
 * Static, motion-free hero backdrop for prefers-reduced-motion (and any browser where the
 * lazy WebGL Hero3D never mounts). Instead of a blank navy panel, a reduced-motion user
 * still sees the product's core image: a perspective pitch with a glowing offside line and
 * an attacker just beyond it. Pure SVG, no animation, no dependencies. Decorative only:
 * aria-hidden, pointer-events-none, low opacity so the hero text keeps AA contrast.
 */
export function HeroBackdrop() {
  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
      <svg
        className="absolute left-1/2 top-1/2 h-[120%] w-[120%] -translate-x-1/2 -translate-y-1/2 opacity-30"
        viewBox="0 0 1200 800"
        preserveAspectRatio="xMidYMid slice"
        role="presentation"
      >
        <defs>
          <linearGradient id="hb-grass" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#0a0f1c" />
            <stop offset="1" stopColor="#0d1b2a" />
          </linearGradient>
          <linearGradient id="hb-line" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#34d399" stopOpacity="0" />
            <stop offset="0.5" stopColor="#34d399" stopOpacity="0.9" />
            <stop offset="1" stopColor="#34d399" stopOpacity="0" />
          </linearGradient>
        </defs>
        <rect width="1200" height="800" fill="url(#hb-grass)" />
        {/* Perspective pitch: receding halfway-style lines converging toward the horizon. */}
        <g stroke="#1e3a5f" strokeWidth="1.5" fill="none">
          <line x1="120" y1="800" x2="470" y2="300" />
          <line x1="1080" y1="800" x2="730" y2="300" />
          <line x1="0" y1="640" x2="1200" y2="640" />
          <line x1="180" y1="500" x2="1020" y2="500" />
          <line x1="330" y1="390" x2="870" y2="390" />
          <line x1="430" y1="320" x2="770" y2="320" />
        </g>
        {/* The offside line: a glowing vertical signal-green sweep, the broadcast motif. */}
        <rect x="592" y="120" width="6" height="600" fill="url(#hb-line)" />
        {/* Defenders (white) level with the line; one attacker (sky-blue) just beyond it. */}
        <circle cx="540" cy="560" r="9" fill="#e2e8f0" />
        <circle cx="470" cy="470" r="7" fill="#e2e8f0" />
        <circle cx="660" cy="540" r="9" fill="#38bdf8" />
      </svg>
    </div>
  )
}
