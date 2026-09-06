/**
 * Infralytix -- Health Score Gauge Component.
 *
 * Renders an animated SVG arc gauge (0-100). Color-coded by score.
 */

import React, { useEffect, useState } from 'react'
import { CodeHealthScore } from '../types'

interface HealthScoreGaugeProps {
  score: CodeHealthScore
}

function getScoreColor(n: number): string {
  if (n >= 75) return '#10b981'
  if (n >= 50) return '#f59e0b'
  return '#ef4444'
}

function getScoreLabel(n: number): string {
  if (n >= 75) return 'Healthy'
  if (n >= 50) return 'Needs Attention'
  return 'Requires Improvement'
}

const SUB: { key: keyof CodeHealthScore; label: string }[] = [
  { key: 'maintainability', label: 'Maintainability' },
  { key: 'complexity', label: 'Simplicity' },
  { key: 'test_coverage_estimate', label: 'Test Coverage' },
  { key: 'documentation', label: 'Documentation' },
]

export const HealthScoreGauge: React.FC<HealthScoreGaugeProps> = ({ score }) => {
  const [animated, setAnimated] = useState(0)

  useEffect(() => {
    let start: number | null = null
    const target = score.overall
    const step = (ts: number) => {
      if (!start) start = ts
      const p = Math.min((ts - start) / 800, 1)
      const e = 1 - Math.pow(1 - p, 3)
      setAnimated(Math.round(e * target))
      if (p < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [score.overall])

  const size = 160
  const sw = 14
  const r = (size - sw) / 2
  const circ = Math.PI * r
  const offset = circ - (animated / 100) * circ
  const color = getScoreColor(score.overall)
  const label = getScoreLabel(score.overall)
  const half = size / 2

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1.5rem' }}>
      <div style={{ position: 'relative', width: size, height: half + sw }}>
        <svg width={size} height={half + sw} viewBox={`0 0 ${size} ${half + sw}`} style={{ overflow: 'visible' }}>
          <path
            d={`M ${sw / 2} ${half} A ${r} ${r} 0 0 1 ${size - sw / 2} ${half}`}
            fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth={sw} strokeLinecap="round"
          />
          <path
            d={`M ${sw / 2} ${half} A ${r} ${r} 0 0 1 ${size - sw / 2} ${half}`}
            fill="none" stroke={color} strokeWidth={sw} strokeLinecap="round"
            strokeDasharray={circ} strokeDashoffset={offset}
            style={{ filter: `drop-shadow(0 0 8px ${color}80)`, transition: 'stroke-dashoffset 0.05s linear' }}
          />
        </svg>
        <div style={{ position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)', textAlign: 'center' }}>
          <div style={{ fontSize: '2.5rem', fontWeight: 800, color, lineHeight: 1, textShadow: `0 0 20px ${color}60` }}>
            {animated}
          </div>
          <div style={{ fontSize: '0.7rem', color: 'rgba(255,255,255,0.4)', marginTop: '0.2rem' }}>/ 100</div>
        </div>
      </div>

      <div style={{ padding: '0.25rem 0.75rem', borderRadius: '999px', background: `${color}20`, border: `1px solid ${color}40`, color, fontSize: '0.8rem', fontWeight: 600, marginTop: '-0.5rem' }}>
        {label}
      </div>

      <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
        {SUB.map(({ key, label }) => {
          const val = score[key] as number
          const bc = getScoreColor(val)
          return (
            <div key={key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', marginBottom: '0.25rem', color: 'rgba(255,255,255,0.6)' }}>
                <span>{label}</span>
                <span style={{ color: bc, fontWeight: 600 }}>{val}</span>
              </div>
              <div style={{ height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '999px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${val}%`, background: bc, borderRadius: '999px', boxShadow: `0 0 6px ${bc}60`, transition: 'width 0.8s cubic-bezier(0.16, 1, 0.3, 1)' }} />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
