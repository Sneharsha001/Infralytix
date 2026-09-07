/**
 * Infralytix — AI Summary Card Component.
 *
 * Displays the AI-generated plain-language architectural trade-off analysis
 * below the Pareto scatter plot, highlighting cost savings, runtime speedup,
 * and multi-cloud deployment recommendations.
 */

import React from 'react'
import { WorkflowOptimizeResult } from '../types'

interface AiSummaryCardProps {
  result: WorkflowOptimizeResult
}

export const AiSummaryCard: React.FC<AiSummaryCardProps> = ({ result }) => {
  const { pareto_front, ai_summary, candidates_evaluated, provider_errors } = result

  // Extract key points
  const cheapest = pareto_front.find((p) => p.label?.includes('Cheapest')) || pareto_front[0]
  const fastest =
    pareto_front.find((p) => p.label?.includes('Fastest')) || pareto_front[pareto_front.length - 1]
  const balanced =
    pareto_front.find((p) => p.label?.includes('Best balance')) || pareto_front[0]

  const hasCostSavings = fastest && cheapest && fastest.total_cost > cheapest.total_cost
  const hasTimeSavings = fastest && cheapest && cheapest.makespan > fastest.makespan

  const costDelta = hasCostSavings ? fastest.total_cost - cheapest.total_cost : 0
  const timeDelta = hasTimeSavings ? cheapest.makespan - fastest.makespan : 0
  const pctFaster =
    hasTimeSavings && cheapest ? ((timeDelta / cheapest.makespan) * 100).toFixed(0) : '0'

  return (
    <div className="glass-card p-6 md:p-8 border-brand-500/30 bg-brand-950/15 relative overflow-hidden shadow-2xl rounded-2xl space-y-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-400 animate-ping" />
          <span className="badge-info text-xs font-semibold">
            AI Pareto Frontier &amp; Multi-Cloud Trade-off Analysis
          </span>
        </div>
        <div className="text-xs text-neutral-400">
          Evaluated {candidates_evaluated} candidates • {pareto_front.length} non-dominated options
        </div>
      </div>

      {/* Main Narrative */}
      <div>
        <h3 className="text-lg font-bold text-white mb-2">
          Architectural Recommendations &amp; Scheduling Strategy
        </h3>
        {ai_summary ? (
          <p className="text-sm md:text-base text-neutral-200 leading-relaxed whitespace-pre-line">
            {ai_summary}
          </p>
        ) : (
          <p className="text-sm md:text-base text-neutral-200 leading-relaxed">
            Multi-cloud optimization evaluated {candidates_evaluated} compute instances across AWS,
            Azure, and GCP. The resulting Pareto front presents an explicit trade-off between
            execution speed and on-demand compute cost.
          </p>
        )}
      </div>

      {/* Key Metric Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        {cheapest && (
          <div className="p-4 rounded-xl bg-white/[0.03] border border-amber-500/20 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wider">
                Cheapest Strategy
              </span>
              <span className="badge-neutral text-[10px]">
                {cheapest.candidate.provider.toUpperCase()}
              </span>
            </div>
            <div className="font-mono text-base font-bold text-white truncate">
              {cheapest.candidate.instance_type}
            </div>
            <div className="text-xs text-neutral-300 font-mono">
              ${cheapest.total_cost.toFixed(4)} total • {cheapest.makespan.toFixed(1)}s runtime
            </div>
            <div className="text-[11px] text-neutral-400">
              Minimizes financial expenditure; ideal for non-critical background jobs.
            </div>
          </div>
        )}

        {fastest && (
          <div className="p-4 rounded-xl bg-white/[0.03] border border-sky-500/20 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-sky-400 uppercase tracking-wider">
                Fastest Strategy
              </span>
              <span className="badge-neutral text-[10px]">
                {fastest.candidate.provider.toUpperCase()}
              </span>
            </div>
            <div className="font-mono text-base font-bold text-white truncate">
              {fastest.candidate.instance_type}
            </div>
            <div className="text-xs text-neutral-300 font-mono">
              ${fastest.total_cost.toFixed(4)} total • {fastest.makespan.toFixed(1)}s runtime
            </div>
            <div className="text-[11px] text-neutral-400">
              {hasTimeSavings
                ? `${pctFaster}% faster (${timeDelta.toFixed(1)}s reduction) for +$${costDelta.toFixed(4)}.`
                : 'Maximizes throughput for SLA-critical pipelines.'}
            </div>
          </div>
        )}

        {balanced && (
          <div className="p-4 rounded-xl bg-white/[0.03] border border-purple-500/30 ring-1 ring-purple-500/30 space-y-1.5 bg-purple-950/20">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-purple-300 uppercase tracking-wider">
                Recommended Balance
              </span>
              <span className="badge-success text-[10px]">
                Ideal Tradeoff
              </span>
            </div>
            <div className="font-mono text-base font-bold text-white truncate">
              {balanced.candidate.instance_type}
            </div>
            <div className="text-xs text-neutral-300 font-mono">
              ${balanced.total_cost.toFixed(4)} total • {balanced.makespan.toFixed(1)}s runtime
            </div>
            <div className="text-[11px] text-neutral-300">
              Minimum normalized Euclidean distance to the optimal theoretical (min cost, min time) point.
            </div>
          </div>
        )}
      </div>

      {/* Provider Health Notices */}
      {provider_errors && provider_errors.length > 0 && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2">
          <span>⚠️</span>
          <span>
            Note: Provider pricing API lookups for {provider_errors.join(', ').toUpperCase()} were
            unavailable during this sweep. Results represent active participating clouds.
          </span>
        </div>
      )}
    </div>
  )
}
