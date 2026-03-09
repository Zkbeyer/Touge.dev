import { useMemo } from 'react'
import * as THREE from 'three'

/**
 * AKINA DOWNHILL road spline — inspired by the real Haruna mountain pass.
 *
 * The pass descends from the summit (far/high) through 5 famous hairpin turns,
 * each alternating left/right, separated by brief straights and sweepers.
 * The car marker travels from t=0 (summit) to t=1 (mountain foot).
 *
 * Camera sits at [4, 2, 10], fov 45 — the full descent is visible with
 * atmospheric fog rolling in toward the summit.
 *
 * Control point annotation: [x, y, z]
 *   +X = right, +Y = up, +Z = toward camera
 */
export const ROAD_CURVE = new THREE.CatmullRomCurve3(
  [
    // ── Summit approach ──────────────────────────────────────────────────────
    new THREE.Vector3(-1,  6.0, -9.0),  // 00 summit start
    new THREE.Vector3( 0,  5.5, -7.5),  // 01 straight descent

    // ── Sweeper (wide right arc) ──────────────────────────────────────────────
    new THREE.Vector3( 1.5, 5.0, -6.0), // 02 sweeper entrance
    new THREE.Vector3( 2.5, 4.5, -4.5), // 03 sweeper apex
    new THREE.Vector3( 2.0, 4.0, -3.0), // 04 sweeper exit → approaching hairpin 1

    // ── Hairpin 1 (right → U-turn left) ─────────────────────────────────────
    new THREE.Vector3( 2.5, 3.5, -1.5), // 05 approach
    new THREE.Vector3( 3.2, 3.0, -0.5), // 06 apex (rightmost point)
    new THREE.Vector3( 2.0, 2.5,  0.5), // 07 exit (now heading left-forward)

    // ── Brief straight ───────────────────────────────────────────────────────
    new THREE.Vector3( 0.0, 2.0,  1.0), // 08

    // ── Hairpin 2 (left → U-turn right) ─────────────────────────────────────
    new THREE.Vector3(-1.5, 1.5,  1.5), // 09 approach
    new THREE.Vector3(-3.0, 1.0,  0.5), // 10 apex (leftmost point)
    new THREE.Vector3(-1.5, 0.5,  1.0), // 11 exit (heading right-forward)

    // ── Brief straight ───────────────────────────────────────────────────────
    new THREE.Vector3( 0.5, 0.0,  2.0), // 12

    // ── Hairpin 3 (right → U-turn left) ─────────────────────────────────────
    new THREE.Vector3( 2.0,-0.5,  2.5), // 13 approach
    new THREE.Vector3( 3.0,-1.0,  1.5), // 14 apex
    new THREE.Vector3( 1.5,-1.5,  2.0), // 15 exit

    // ── Brief straight ───────────────────────────────────────────────────────
    new THREE.Vector3(-0.5,-2.0,  2.5), // 16

    // ── Hairpin 4 (left → U-turn right) ─────────────────────────────────────
    new THREE.Vector3(-2.0,-2.5,  3.0), // 17 approach
    new THREE.Vector3(-3.0,-3.0,  2.0), // 18 apex
    new THREE.Vector3(-1.5,-3.5,  2.5), // 19 exit

    // ── Brief straight ───────────────────────────────────────────────────────
    new THREE.Vector3( 0.5,-4.0,  3.5), // 20

    // ── Hairpin 5 (right → U-turn left) ─────────────────────────────────────
    new THREE.Vector3( 2.0,-4.5,  4.0), // 21 approach
    new THREE.Vector3( 2.8,-5.0,  3.0), // 22 apex
    new THREE.Vector3( 1.0,-5.5,  3.5), // 23 exit

    // ── Final straight — mountain foot ───────────────────────────────────────
    new THREE.Vector3( 0.0,-6.0,  5.0), // 24 finish
  ],
  false,         // closed = false
  'catmullrom',
  0.5,           // tension — 0.5 default gives smooth curves; reduce for sharper turns
)

export function Road() {
  const tubeGeometry = useMemo(
    () => new THREE.TubeGeometry(ROAD_CURVE, 200, 0.07, 8, false),
    [],
  )

  // Center-line dashes
  const dashGeometry = useMemo(() => {
    const points: THREE.Vector3[] = []
    const dashCount = 40
    for (let i = 0; i < dashCount; i++) {
      const t0 = i / dashCount
      const t1 = t0 + 0.4 / dashCount  // dash length
      points.push(ROAD_CURVE.getPointAt(t0))
      points.push(ROAD_CURVE.getPointAt(Math.min(t1, 0.999)))
    }
    const geo = new THREE.BufferGeometry()
    geo.setFromPoints(points)
    return geo
  }, [])

  // Guard rail indicators at hairpin apexes (subtle marker lines)
  const hairpinMarkers = useMemo(() => {
    // t values roughly corresponding to the 5 hairpin apexes
    const apexTs = [0.22, 0.38, 0.53, 0.68, 0.83]
    const pts: THREE.Vector3[] = []
    for (const t of apexTs) {
      const pos = ROAD_CURVE.getPointAt(t)
      const tangent = ROAD_CURVE.getTangentAt(t)
      const normal = new THREE.Vector3(-tangent.z, 0, tangent.x).normalize()
      // Small perpendicular line across the road at the apex
      pts.push(pos.clone().addScaledVector(normal, -0.4))
      pts.push(pos.clone().addScaledVector(normal,  0.4))
    }
    const geo = new THREE.BufferGeometry()
    geo.setFromPoints(pts)
    return geo
  }, [])

  return (
    <group>
      {/* Road surface */}
      <mesh geometry={tubeGeometry}>
        <meshStandardMaterial color="#4a4560" roughness={0.85} metalness={0.05} />
      </mesh>

      {/* Center-line dashes */}
      <lineSegments geometry={dashGeometry}>
        <lineBasicMaterial color="#e5e1db" opacity={0.5} transparent />
      </lineSegments>

      {/* Hairpin apex markers (subtle white lines) */}
      <lineSegments geometry={hairpinMarkers}>
        <lineBasicMaterial color="#ffffff" opacity={0.6} transparent />
      </lineSegments>
    </group>
  )
}
