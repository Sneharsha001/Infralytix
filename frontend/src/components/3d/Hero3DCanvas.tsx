/**
 * Infralytix — Hero 3D Canvas Host Component.
 *
 * Provides:
 * - Lazy-loading of Three.js & R3F bundles via React.lazy and Suspense.
 * - WebGL context capability detection & graceful ErrorBoundary fallback.
 * - Detection of prefers-reduced-motion to freeze 3D animation.
 * - Atmosphere masking with high-contrast text preservation for foreground content.
 */

import React, { Suspense, Component, useState, useEffect } from 'react'
import { useReducedMotion } from 'framer-motion'
import { SceneFallback } from './SceneFallback'
import type { SceneVariant } from './CloudInfrastructureScene'

// Lazy-load the heavy 3D scene bundle so it doesn't block First Contentful Paint (FCP)
const LazyCloudInfrastructureScene = React.lazy(
  () => import('./CloudInfrastructureScene')
)

// ── WebGL Capability Check Helper ───────────────────────────────────────────
function isWebGLAvailable(): boolean {
  if (typeof window === 'undefined') return false
  try {
    const canvas = document.createElement('canvas')
    const gl =
      canvas.getContext('webgl2') ||
      canvas.getContext('webgl') ||
      canvas.getContext('experimental-webgl')
    return Boolean(gl)
  } catch {
    return false
  }
}

// ── WebGL Error Boundary ────────────────────────────────────────────────────
interface WebGLErrorBoundaryProps {
  children: React.ReactNode
  fallback: React.ReactNode
}

interface WebGLErrorBoundaryState {
  hasError: boolean
}

class WebGLErrorBoundary extends Component<
  WebGLErrorBoundaryProps,
  WebGLErrorBoundaryState
> {
  constructor(props: WebGLErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(): WebGLErrorBoundaryState {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo): void {
    console.warn(
      '[Infralytix 3D] WebGL context failed to initialize; switching to static ambient fallback:',
      error,
      errorInfo
    )
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback
    }
    return this.props.children
  }
}

// ── Hero3DCanvas Props ───────────────────────────────────────────────────────
export interface Hero3DCanvasProps {
  variant?: SceneVariant
  className?: string
}

export const Hero3DCanvas: React.FC<Hero3DCanvasProps> = ({
  variant = 'compare',
  className = '',
}) => {
  const prefersReduced = useReducedMotion()
  const [canRenderWebGL, setCanRenderWebGL] = useState<boolean | null>(null)

  useEffect(() => {
    setCanRenderWebGL(isWebGLAvailable())
  }, [])

  return (
    <div
      className={`absolute inset-0 w-full h-[600px] md:h-[700px] pointer-events-none overflow-hidden select-none z-0 ${className}`}
      aria-hidden="true"
    >
      {/* ── Background Layer: 3D Scene or Fallback ────────────────────────── */}
      {canRenderWebGL === false ? (
        <SceneFallback variant={variant} />
      ) : (
        <WebGLErrorBoundary fallback={<SceneFallback variant={variant} />}>
          <Suspense fallback={<SceneFallback variant={variant} />}>
            <LazyCloudInfrastructureScene
              variant={variant}
              reducedMotion={Boolean(prefersReduced)}
            />
          </Suspense>
        </WebGLErrorBoundary>
      )}

      {/* ── Contrast & Atmosphere Gradient Mask ───────────────────────────── */}
      {/* Soft gradient mask ensuring foreground headings/badges remain 100% legible */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse 75% 65% at 50% 38%, transparent 35%, rgba(10, 6, 24, 0.25) 65%, rgba(10, 6, 24, 0.85) 92%, #0a0618 100%), linear-gradient(to bottom, transparent 50%, rgba(10, 6, 24, 0.75) 85%, #0a0618 100%)',
        }}
      />
    </div>
  )
}

export default Hero3DCanvas
