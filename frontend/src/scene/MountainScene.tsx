import { Canvas } from '@react-three/fiber'
import { Road } from './Road'
import { Terrain } from './Terrain'
import { CarMarker } from './CarMarker'
import { Particles } from './Particles'
import { SceneLighting } from './SceneLighting'

interface MountainSceneProps {
  progress: number
}

export function MountainScene({ progress }: MountainSceneProps) {
  return (
    <Canvas
      style={{ width: '100%', height: '100%', background: '#0d0c12' }}
      camera={{ position: [4, 2, 10], fov: 45 }}
      dpr={[1, 2]}
    >
      <fog attach="fog" args={['#0d0c12', 8, 28]} />
      <SceneLighting />
      <Terrain />
      <Road />
      <CarMarker progress={progress} />
      <Particles />
    </Canvas>
  )
}
