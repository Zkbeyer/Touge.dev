import { useMemo } from 'react'
import * as THREE from 'three'

const PLANES = [
  { z: -8, y: -1, rx: -0.3, scale: [12, 6], color: '#13121e' },
  { z: -5, y: -2, rx: -0.2, scale: [10, 4], color: '#17161f' },
  { z: -2, y: -3, rx: -0.15, scale: [8, 3], color: '#1a1720' },
]

export function Terrain() {
  return (
    <group>
      {PLANES.map((p, i) => (
        <mesh
          key={i}
          position={[0, p.y, p.z]}
          rotation={[p.rx, 0, 0]}
        >
          <planeGeometry args={[p.scale[0], p.scale[1], 8, 4]} />
          <meshStandardMaterial
            color={p.color}
            roughness={1}
            metalness={0}
            side={THREE.DoubleSide}
          />
        </mesh>
      ))}
    </group>
  )
}
