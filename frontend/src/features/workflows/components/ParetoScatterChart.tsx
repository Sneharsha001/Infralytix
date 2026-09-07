/**
 * Infralytix — Pareto Scatter Chart (Recharts).
 *
 * Renders workflow candidates in Cost (X-axis) vs Makespan (Y-axis) space:
 * - Dominated candidates in subtle slate dots.
 * - Pareto-optimal candidates with vibrant provider colors.
 * - Pareto frontier step/connection line highlighting the optimal tradeoff curve.
 * - Prominently marked Fastest, Cheapest, and Best Balance points.
 */

import React, { useMemo, useState } from 'react'
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
import { CandidateResult, ParetoPoint, WorkflowOptimizeResult } from '../types'

interface ChartPoint {
  x: number // cost in USD
  y: number // makespan in seconds
  provider: string
  instanceType: string
  vcpu: number
  ramGb: number
  hasGpu: boolean
  isPareto: boolean
  label: string | null
}

const PROVIDER_COLORS: Record<string, string> = {
  aws: '#f59e0b', // amber
  azure: '#0ea5e9', // sky
  gcp: '#3b82f6', // blue
}

interface CustomTooltipProps {
  active?: boolean
  payload?: Array<{ payload: ChartPoint }>
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (!active || !payload || payload.length === 0) return null

  const data = payload[0].payload
  const providerColor = PROVIDER_COLORS[data.provider.toLowerCase()] || '#a855f7'

  return (
    <div className="glass-card p-3.5 bg-neutral-950/95 border-white/20 shadow-2xl rounded-xl text-xs space-y-2 min-w-[210px]">
      <div className="flex items-center justify-between gap-2 border-b border-white/10 pb-2">
        <span
          className="font-bold uppercase tracking-wider text-[10px] px-2 py-0.5 rounded-full"
          style={{
            backgroundColor: `${providerColor}20`,
            color: providerColor,
            border: `1px solid ${providerColor}40`,
          }}
        >
          {data.provider.toUpperCase()}
        </span>
        {data.label && (
          <span className="badge-success text-[10px] font-semibold">
            ★ {data.label}
          </span>
        )}
      </div>

      <div>
        <div className="font-mono text-sm font-bold text-white truncate">
          {data.instanceType}
        </div>
        <div className="text-neutral-400 text-[11px]">
          {data.vcpu} vCPU • {data.ramGb} GB RAM {data.hasGpu ? '• GPU' : ''}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/10">
        <div>
          <div className="text-[10px] text-neutral-400">Total Cost</div>
          <div className="font-mono text-sm font-bold text-emerald-400">
            ${data.x.toFixed(4)}
          </div>
        </div>
        <div>
          <div className="text-[10px] text-neutral-400">Makespan</div>
          <div className="font-mono text-sm font-bold text-sky-400">
            {data.y >= 60
              ? `${(data.y / 60).toFixed(1)}m (${data.y.toFixed(0)}s)`
              : `${data.y.toFixed(1)}s`}
          </div>
        </div>
      </div>

      <div className="text-[10px] text-neutral-500 pt-1">
        {data.isPareto ? '✓ Pareto-optimal configuration' : '○ Dominated by superior tradeoff'}
      </div>
    </div>
  )
}

interface ParetoScatterChartProps {
  result: WorkflowOptimizeResult
}

export const ParetoScatterChart: React.FC<ParetoScatterChartProps> = ({ result }) => {
  const [showAllCandidates, setShowAllCandidates] = useState<boolean>(true)

  // Map Pareto set for O(1) lookup
  const paretoLookup = useMemo(() => {
    const map = new Map<string, ParetoPoint>()
    result.pareto_front.forEach((p) => {
      const key = `${p.candidate.provider}:${p.candidate.instance_type}`
      map.set(key, p)
    })
    return map
  }, [result.pareto_front])

  // Process all candidates into chart points
  const { paretoPoints, dominatedPoints, frontierLinePoints } = useMemo(() => {
    const pareto: ChartPoint[] = []
    const dominated: ChartPoint[] = []

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
        pareto.push(point)
      } else {
        dominated.push(point)
      }
    })

    // Sort Pareto frontier points by cost ascending to draw the frontier line
    const frontier = [...pareto].sort((a, b) => a.x - b.x)

    return {
      paretoPoints: pareto,
      dominatedPoints: dominated,
      frontierLinePoints: frontier,
    }
  }, [result.all_candidates, paretoLookup])

  return (
    <div className="glass-card p-6 rounded-2xl border border-white/10 space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Multi-Cloud Pareto Efficiency Frontier
            <span className="badge-info text-xs">
              {result.candidates_pareto} Optimal of {result.candidates_evaluated} Evaluated
            </span>
          </h3>
          <p className="text-xs text-neutral-400 mt-0.5">
            Lower Cost (left) and Lower Makespan (bottom) represent superior configurations.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-neutral-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={showAllCandidates}
              onChange={(e) => setShowAllCandidates(e.target.checked)}
              className="rounded bg-white/10 border-white/20 text-brand-500 focus:ring-0 w-3.5 h-3.5"
            />
            <span>Show dominated points ({dominatedPoints.length})</span>
          </label>
        </div>
      </div>

      {/* Recharts Canvas */}
      <div className="w-full h-[420px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart
            margin={{ top: 20, right: 30, bottom: 25, left: 20 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#334155"
              opacity={0.4}
            />
            <XAxis
              type="number"
              dataKey="x"
              name="Cost"
              stroke="#94a3b8"
              fontSize={11}
              tickFormatter={(v: number) => `$${v.toFixed(3)}`}
              label={{
                value: 'Total Workflow Cost (USD)',
                position: 'insideBottom',
                offset: -12,
                fill: '#94a3b8',
                fontSize: 11,
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="Makespan"
              stroke="#94a3b8"
              fontSize={11}
              tickFormatter={(v: number) => (v >= 60 ? `${(v / 60).toFixed(0)}m` : `${v.toFixed(0)}s`)}
              label={{
                value: 'Makespan Completion Time',
                angle: -90,
                position: 'insideLeft',
                offset: 5,
                fill: '#94a3b8',
                fontSize: 11,
              }}
            />
            <ZAxis range={[60, 240]} />
            <Tooltip content={<CustomTooltip />} />

            {/* Pareto Frontier Connecting Line */}
            {frontierLinePoints.length > 1 && (
              <Line
                type="monotone"
                data={frontierLinePoints}
                dataKey="y"
                stroke="#818cf8"
                strokeWidth={2}
                strokeDasharray="4 4"
                dot={false}
                activeDot={false}
                isAnimationActive={false}
                name="Pareto Frontier"
              />
            )}

            {/* Dominated Candidates */}
            {showAllCandidates && (
              <Scatter
                name="Dominated Candidates"
                data={dominatedPoints}
                fill="#475569"
                opacity={0.4}
              />
            )}

            {/* Pareto Frontier Points */}
            <Scatter
              name="Pareto Optimal"
              data={paretoPoints}
              fill="#818cf8"
              stroke="#ffffff"
              strokeWidth={1.5}
            />

            <Legend
              verticalAlign="top"
              height={36}
              wrapperStyle={{ fontSize: '11px', color: '#cbd5e1' }}
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Legend & Provider Indicators */}
      <div className="flex flex-wrap items-center justify-between text-xs text-neutral-400 pt-3 border-t border-white/10 gap-3">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500" /> AWS EC2
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-sky-500" /> Azure VMs
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500" /> GCP Compute
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-indigo-400 border-dashed" /> Pareto Frontier Line
          </span>
        </div>

        <div className="text-[11px] text-neutral-500">
          Evaluated via critical-path makespan DAG & live catalog pricing
        </div>
      </div>
    </div>
  )
}
