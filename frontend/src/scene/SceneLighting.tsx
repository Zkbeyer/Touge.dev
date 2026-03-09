export function SceneLighting() {
  return (
    <>
      <ambientLight intensity={0.5} color="#fff8f0" />
      <directionalLight intensity={1.2} position={[5, 8, -3]} color="#c8d8ff" />
      <directionalLight intensity={0.4} position={[-4, 3, 6]} color="#ffe8c0" />
    </>
  )
}
