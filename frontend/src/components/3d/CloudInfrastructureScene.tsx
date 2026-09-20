/**
 * Infralytix — Signature 3D Multi-Cloud Infrastructure Scene.
 *
 * A high-performance, low-poly abstract composition representing cloud nodes
 * (AWS / Azure / GCP / Infralytix) connected by pulsing energy pathways,
 * floating in a softly lit dark void matching the #242547 / #882ECA design palette.
 *
 * Features:
 * - Shared scene architecture across Cost Comparison, Workload Detection, and Workflow Optimizer.
 * - Dynamic camera angle and lighting accentuation per page variant ('compare', 'detect', 'optimize').
 * - Restrained autonomous drift + subtle mouse parallax.
 * - Full prefers-reduced-motion support (freezes to a single pristine frame).
 * - Capped dpr (1.5 max) and low polygon budget (<1,000 vertices) for 60fps on mid-range devices.
 */

import React, { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export type SceneVariant = 'compare' | 'detect' | 'optimize'

interface CloudInfrastructureSceneProps {
  variant?: SceneVariant
  reducedMotion?: boolean
}

// ── Node Definitions ─────────────────────────────────────────────────────────
interface NodeSpec {
  id: string
  name: string
  position: [number, number, number]
  geometryType: 'icosahedron' | 'octahedron' | 'dodecahedron'
  color: string
  emissive: string
  size: number
  wireColor: string
}

const NODES: NodeSpec[] = [
  // 1. Central Infralytix Orchestration Core
  {
    id: 'core',
    name: 'Infralytix Core',
    position: [0, 0.4, -0.6],
    geometryType: 'octahedron',
    color: '#9D3CE6',
    emissive: '#6E1AB5',
    size: 0.72,
    wireColor: '#D896FF',
  },
  // 2. AWS Compute Node
  {
    id: 'aws',
    name: 'AWS EC2 Node',
    position: [-2.9, -0.5, 0.3],
    geometryType: 'icosahedron',
    color: '#FF9900',
    emissive: '#B36B00',
    size: 0.50,
    wireColor: '#FFC066',
  },
  // 3. Azure Cloud Node
  {
    id: 'azure',
    name: 'Azure Compute Node',
    position: [2.8, 0.6, -0.2],
    geometryType: 'octahedron',
    color: '#0078D4',
    emissive: '#005A9E',
    size: 0.52,
    wireColor: '#66B2FF',
  },
  // 4. GCP Cloud Node
  {
    id: 'gcp',
    name: 'GCP Compute Node',
    position: [-0.6, 2.1, -0.8],
    geometryType: 'dodecahedron',
    color: '#4285F4',
    emissive: '#1A5EC8',
    size: 0.48,
    wireColor: '#99BEFF',
  },
  // 5. Infralytix Edge Satellite Node
  {
    id: 'edge',
    name: 'Edge Evaluator',
    position: [1.3, -1.8, -0.5],
    geometryType: 'octahedron',
    color: '#61D29A',
    emissive: '#2EA86E',
    size: 0.40,
    wireColor: '#A8ECC8',
  },
]

// Edges connecting nodes in the multi-cloud topology graph
const EDGES: [number, number][] = [
  [0, 1], // Core -> AWS
  [0, 2], // Core -> Azure
  [0, 3], // Core -> GCP
  [0, 4], // Core -> Edge
  [1, 3], // AWS -> GCP
  [2, 3], // Azure -> GCP
  [1, 4], // AWS -> Edge
  [2, 4], // Azure -> Edge
]

// ── Single Geometric Node Component ──────────────────────────────────────────
const InfrastructureNode: React.FC<{
  spec: NodeSpec
  reducedMotion: boolean
}> = ({ spec, reducedMotion }) => {
  const meshRef = useRef<THREE.Mesh>(null)
  const wireRef = useRef<THREE.Mesh>(null)

  useFrame((_, delta) => {
    if (reducedMotion) return
    if (meshRef.current) {
      meshRef.current.rotation.x += delta * 0.25
      meshRef.current.rotation.y += delta * 0.35
    }
    if (wireRef.current) {
      wireRef.current.rotation.x -= delta * 0.2
      wireRef.current.rotation.z += delta * 0.25
    }
  })

  return (
    <group position={spec.position}>
      {/* Solid Inner Body with soft emissive sheen */}
      <mesh ref={meshRef}>
        {spec.geometryType === 'icosahedron' && <icosahedronGeometry args={[spec.size, 0]} />}
        {spec.geometryType === 'octahedron' && <octahedronGeometry args={[spec.size, 0]} />}
        {spec.geometryType === 'dodecahedron' && <dodecahedronGeometry args={[spec.size, 0]} />}
        <meshStandardMaterial
          color={spec.color}
          emissive={spec.emissive}
          emissiveIntensity={0.9}
          roughness={0.2}
          metalness={0.8}
          flatShading
        />
      </mesh>

      {/* Wireframe Outer Halo */}
      <mesh ref={wireRef} scale={1.25}>
        {spec.geometryType === 'icosahedron' && <icosahedronGeometry args={[spec.size, 0]} />}
        {spec.geometryType === 'octahedron' && <octahedronGeometry args={[spec.size, 0]} />}
        {spec.geometryType === 'dodecahedron' && <dodecahedronGeometry args={[spec.size, 0]} />}
        <meshBasicMaterial
          color={spec.wireColor}
          wireframe
          transparent
          opacity={0.5}
        />
      </mesh>
    </group>
  )
}

// ── Connecting Pathways & Pulsing Data Packets ───────────────────────────────
const NetworkConnections: React.FC<{
  reducedMotion: boolean
  variant: SceneVariant
}> = ({ reducedMotion, variant }) => {
  const packetsRef = useRef<THREE.InstancedMesh>(null)
  const lineMeshRef = useRef<THREE.LineSegments>(null)

  // Build line segments geometry
  const lineGeometry = useMemo(() => {
    const points: THREE.Vector3[] = []
    EDGES.forEach(([i, j]) => {
      points.push(new THREE.Vector3(...NODES[i].position))
      points.push(new THREE.Vector3(...NODES[j].position))
    })
    const geom = new THREE.BufferGeometry().setFromPoints(points)
    return geom
  }, [])

  // Packet travel points
  const edgeCount = EDGES.length
  const dummy = useMemo(() => new THREE.Object3D(), [])

  // Primary line tint based on variant
  const lineColor = {
    compare: '#882ECA',
    detect: '#A855F7',
    optimize: '#61D29A',
  }[variant]

  const packetColor = {
    compare: '#FFFFFF',
    detect: '#61D29A',
    optimize: '#882ECA',
  }[variant]

  useFrame(({ clock }) => {
    if (reducedMotion || !packetsRef.current) return
    const mesh = packetsRef.current
    const t = clock.getElapsedTime()

    EDGES.forEach(([i, j], idx) => {
      const start = new THREE.Vector3(...NODES[i].position)
      const end = new THREE.Vector3(...NODES[j].position)

      // Calculate progress along edge with offset per edge
      const progress = ((t * 0.4 + idx * 0.18) % 1)
      const currentPos = new THREE.Vector3().lerpVectors(start, end, progress)

      // Slight pulsation scale
      const scale = 0.05 + Math.sin(t * 3 + idx) * 0.015

      dummy.position.copy(currentPos)
      dummy.scale.set(scale, scale, scale)
      dummy.updateMatrix()
      mesh.setMatrixAt(idx, dummy.matrix)
    })
    mesh.instanceMatrix.needsUpdate = true
  })

  return (
    <group>
      {/* Static Line Connections */}
      <lineSegments ref={lineMeshRef} geometry={lineGeometry}>
        <lineBasicMaterial
          color={lineColor}
          transparent
          opacity={0.6}
          linewidth={1.5}
        />
      </lineSegments>

      {/* Pulsing Energy Packets */}
      {!reducedMotion && (
        <instancedMesh
          ref={packetsRef}
          args={[undefined, undefined, edgeCount]}
        >
          <sphereGeometry args={[1, 8, 8]} />
          <meshBasicMaterial color={packetColor} />
        </instancedMesh>
      )}
    </group>
  )
}

// ── Camera Controller with Autonomous Drift + Mouse Parallax ─────────────────
const CameraRig: React.FC<{
  variant: SceneVariant
  reducedMotion: boolean
}> = ({ variant, reducedMotion }) => {
  // Variant-specific camera home position & orientation
  const homePos = useMemo<THREE.Vector3>(() => {
    switch (variant) {
      case 'compare':
        return new THREE.Vector3(0, 0.4, 6.4) // Balanced front view
      case 'detect':
        return new THREE.Vector3(1.8, 2.2, 5.8) // Angled top-down inspection
      case 'optimize':
        return new THREE.Vector3(-2.1, 1.5, 6.0) // Dynamic diagonal DAG view
    }
  }, [variant])

  const targetLook = useMemo(() => new THREE.Vector3(0, 0, 0), [])

  useFrame((state, delta) => {
    if (reducedMotion) {
      state.camera.position.copy(homePos)
      state.camera.lookAt(targetLook)
      return
    }

    const t = state.clock.getElapsedTime()
    // Very gentle autonomous drift
    const driftX = Math.sin(t * 0.18) * 0.22
    const driftY = Math.cos(t * 0.22) * 0.15

    // Subtle pointer parallax (restrained to avoid motion sickness)
    const pointerX = state.pointer.x * 0.35
    const pointerY = state.pointer.y * 0.22

    // Smooth lerp to target position
    state.camera.position.x = THREE.MathUtils.damp(
      state.camera.position.x,
      homePos.x + driftX + pointerX,
      2.5,
      delta
    )
    state.camera.position.y = THREE.MathUtils.damp(
      state.camera.position.y,
      homePos.y + driftY + pointerY,
      2.5,
      delta
    )
    state.camera.position.z = THREE.MathUtils.damp(
      state.camera.position.z,
      homePos.z,
      2.5,
      delta
    )

    state.camera.lookAt(targetLook)
  })

  return null
}

// ── Main Scene Group with Orbiting System ────────────────────────────────────
const SceneContent: React.FC<{
  variant: SceneVariant
  reducedMotion: boolean
}> = ({ variant, reducedMotion }) => {
  const systemRef = useRef<THREE.Group>(null)

  // Slow ambient rotation of the entire constellation
  useFrame((_, delta) => {
    if (reducedMotion || !systemRef.current) return
    systemRef.current.rotation.y += delta * 0.05
    systemRef.current.rotation.x = Math.sin(systemRef.current.rotation.y * 0.6) * 0.08
  })

  // Variant-specific key lights
  const keyLightColor = {
    compare: '#882ECA',
    detect: '#61D29A',
    optimize: '#0078D4',
  }[variant]

  const rimLightColor = {
    compare: '#FF9900',
    detect: '#882ECA',
    optimize: '#61D29A',
  }[variant]

  return (
    <>
      {/* ── Soft Ambient Lighting in Void (#242547) ───────────────────────── */}
      <ambientLight color="#242547" intensity={2.2} />

      {/* Primary Key Accent Light */}
      <pointLight
        position={[3, 3, 4]}
        color={keyLightColor}
        intensity={3.8}
        distance={18}
        decay={2}
      />

      {/* Deep Violet Fill Light */}
      <pointLight
        position={[-4, -2, 2]}
        color="#36136E"
        intensity={2.8}
        distance={14}
        decay={2}
      />

      {/* Variant-specific rim highlight */}
      <pointLight
        position={[0, -3, -3]}
        color={rimLightColor}
        intensity={2.4}
        distance={12}
        decay={2}
      />

      {/* ── Rotating Infrastructure Constellation ─────────────────────────── */}
      <group ref={systemRef}>
        {NODES.map((node) => (
          <InfrastructureNode
            key={node.id}
            spec={node}
            reducedMotion={reducedMotion}
          />
        ))}
        <NetworkConnections
          reducedMotion={reducedMotion}
          variant={variant}
        />
      </group>

      <CameraRig variant={variant} reducedMotion={reducedMotion} />
    </>
  )
}

// ── Exported Canvas Wrapper ──────────────────────────────────────────────────
export const CloudInfrastructureScene: React.FC<CloudInfrastructureSceneProps> = ({
  variant = 'compare',
  reducedMotion = false,
}) => {
  return (
    <div className="w-full h-full pointer-events-none select-none">
      <Canvas
        camera={{ position: [0, 0.4, 6.4], fov: 45, near: 0.1, far: 30 }}
        dpr={[1, 1.5]} // Clamp pixel ratio for mid-range laptops
        frameloop={reducedMotion ? 'demand' : 'always'}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
        }}
        style={{ pointerEvents: 'none' }}
      >
        <SceneContent variant={variant} reducedMotion={reducedMotion} />
      </Canvas>
    </div>
  )
}

export default CloudInfrastructureScene
