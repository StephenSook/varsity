import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

// Decorative broadcast-style 3D pitch behind the hero: a dark field, two teams of
// player markers, and a glowing signal-green offside line that pulses, the whole
// scene rotating slowly. Purely atmospheric: the canvas is aria-hidden and is only
// mounted when the user has NOT requested reduced motion.

const NAVY = '#0a0f1c'
const GREEN = '#34d399'

// Scattered players: teammate (sky) vs opponent (slate), on a 16x10 pitch.
const PLAYERS: { x: number; z: number; team: 'a' | 'b' }[] = [
  { x: -5.5, z: -1.2, team: 'a' },
  { x: -3.1, z: 2.4, team: 'a' },
  { x: -1.4, z: -3.0, team: 'a' },
  { x: 1.2, z: 1.1, team: 'a' },
  { x: 3.6, z: 3.2, team: 'a' },
  { x: -4.2, z: 3.3, team: 'b' },
  { x: -2.0, z: -1.6, team: 'b' },
  { x: 0.4, z: -2.7, team: 'b' },
  { x: 2.8, z: -0.4, team: 'b' },
  { x: 4.7, z: 2.0, team: 'b' },
]

const OFFSIDE_LINE_X = 3.6 // aligns with the most advanced attacker

function Pitch() {
  const group = useRef<THREE.Group>(null)
  const lineMat = useRef<THREE.MeshStandardMaterial>(null)

  useFrame((state) => {
    const t = state.clock.elapsedTime
    if (group.current) group.current.rotation.y = Math.sin(t * 0.08) * 0.35
    if (lineMat.current) lineMat.current.emissiveIntensity = 1.4 + Math.sin(t * 1.6) * 0.6
  })

  return (
    <group ref={group}>
      {/* field */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.05, 0]} receiveShadow>
        <planeGeometry args={[18, 11]} />
        <meshStandardMaterial color="#0c182a" metalness={0.1} roughness={0.85} />
      </mesh>

      {/* halfway + box markings as thin emissive strips */}
      {[-9, -3, 3, 9].map((x) => (
        <mesh key={x} rotation={[-Math.PI / 2, 0, 0]} position={[x, -0.04, 0]}>
          <planeGeometry args={[0.05, 11]} />
          <meshStandardMaterial color={GREEN} emissive={GREEN} emissiveIntensity={0.25} />
        </mesh>
      ))}

      {/* players */}
      {PLAYERS.map((p, i) => (
        <mesh key={i} position={[p.x, 0.35, p.z]} castShadow>
          <cylinderGeometry args={[0.28, 0.28, 0.7, 16]} />
          <meshStandardMaterial
            color={p.team === 'a' ? '#38bdf8' : '#e2e8f0'}
            emissive={p.team === 'a' ? '#0ea5e9' : '#0f172a'}
            emissiveIntensity={0.3}
            metalness={0.2}
            roughness={0.5}
          />
        </mesh>
      ))}

      {/* glowing offside line: a vertical plane across the pitch */}
      <mesh position={[OFFSIDE_LINE_X, 0.9, 0]}>
        <planeGeometry args={[0.12, 2.4]} />
        <meshStandardMaterial
          ref={lineMat}
          color={GREEN}
          emissive={GREEN}
          emissiveIntensity={1.6}
          transparent
          opacity={0.92}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  )
}

export default function Hero3D() {
  return (
    <Canvas
      aria-hidden="true"
      gl={{ antialias: true, alpha: false }}
      camera={{ position: [0, 6.5, 10], fov: 42 }}
      dpr={[1, 1.8]}
      onCreated={({ scene }) => {
        scene.fog = new THREE.Fog(NAVY, 13, 30)
        scene.background = new THREE.Color(NAVY)
      }}
    >
      <ambientLight intensity={0.35} />
      <pointLight position={[6, 9, 6]} intensity={120} color="#a7f3d0" distance={40} decay={1.6} />
      <pointLight position={[-8, 5, -4]} intensity={60} color="#38bdf8" distance={40} decay={1.8} />
      <Pitch />
    </Canvas>
  )
}
