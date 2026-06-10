import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import type { Geometry } from './OffsidePitch'

// A broadcast-style 3D rendering of the SAME offside geometry the SVG shows: the real
// freeze-frame players, the computed offside line at the second-to-last defender, and
// the attacker's margin, in a slowly orbiting 3D scene. Purely decorative: the canvas
// is aria-hidden and only mounted when motion is allowed; the SVG is the reduced-motion
// fallback and the screen reader speaks via the aria-live region either way.
//
// Renderer: WebGL (the default R3F renderer). A WebGPURenderer was considered but WebGL
// is visually identical for a ten-player scene, works in every judge's browser, and
// carries no async-init / Safari-support / build risk.

const NAVY = '#0a0f1c'
const GREEN = '#34d399'
const S = 1 / 8 // pitch units (120x80) -> world units (15x10)

function world(x: number, y: number): [number, number] {
  return [(x - 60) * S, (y - 40) * S]
}

function Scene({ geo, whatIfX }: { geo: Geometry; whatIfX?: number | null }) {
  const group = useRef<THREE.Group>(null)
  const lineMat = useRef<THREE.MeshStandardMaterial>(null)

  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (group.current) group.current.rotation.y = Math.sin(t * 0.1) * 0.4
    if (lineMat.current) lineMat.current.emissiveIntensity = 1.5 + Math.sin(t * 1.8) * 0.7
  })

  const [lineX] = world(geo.offside_line_x, 40)
  const [attX] = world(geo.attacker_x, 40)
  const lineColor = geo.is_offside ? GREEN : '#fbbf24'

  return (
    <group ref={group}>
      {/* field */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
        <planeGeometry args={[15.5, 10.5]} />
        <meshStandardMaterial color="#0c182a" metalness={0.1} roughness={0.85} />
      </mesh>

      {/* halfway line + the attacking penalty box (right end) */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.04, 0]}>
        <planeGeometry args={[0.04, 10]} />
        <meshStandardMaterial color={GREEN} emissive={GREEN} emissiveIntensity={0.2} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[5.6, -0.04, 0]}>
        <planeGeometry args={[2.2, 5]} />
        <meshStandardMaterial color={GREEN} emissive={GREEN} emissiveIntensity={0.08} wireframe />
      </mesh>

      {/* players: attacker sky, defender slate, keeper amber; the actor is taller + ringed */}
      {geo.players.map((p, i) => {
        const [px, pz] = world(p.x, p.y)
        const color = p.teammate ? '#38bdf8' : p.keeper ? '#fb923c' : '#e2e8f0'
        const h = p.actor ? 1.0 : 0.7
        return (
          <mesh key={i} position={[px, h / 2, pz]} castShadow>
            <cylinderGeometry args={[p.actor ? 0.32 : 0.26, 0.26, h, 18]} />
            <meshStandardMaterial
              color={color}
              emissive={p.teammate ? '#0ea5e9' : '#0f172a'}
              emissiveIntensity={p.actor ? 0.5 : 0.3}
              metalness={0.2}
              roughness={0.5}
            />
          </mesh>
        )
      })}

      {/* the offside line: a glowing vertical plane across the pitch at the 2nd-last defender */}
      <mesh position={[lineX, 0.8, 0]}>
        <planeGeometry args={[0.1, 2.2]} />
        <meshStandardMaterial
          ref={lineMat}
          color={lineColor}
          emissive={lineColor}
          emissiveIntensity={1.6}
          transparent
          opacity={0.92}
          side={THREE.DoubleSide}
        />
      </mesh>
      {/* the what-if calibrator line: static amber SEGMENTS (the 3D read of the 2D dashed
          line), only while the user has moved it. The real line above stays solid and
          pulsing, so the two are distinguishable even when both render amber (onside). */}
      {typeof whatIfX === 'number' &&
        [0.25, 0.8, 1.35, 1.9].map((y) => (
          <mesh key={y} position={[world(whatIfX, 40)[0], y, 0]}>
            <planeGeometry args={[0.07, 0.4]} />
            <meshStandardMaterial
              color="#fbbf24"
              emissive="#fbbf24"
              emissiveIntensity={1.1}
              transparent
              opacity={0.85}
              side={THREE.DoubleSide}
            />
          </mesh>
        ))}

      {/* the attacker's line + the margin gap between them */}
      <mesh position={[attX, 0.55, 0]}>
        <planeGeometry args={[0.06, 1.5]} />
        <meshStandardMaterial color="#fde68a" emissive="#fde68a" emissiveIntensity={0.9} transparent opacity={0.8} side={THREE.DoubleSide} />
      </mesh>
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[(lineX + attX) / 2, -0.03, 0]}>
        <planeGeometry args={[Math.abs(attX - lineX), 0.5]} />
        <meshStandardMaterial color="#facc15" emissive="#facc15" emissiveIntensity={0.5} transparent opacity={0.5} />
      </mesh>
    </group>
  )
}

export default function OffsidePitch3D({
  geo,
  whatIfX,
}: {
  geo: Geometry
  whatIfX?: number | null
}) {
  return (
    <Canvas
      aria-hidden="true"
      gl={{ antialias: true, alpha: false }}
      camera={{ position: [2, 7, 9], fov: 40 }}
      dpr={[1, 1.8]}
      style={{ width: '100%', aspectRatio: '16 / 9' }}
      onCreated={({ scene, camera }) => {
        scene.fog = new THREE.Fog(NAVY, 12, 28)
        scene.background = new THREE.Color('#06101e')
        camera.lookAt(0, 0, 0)
      }}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[5, 9, 5]} intensity={120} color="#a7f3d0" distance={40} decay={1.6} />
      <pointLight position={[-7, 5, -4]} intensity={55} color="#38bdf8" distance={40} decay={1.8} />
      <Scene geo={geo} whatIfX={whatIfX} />
    </Canvas>
  )
}
