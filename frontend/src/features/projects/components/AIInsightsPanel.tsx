/**
 * Infralytix -- AI Insights Panel Component.
 *
 * Displays Gemini AI analysis results: health score gauge, insight cards,
 * tech debt indicators, and recommended next steps. Handles all states:
 * no_repo, no_analysis, loading, and complete.
 */

import React, { useState } from 'react'
import { projectsApi } from '../api'
import { AgentRun, AIInsightResult, ArchitectureInsight } from '../types'
import { HealthScoreGauge } from './HealthScoreGauge'

interface AIInsightsPanelProps {
  projectId: string
  hasRepository: boolean          // true if project has an uploaded archive
  existingRun?: AgentRun | null   // latest gemini AgentRun if one exists
  onAnalysisComplete?: (run: AgentRun) => void
}

const SEVERITY_CONFIG = {
  info: { bg: 'rgba(99,102,241,0.12)', border: 'rgba(99,102,241,0.3)', dot: '#818cf8', label: 'Info' },
  warning: { bg: 'rgba(245,158,11,0.12)', border: 'rgba(245,158,11,0.3)', dot: '#fbbf24', label: 'Warning' },
  critical: { bg: 'rgba(239,68,68,0.12)', border: 'rgba(239,68,68,0.3)', dot: '#f87171', label: 'Critical' },
}


function InsightCard({ insight }: { insight: ArchitectureInsight }) {
  const sev = SEVERITY_CONFIG[insight.severity] ?? SEVERITY_CONFIG.info
  return (
    <div style={{
      padding: '1rem',
      borderRadius: '0.75rem',
      background: sev.bg,
      border: `1px solid ${sev.border}`,
      display: 'flex',
      gap: '0.75rem',
    }}>
      <div style={{
        width: '8px', height: '8px', borderRadius: '50%',
        background: sev.dot, flexShrink: 0, marginTop: '0.35rem',
        boxShadow: `0 0 8px ${sev.dot}80`,
      }} />
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'rgba(255,255,255,0.9)' }}>
            {insight.title}
          </span>
          <span style={{
            fontSize: '0.65rem', padding: '0.1rem 0.4rem',
            borderRadius: '999px', background: `${sev.dot}25`, color: sev.dot, fontWeight: 600,
          }}>
            {sev.label}
          </span>
          <span style={{
            fontSize: '0.65rem', padding: '0.1rem 0.4rem',
            borderRadius: '999px', background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.4)',
          }}>
            {insight.category}
          </span>
        </div>
        <p style={{ fontSize: '0.82rem', color: 'rgba(255,255,255,0.55)', margin: 0, lineHeight: 1.6 }}>
          {insight.description}
        </p>
      </div>
    </div>
  )
}

function SkeletonLine({ width = '100%', height = '14px' }: { width?: string; height?: string }) {
  return (
    <div style={{
      width, height, borderRadius: '4px',
      background: 'linear-gradient(90deg, rgba(255,255,255,0.05) 25%, rgba(255,255,255,0.1) 50%, rgba(255,255,255,0.05) 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.5s infinite',
    }} />
  )
}

export const AIInsightsPanel: React.FC<AIInsightsPanelProps> = ({
  projectId,
  hasRepository,
  existingRun,
  onAnalysisComplete,
}) => {
  const [run, setRun] = useState<AgentRun | null>(existingRun ?? null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRunAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await projectsApi.triggerAnalysis(projectId)
      setRun(result)
      onAnalysisComplete?.(result)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setError(msg ?? 'Analysis failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const insight: AIInsightResult | null =
    run?.status === 'completed' && run.output_data
      ? (run.output_data as AIInsightResult)
      : null

  // ── State: no repository uploaded ────────────────────────────────────────
  if (!hasRepository) {
    return (
      <div className="glass-card" style={{ padding: '2rem', textAlign: 'center' }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>📦</div>
        <h3 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '0.5rem' }}>
          No Repository Yet
        </h3>
        <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.9rem' }}>
          Upload a repository zip archive first to enable AI analysis.
        </p>
      </div>
    )
  }

  // ── State: loading ────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="glass-card" style={{ padding: '2rem' }}>
        <style>{`@keyframes shimmer { to { background-position: -200% 0; } }`}</style>
        <div style={{ marginBottom: '1.5rem' }}>
          <SkeletonLine width="40%" height="20px" />
          <div style={{ marginTop: '0.75rem' }}>
            <SkeletonLine />
          </div>
          <div style={{ marginTop: '0.4rem' }}>
            <SkeletonLine width="80%" />
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: '80px', height: '80px', borderRadius: '50%',
            background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '50%',
              border: '3px solid transparent',
              borderTopColor: '#6366f1',
              animation: 'spin 0.8s linear infinite',
            }} />
          </div>
        </div>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        <p style={{ textAlign: 'center', color: 'rgba(255,255,255,0.4)', fontSize: '0.9rem' }}>
          Running Gemini AI analysis...
        </p>
        {[1, 2, 3].map(i => (
          <div key={i} style={{ marginTop: '0.75rem' }}>
            <SkeletonLine width={`${70 + i * 5}%`} />
          </div>
        ))}
      </div>
    )
  }

  // ── State: no AI analysis run yet ─────────────────────────────────────────
  if (!insight) {
    return (
      <div className="glass-card" style={{ padding: '2rem', textAlign: 'center' }}>
        <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🤖</div>
        <h3 style={{ color: 'rgba(255,255,255,0.9)', marginBottom: '0.5rem' }}>
          AI Analysis Available
        </h3>
        <p style={{ color: 'rgba(255,255,255,0.45)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
          Run the Gemini AI agent to get architectural insights, health scores, and recommendations.
        </p>
        {error && (
          <div style={{
            padding: '0.75rem 1rem', borderRadius: '0.5rem',
            background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)',
            color: '#f87171', fontSize: '0.85rem', marginBottom: '1rem',
          }}>
            {error}
          </div>
        )}
        <button
          onClick={handleRunAnalysis}
          id="run-ai-analysis-btn"
          style={{
            padding: '0.75rem 1.75rem',
            borderRadius: '0.625rem',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            border: 'none',
            color: '#fff',
            fontSize: '0.9rem',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 4px 15px rgba(99,102,241,0.4)',
            transition: 'transform 0.2s, box-shadow 0.2s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-2px)'
            ;(e.currentTarget as HTMLButtonElement).style.boxShadow = '0 8px 25px rgba(99,102,241,0.6)'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)'
            ;(e.currentTarget as HTMLButtonElement).style.boxShadow = '0 4px 15px rgba(99,102,241,0.4)'
          }}
        >
          Run AI Analysis
        </button>
      </div>
    )
  }

  // ── State: complete -- show full insights ──────────────────────────────────
  const grouped = {
    critical: insight.insights.filter(i => i.severity === 'critical'),
    warning: insight.insights.filter(i => i.severity === 'warning'),
    info: insight.insights.filter(i => i.severity === 'info'),
  }
  const sorted = [...grouped.critical, ...grouped.warning, ...grouped.info]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'rgba(255,255,255,0.95)', margin: 0 }}>
          AI Intelligence Report
        </h2>
        <button
          id="re-run-analysis-btn"
          onClick={handleRunAnalysis}
          style={{
            padding: '0.4rem 0.9rem', borderRadius: '0.5rem',
            background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)',
            color: '#818cf8', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
          }}
        >
          Re-run Analysis
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '1.5rem' }}>
        {/* Health Score Gauge */}
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)', marginBottom: '1.25rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Health Score
          </h3>
          <HealthScoreGauge score={insight.health_score} />
        </div>

        {/* Summary + tech debt + next steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="glass-card" style={{ padding: '1.25rem' }}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Executive Summary
            </h3>
            <p style={{ fontSize: '0.9rem', color: 'rgba(255,255,255,0.75)', lineHeight: 1.7, margin: 0 }}>
              {insight.summary}
            </p>
          </div>

          {insight.tech_debt_indicators.length > 0 && (
            <div className="glass-card" style={{ padding: '1.25rem', background: 'rgba(239,68,68,0.06)', borderColor: 'rgba(239,68,68,0.15)' }}>
              <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#f87171', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Tech Debt Signals
              </h3>
              <ul style={{ margin: 0, padding: '0 0 0 1rem' }}>
                {insight.tech_debt_indicators.map((item, i) => (
                  <li key={i} style={{ fontSize: '0.85rem', color: 'rgba(255,255,255,0.6)', marginBottom: '0.3rem' }}>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Insight cards */}
      {sorted.length > 0 && (
        <div className="glass-card" style={{ padding: '1.5rem' }}>
          <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: 'rgba(255,255,255,0.6)', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Architectural Insights
            <span style={{ marginLeft: '0.5rem', background: 'rgba(255,255,255,0.08)', padding: '0.1rem 0.4rem', borderRadius: '999px', fontSize: '0.75rem' }}>
              {sorted.length}
            </span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {sorted.map((insight, i) => (
              <InsightCard key={i} insight={insight} />
            ))}
          </div>
        </div>
      )}

      {/* Recommended next steps */}
      {insight.recommended_next_steps.length > 0 && (
        <div className="glass-card" style={{ padding: '1.5rem', background: 'rgba(16,185,129,0.05)', borderColor: 'rgba(16,185,129,0.15)' }}>
          <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#34d399', marginBottom: '1rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Recommended Next Steps
          </h3>
          <ol style={{ margin: 0, padding: '0 0 0 1.25rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {insight.recommended_next_steps.map((step, i) => (
              <li key={i} style={{ fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)', lineHeight: 1.6 }}>
                {step}
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
