/**
 * Infralytix — Pareto Scatter Chart (Recharts).
 *
 * Renders workflow candidates in Cost (X-axis) vs Makespan (Y-axis) space.
 * Visual upgrades vs v1:
 * - Per-provider branded scatter colors (AWS amber, Azure sky, GCP blue)
 * - Custom dark glassmorphic tooltip (no default Recharts tooltip background)
 * - Staggered point entrance: dominated points fade in first, then Pareto layer
 * - Darker grid + axis styling to match neutral-950 background
 */

import React, { useMemo, useState, useEffect } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { motion } from 'framer-motion'
import { CandidateResult, ParetoPoint, WorkflowOptimizeResult } from '../types'

// ─── Types ────────────────────────────────────────────────────────────────────

interface ChartPoint {
  x: number
  y: number
  provider: string
  instanceType: string
  vcpu: number
  ramGb: number
  hasGpu: boolean
  isPareto: boolean
  label: string | null
}

// ─── Per-provider brand colors ────────────────────────────────────────────────

const PROVIDER_COLORS: Record<string, string> = {
  aws:   '#FF9900', // official AWS orange
  azure: '#0089D6', // official Azure blue
  gcp:   '#4285F4', // official GCP blue
}

const PROVIDER_LABELS: Record<string, string> = {
  aws:   'AWS EC2',
  azure: 'Azure VMs',
  gcp:   'GCP Compute',
}

// ─── Custom Tooltip ───────────────────────────────────────────────────────────

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ payload: ChartPoint }>
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) return null

  const data = payload[0].payload
  const color = PROVIDER_COLORS[data.provider.toLowerCase()] || '#a855f7'

  return (
    <div className="glass-card p-3.5 bg-neutral-950/98 border-[color-mix(in_srgb,var(--color-bg-elevated)_65%,rgba(255,255,255,0.12))] shadow-2xl rounded-xl text-xs space-y-2 min-w-[220px] backdrop-blur-md">
      {/* Provider chip */}
      <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-2">
        <span
          className="font-bold uppercase tracking-wider text-[10px] px-2.5 py-0.5 rounded-full"
          style={{
            backgroundColor: `${color}18`,
            color,
            border: `1px solid ${color}38`,
          }}
        >
          {PROVIDER_LABELS[data.provider.toLowerCase()] ?? data.provider.toUpperCase()}
        </span>
        {data.label && (
          <span className="badge-success text-[10px] font-semibold">★ {data.label}</span>
        )}
      </div>

      {/* Instance */}
      <div>
        <div className="font-mono text-sm font-bold text-white truncate">{data.instanceType}</div>
        <div className="text-neutral-400 text-[11px] mt-0.5">
          {data.vcpu} vCPU · {data.ramGb} GB RAM{data.hasGpu ? ' · GPU' : ''}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2 pt-1.5 border-t border-white/10">
        <div>
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider mb-0.5">Total Cost</div>
          <div className="font-mono text-sm font-bold text-emerald-400">${data.x.toFixed(4)}</div>
        </div>
        <div>
          <div className="text-[10px] text-neutral-500 uppercase tracking-wider mb-0.5">Makespan</div>
          <div className="font-mono text-sm font-bold text-sky-400">
            {data.y >= 60 ? `${(data.y / 60).toFixed(1)}m` : `${data.y.toFixed(1)}s`}
          </div>
        </div>
      </div>

      <div className="text-[10px] text-neutral-600 pt-0.5">
        {data.isPareto ? '✓ Pareto-optimal configuration' : '○ Dominated by superior tradeoff'}
      </div>
    </div>
  )
}

// ─── Main chart component ─────────────────────────────────────────────────────

interface ParetoScatterChartProps {
  result: WorkflowOptimizeResult
}

export const ParetoScatterChart: React.FC<ParetoScatterChartProps> = ({ result }) => {
  const [showAllCandidates, setShowAllCandidates] = useState<boolean>(true)
  const [chartVisible, setChartVisible] = useState(false)

  // Staggered entrance: trigger after a short mount delay
  useEffect(() => {
    const t = setTimeout(() => setChartVisible(true), 80)
    return () => clearTimeout(t)
  }, [])

  // Map Pareto set for O(1) lookup
  const paretoLookup = useMemo(() => {
    const map = new Map<string, ParetoPoint>()
    result.pareto_front.forEach((p) => {
      map.set(`${p.candidate.provider}:${p.candidate.instance_type}`, p)
    })
    return map
  }, [result.pareto_front])

  // Split candidates: pareto by provider, dominated
  const { awsPareto, azurePareto, gcpPareto, dominated, frontierLinePoints } = useMemo(() => {
    const aws: ChartPoint[] = []
    const azure: ChartPoint[] = []
    const gcp: ChartPoint[] = []
    const dom: ChartPoint[] = []

    result.all_candidates.forEach((c: CandidateResult) => {
      if (c.provider_error) return
      const key = `${c.provider}:${c.instance_type}`
      const paretoMatch = paretoLookup.get(key)
      const isPareto = Boolean(paretoMatch)

      const point: ChartPoint = {
        x: c.evaluation.total_cost_usd,
        y: c.evaluation.makespan_seconds,
        provider: c.provider,
        instanceType: c.instance_type,
        vcpu: c.instance_spec.vcpu,
        ramGb: c.instance_spec.ram_gb,
        hasGpu: c.instance_spec.has_gpu,
        isPareto,
        label: paretoMatch?.label || null,
      }

      if (isPareto) {
        const p = c.provider.toLowerCase()
        if (p === 'aws') aws.push(point)
        else if (p === 'azure') azure.push(point)
        else gcp.push(point)
      } else {
        dom.push(point)
      }
    })

    const frontier = [...aws, ...azure, ...gcp].sort((a, b) => a.x - b.x)

    return {
      awsPareto: aws,
      azurePareto: azure,
      gcpPareto: gcp,
      dominated: dom,
      frontierLinePoints: frontier,
    }
  }, [result.all_candidates, paretoLookup])

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card p-6 rounded-2xl space-y-4"
    >
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Multi-Cloud Pareto Efficiency Frontier
            <span className="badge-info text-xs">
              {result.candidates_pareto} Optimal of {result.candidates_evaluated} Evaluated
            </span>
          </h3>
          <p className="text-xs text-neutral-400 mt-0.5">
            Lower cost (left) and lower makespan (bottom) represent superior configurations.
          </p>
        </div>

        <label className="flex items-center gap-2 text-xs text-neutral-300 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showAllCandidates}
            onChange={(e) => setShowAllCandidates(e.target.checked)}
            className="rounded bg-white/10 border-white/20 text-brand-500 focus:ring-0 w-3.5 h-3.5"
          />
          <span>Show dominated ({dominated.length})</span>
        </label>
      </div>

      {/* Chart canvas — fade in when ready */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: chartVisible ? 1 : 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="w-full h-[420px]"
      >
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 20, right: 30, bottom: 30, left: 20 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#1e293b"
              opacity={0.7}
            />
            <XAxis
              type="number"
              dataKey="x"
              name="Cost"
              stroke="#475569"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={(v: number) => `$${v.toFixed(3)}`}
              label={{
                value: 'Total Workflow Cost (USD)',
                position: 'insideBottom',
                offset: -15,
                fill: '#64748b',
                fontSize: 11,
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Makespan"
              stroke="#475569"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              tickFormatter={(v: number) => (v >= 60 ? `${(v / 60).toFixed(0)}m` : `${v.toFixed(0)}s`)}
              label={{
                value: 'Makespan',
                angle: -90,
                position: 'insideLeft',
                offset: 10,
                fill: '#64748b',
                fontSize: 11,
              }}
            />
            <ZAxis range={[60, 240]} />
            <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#334155' }} />

            {/* Pareto frontier dashed line */}
            {frontierLinePoints.length > 1 && (
              <Line
                type="monotone"
                data={frontierLinePoints}
                dataKey="y"
                stroke="#818cf8"
                strokeWidth={1.5}
                strokeDasharray="5 4"
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                name="Pareto Frontier"
              />
            )}

            {/* Dominated candidates */}
            {showAllCandidates && (
              <Scatter
                name="Dominated"
                data={dominated}
                fill="#334155"
                opacity={0.35}
                isAnimationActive={chartVisible}
                animationBegin={0}
                animationDuration={600}
              />
            )}

            {/* Per-provider Pareto points */}
            {awsPareto.length > 0 && (
              <Scatter
                name="AWS Pareto"
                data={awsPareto}
                fill={PROVIDER_COLORS.aws}
                stroke="#1c1917"
                strokeWidth={1.5}
                isAnimationActive={chartVisible}
                animationBegin={showAllCandidates ? 300 : 0}
                animationDuration={700}
              />
            )}
            {azurePareto.length > 0 && (
              <Scatter
                name="Azure Pareto"
                data={azurePareto}
                fill={PROVIDER_COLORS.azure}
                stroke="#0c1a27"
                strokeWidth={1.5}
                isAnimationActive={chartVisible}
                animationBegin={showAllCandidates ? 400 : 100}
                animationDuration={700}
              />
            )}
            {gcpPareto.length > 0 && (
              <Scatter
                name="GCP Pareto"
                data={gcpPareto}
                fill={PROVIDER_COLORS.gcp}
                stroke="#0f172a"
                strokeWidth={1.5}
                isAnimationActive={chartVisible}
                animationBegin={showAllCandidates ? 500 : 200}
                animationDuration={700}
              />
            )}

            <Legend
              verticalAlign="top"
              height={36}
              wrapperStyle={{ fontSize: '11px', color: '#94a3b8' }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Custom provider legend row */}
      <div className="flex flex-wrap items-center justify-between text-xs text-neutral-400 pt-3 border-t border-white/10 gap-3">
        <div className="flex items-center gap-5">
          {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
            <span key={key} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ background: PROVIDER_COLORS[key] }}
              />
              {label}
            </span>
          ))}
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0 border-t border-dashed border-indigo-400" />
            Pareto Frontier
          </span>
        </div>
        <div className="text-[11px] text-neutral-600">
          Evaluated via critical-path makespan DAG &amp; live catalog pricing
        </div>
      </div>
    </motion.div>
  )
}
