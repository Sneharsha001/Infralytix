/**
 * PhysicalTiltCard
 *
 * A wrapper component that gives cards:
 *   1. CSS 3D perspective spring-eased tilt on mouse hover (rotateX / rotateY)
 *   2. 3 stacked depth sheet pseudo-elements behind the card for physical depth illusion.
 *   3. An optional rotating conic-gradient aurora border for isWinner mode.
 */

import React, { useCallback, useRef } from 'react'
import { useReducedMotion } from 'framer-motion'

interface PhysicalTiltCardProps {
  children: React.ReactNode
  className?: string
  style?: React.CSSProperties
  isWinner?: boolean
  depthSheets?: 1 | 2 | 3
  maxTilt?: number
}

export const PhysicalTiltCard: React.FC<PhysicalTiltCardProps> = ({
  children,
  className = '',
  style,
  isWinner = false,
  depthSheets = 3,
  maxTilt = 10,
}) => {
  const shouldReduce = useReducedMotion()
  const containerRef = useRef<HTMLDivElement>(null)
  const frameRef = useRef<number>(0)

  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (shouldReduce) return
      const el = containerRef.current
      if (!el) return
      cancelAnimationFrame(frameRef.current)
      frameRef.current = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect()
        const dx = (e.clientX - (rect.left + rect.width / 2)) / (rect.width / 2)
        const dy = (e.clientY - (rect.top + rect.height / 2)) / (rect.height / 2)
        const rotY = dx * maxTilt
        const rotX = -dy * maxTilt
        el.style.transform = `perspective(900px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(1.015)`
        el.style.transition = 'transform 80ms linear'
      })
    },
    [shouldReduce, maxTilt]
  )

  const handleMouseLeave = useCallback(() => {
    cancelAnimationFrame(frameRef.current)
    const el = containerRef.current
    if (!el) return
    el.style.transform = 'perspective(900px) rotateX(0deg) rotateY(0deg) scale(1)'
    el.style.transition = 'transform 400ms cubic-bezier(0.22, 1, 0.36, 1)'
  }, [])

  const sheets = Array.from({ length: depthSheets ?? 3 }, (_, i) => i + 1)

  return (
    <div className="depth-card-host" style={{ perspective: 900 }}>
      {sheets.map((n) => (
        <div key={n} className={`depth-sheet depth-sheet-${n}`} />
      ))}
      <div
        ref={containerRef}
        className={[
          'relative',
          isWinner ? 'aurora-border-card z-20' : 'z-10',
          className,
        ].join(' ')}
        style={{
          transformStyle: 'preserve-3d',
          willChange: 'transform',
          ...style,
        }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        {children}
      </div>
    </div>
  )
}
