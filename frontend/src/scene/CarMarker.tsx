import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'
import { ROAD_CURVE } from './Road'

interface CarMarkerProps {
  progress: number
}

export function CarMarker({ progress }: CarMarkerProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const lightRef = useRef<THREE.PointLight>(null)
  const targetProgress = useRef(progress / 100)

  useFrame((_, delta) => {
    const target = progress / 100
    targetProgress.current = THREE.MathUtils.lerp(
      targetProgress.current,
      target,
      1 - Math.pow(0.01, delta),
    )

    const t = Math.min(Math.max(targetProgress.current, 0), 0.999)
    const pos = ROAD_CURVE.getPointAt(t)
    const tangent = ROAD_CURVE.getTangentAt(t)

    if (meshRef.current) {
      meshRef.current.position.copy(pos)
      meshRef.current.lookAt(pos.clone().add(tangent))
    }
    if (lightRef.current) {
      lightRef.current.position.copy(pos)
    }
  })

  return (
    <group>
      <mesh ref={meshRef}>
        <boxGeometry args={[0.08, 0.04, 0.15]} />
        <meshStandardMaterial
          color="#c8102e"
          emissive="#c8102e"
          emissiveIntensity={0.6}
          roughness={0.3}
          metalness={0.8}
        />
      </mesh>
      <pointLight
        ref={lightRef}
        intensity={0.4}
        color="#c8102e"
        distance={3}
      />
    </group>
  )
}
