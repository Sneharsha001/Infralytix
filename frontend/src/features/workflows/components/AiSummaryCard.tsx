/**
 * Infralytix — AI Summary Card Component.
 *
 * Hero-style result panel for the winning workflow optimization strategies.
 * Displays brand icon, animated count-up cost/time figures, and Framer Motion
 * fade+scale reveal — matching the Cost Comparison card design language.
 */

import React, { useRef, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { SiGooglecloud } from 'react-icons/si'
import { WorkflowOptimizeResult } from '../types'

// ─── Inline brand SVGs (same as CostComparisonPage) ─────────────────────────

const AwsIcon: React.FC<{ size?: number }> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 100 100" fill="none">
    <path d="M28.7 40.3c0 1.4.2 2.6.5 3.4.4.9.9 1.8 1.6 2.8.3.4.4.8.4 1.2 0 .5-.3 1.1-.9 1.6l-3 2c-.4.3-.8.4-1.2.4-.5 0-1-.2-1.4-.6-.7-.7-1.3-1.5-1.8-2.3-.5-.8-1-1.8-1.6-3-.4-.8-1-1.4-1.8-1.8-1.8 3.1-4.3 4.6-7.5 4.6-2.1 0-3.9-.6-5.1-1.9-1.3-1.3-1.9-3-1.9-5.1 0-2.3.8-4.1 2.4-5.6 1.6-1.4 3.8-2.1 6.6-2.1.9 0 1.9.1 2.9.2 1 .2 2 .4 3.1.7v-2c0-2-.4-3.4-1.3-4.2-.9-.9-2.4-1.3-4.6-1.3-1 0-2 .1-3 .4-1 .3-2 .6-3 1.1-.4.2-.8.3-1 .3-.5 0-.8-.4-.8-.9V27c0-.5.1-.9.3-1.1.2-.2.6-.4 1.1-.6 1-.5 2.2-.9 3.6-1.2 1.4-.3 2.9-.5 4.5-.5 3.4 0 5.9.8 7.5 2.3 1.6 1.5 2.4 3.8 2.4 6.9v9.5zm-10.4 3.9c.9 0 1.8-.2 2.8-.5 1-.3 1.9-.9 2.6-1.7.4-.5.7-1 .9-1.6.2-.6.3-1.3.3-2.2v-1.1c-.8-.2-1.6-.3-2.4-.4-.8-.1-1.6-.2-2.4-.2-1.7 0-2.9.3-3.7 1-.8.7-1.2 1.7-1.2 3 0 1.2.3 2.1.9 2.7.6.7 1.5 1 2.2 1zm20.1 2.7c-.6 0-1-.1-1.2-.4-.3-.3-.5-.8-.7-1.4L30 20.3c-.2-.7-.3-1.2-.3-1.4 0-.6.3-.9.9-.9h3.5c.6 0 1 .1 1.2.4.3.3.5.8.7 1.4l5.8 22.9 5.4-22.9c.2-.7.4-1.1.7-1.4.3-.3.7-.4 1.3-.4h2.9c.6 0 1 .1 1.3.4.3.3.5.8.7 1.4l5.5 23.2L65 19.8c.2-.7.4-1.1.7-1.4.3-.3.7-.4 1.2-.4h3.3c.6 0 .9.3.9.9 0 .2 0 .4-.1.6l-.2.8-7.7 25.2c-.2.7-.4 1.1-.7 1.4-.3.3-.7.4-1.2.4h-3.1c-.6 0-1-.1-1.3-.4-.3-.3-.5-.8-.7-1.4l-5.4-22.5-5.4 22.5c-.2.7-.4 1.1-.7 1.4-.3.3-.7.4-1.3.4h-3.1zm41.1.9c-1.9 0-3.8-.2-5.6-.7-1.8-.5-3.2-1-4.1-1.6-.6-.3-.9-.7-.9-1.2V43c0-.5.2-.9.7-.9.2 0 .4.1.7.2.2.1.5.2.8.4.9.4 1.9.8 3 1.1 1.1.3 2.2.4 3.3.4 1.7 0 3-.3 3.9-.9.9-.6 1.3-1.4 1.3-2.4 0-.7-.2-1.3-.7-1.8-.5-.5-1.4-1-2.7-1.4l-3.9-1.2c-2-.6-3.4-1.5-4.3-2.7-.9-1.2-1.4-2.6-1.4-4 0-1.2.3-2.2.8-3.1.5-.9 1.2-1.7 2-2.3.8-.6 1.8-1.1 2.9-1.4 1.1-.3 2.3-.5 3.5-.5.6 0 1.2.1 1.8.1.6.1 1.2.2 1.7.3.5.1 1 .3 1.5.4.5.2.9.3 1.2.5.4.2.7.4.8.7.2.2.2.5.2.9v2.1c0 .5-.2.9-.7.9-.3 0-.6-.1-1.1-.3-1.7-.7-3.5-1.1-5.5-1.1-1.5 0-2.7.2-3.5.7-.8.5-1.2 1.2-1.2 2.2 0 .7.2 1.3.7 1.8.5.5 1.5 1 3 1.5l3.8 1.2c2 .6 3.4 1.5 4.2 2.6.8 1.1 1.2 2.4 1.2 3.8 0 1.2-.2 2.3-.7 3.3-.5 1-1.2 1.8-2 2.5-.9.7-1.9 1.2-3 1.6-1.3.3-2.5.5-3.8.5z" fill="#FF9900"/>
    <path d="M83.2 57.9C73.4 65.1 59.4 69 47.4 69c-16.7 0-31.8-6.2-43.2-16.4-1-.9-.1-2.1 1.1-1.4C17 57.8 31.5 62 46.4 62c10.1 0 21.2-2.1 31.4-6.4 1.5-.7 2.8 1 1.4 2.3z" fill="#FF9900"/>
    <path d="M87.3 53.3c-1.3-1.7-8.7-1.2-12.1-.6-.9.1-1-.6-.2-1.2 5.9-4.1 15.6-2.9 16.7-1.6 1.1 1.4-.3 10.9-5.8 15.4-.8.7-1.6.3-1.3-.6 1.3-3.1 4-10 2.7-11.4z" fill="#FF9900"/>
  </svg>
)

const AzureIcon: React.FC<{ size?: number }> = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 96 96" fill="none">
    <defs>
      <linearGradient id="az-sum-a" x1="-1032.17" y1="145.31" x2="-1059.17" y2="65.31" gradientTransform="matrix(1 0 0 -1 1075 158)" gradientUnits="userSpaceOnUse">
        <stop offset="0" stopColor="#114A8B"/>
        <stop offset="1" stopColor="#0669BC"/>
      </linearGradient>
      <linearGradient id="az-sum-b" x1="-1023.73" y1="108.08" x2="-1029.98" y2="105.98" gradientTransform="matrix(1 0 0 -1 1075 158)" gradientUnits="userSpaceOnUse">
        <stop offset="0" stopOpacity=".3"/>
        <stop offset=".071" stopOpacity=".2"/>
        <stop offset=".321" stopOpacity=".1"/>
        <stop offset=".623" stopOpacity=".05"/>
        <stop offset="1" stopOpacity="0"/>
      </linearGradient>
      <linearGradient id="az-sum-c" x1="-1027.16" y1="147.64" x2="-997.48" y2="68.56" gradientTransform="matrix(1 0 0 -1 1075 158)" gradientUnits="userSpaceOnUse">
        <stop offset="0" stopColor="#3CCBF4"/>
        <stop offset="1" stopColor="#2892DF"/>
      </linearGradient>
    </defs>
    <path d="M33.34 6.54h26.04L32.84 89.9a4.14 4.14 0 01-3.93 2.83H8.78a4.14 4.14 0 01-3.92-5.46L29.42 9.37a4.14 4.14 0 013.93-2.83z" fill="url(#az-sum-a)"/>
    <path d="M71.17 60.26H29.88a1.91 1.91 0 00-1.3 3.31l26.53 24.78a4.17 4.17 0 002.85 1.12h23.38z" fill="url(#az-sum-b)"/>
    <path d="M33.34 6.54a4.1 4.1 0 00-3.95 2.88L4.9 87.22a4.13 4.13 0 003.91 5.51h20.56a4.44 4.44 0 003.4-2.88l4.96-14.63 17.76 16.6a4.24 4.24 0 002.76 1h24.1l-10.57-30.26-30.82.01L59.37 6.54z" fill="url(#az-sum-c)"/>
    <path d="M66.6 9.36a4.13 4.13 0 00-3.93-2.82H33.65a4.13 4.13 0 013.93 2.82l24.56 77.91a4.14 4.14 0 01-3.93 5.46h29.02a4.14 4.14 0 003.93-5.46z" fill="#0078D4"/>
  </svg>
)

// ─── Provider brand metadata ─────────────────────────────────────────────────

const PROVIDER_META: Record<string, {
  name: string
  Icon: React.FC<{ size?: number }>
  iconColor: string
  accentClass: string
  glowColor: string
}> = {
  aws: {
    name: 'Amazon Web Services',
    Icon: AwsIcon,
    iconColor: '#FF9900',
    accentClass: 'border-amber-500/40 bg-amber-950/20',
    glowColor: 'rgba(255,153,0,0.15)',
  },
  azure: {
    name: 'Microsoft Azure',
    Icon: AzureIcon,
    iconColor: '#0089D6',
    accentClass: 'border-sky-500/40 bg-sky-950/20',
    glowColor: 'rgba(0,137,214,0.15)',
  },
  gcp: {
    name: 'Google Cloud Platform',
    Icon: ({ size = 20 }) => <SiGooglecloud size={size} />,
    iconColor: '#4285F4',
    accentClass: 'border-blue-500/40 bg-blue-950/20',
    glowColor: 'rgba(66,133,244,0.15)',
  },
}

// ─── Count-up animation hook (same as CostComparisonPage) ───────────────────

function usePriceCounter(target: number, durationMs = 700): number {
  const [display, setDisplay] = useState(0)
  const rafRef = useRef<number>(0)
  const startRef = useRef<number | null>(null)

  useEffect(() => {
    startRef.current = null
    const animate = (ts: number) => {
      if (startRef.current === null) startRef.current = ts
      const elapsed = ts - startRef.current
      const progress = Math.min(elapsed / durationMs, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(eased * target)
      if (progress < 1) rafRef.current = requestAnimationFrame(animate)
      else setDisplay(target)
    }
    rafRef.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, durationMs])

  return display
}

// ─── Individual strategy hero card ──────────────────────────────────────────

interface StrategyCardProps {
  label: string
  labelColor: string
  borderClass: string
  candidate: { provider: string; instance_type: string }
  cost: number
  makespan: number
  description: string
  delay: number
  isFeatured?: boolean
  badge?: React.ReactNode
}

const StrategyCard: React.FC<StrategyCardProps> = ({
  label, labelColor, borderClass, candidate, cost, makespan, description, delay, isFeatured, badge,
}) => {
  const animatedCost = usePriceCounter(cost, 800)
  const animatedMakespan = usePriceCounter(makespan, 800)
  const providerKey = candidate.provider.toLowerCase()
  const meta = PROVIDER_META[providerKey] ?? PROVIDER_META['aws']

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
      className={[
        'relative p-4 rounded-xl border backdrop-blur-sm space-y-2 overflow-hidden',
        isFeatured
          ? 'border-purple-500/40 bg-purple-950/20 ring-1 ring-purple-500/30'
          : borderClass,
      ].join(' ')}
      style={{ boxShadow: isFeatured ? '0 0 24px -4px rgba(168,85,247,0.2)' : undefined }}
    >
      {/* Provider icon chip */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
            style={{ background: `${meta.iconColor}1A` }}
          >
            <meta.Icon size={18} />
          </div>
          <div>
            <div className="text-[9px] uppercase tracking-widest text-neutral-500 font-semibold leading-none">
              {candidate.provider.toUpperCase()}
            </div>
            <div className="text-[11px] text-neutral-300 font-medium leading-snug">
              {meta.name}
            </div>
          </div>
        </div>
        {badge}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: labelColor }}>
          {label}
        </span>
      </div>

      {/* Instance type */}
      <div className="font-mono text-sm font-bold text-white truncate">
        {candidate.instance_type}
      </div>

      {/* Animated cost/time */}
      <div className="flex items-baseline gap-3 pt-1 border-t border-white/[0.07]">
        <div>
          <div className="text-[9px] text-neutral-500 uppercase tracking-wider">Cost</div>
          <div className="text-xl font-extrabold text-emerald-300 font-mono">
            ${animatedCost.toFixed(4)}
          </div>
        </div>
        <div className="text-neutral-700 text-lg font-light">·</div>
        <div>
          <div className="text-[9px] text-neutral-500 uppercase tracking-wider">Makespan</div>
          <div className="text-xl font-extrabold text-sky-300 font-mono">
            {animatedMakespan >= 60
              ? `${(animatedMakespan / 60).toFixed(1)}m`
              : `${animatedMakespan.toFixed(1)}s`}
          </div>
        </div>
      </div>

      <div className="text-[11px] text-neutral-400 leading-relaxed">{description}</div>
    </motion.div>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

interface AiSummaryCardProps {
  result: WorkflowOptimizeResult
}

export const AiSummaryCard: React.FC<AiSummaryCardProps> = ({ result }) => {
  const { pareto_front, ai_summary, candidates_evaluated, provider_errors } = result

  const cheapest = pareto_front.find((p) => p.label?.includes('Cheapest')) || pareto_front[0]
  const fastest =
    pareto_front.find((p) => p.label?.includes('Fastest')) || pareto_front[pareto_front.length - 1]
  const balanced = pareto_front.find((p) => p.label?.includes('Best balance')) || pareto_front[0]

  const hasCostSavings = fastest && cheapest && fastest.total_cost > cheapest.total_cost
  const hasTimeSavings = fastest && cheapest && cheapest.makespan > fastest.makespan
  const timeDelta = hasTimeSavings ? cheapest.makespan - fastest.makespan : 0
  const costDelta = hasCostSavings ? fastest.total_cost - cheapest.total_cost : 0
  const pctFaster = hasTimeSavings && cheapest
    ? ((timeDelta / cheapest.makespan) * 100).toFixed(0)
    : '0'

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="glass-card p-6 md:p-8 border-brand-500/30 bg-brand-950/15 relative overflow-hidden shadow-2xl rounded-2xl space-y-6"
    >
      {/* Decorative background glow */}
      <div className="absolute top-0 right-0 w-72 h-72 bg-brand-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 pb-4 relative z-10">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-brand-400 animate-ping" />
          <span className="badge-info text-xs font-semibold">
            AI Pareto Frontier &amp; Multi-Cloud Trade-off Analysis
          </span>
        </div>
        <div className="text-xs text-neutral-400">
          {candidates_evaluated} candidates evaluated &bull; {pareto_front.length} non-dominated
        </div>
      </div>

      {/* AI narrative */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2, duration: 0.5 }}
        className="relative z-10"
      >
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
      </motion.div>

      {/* Three strategy hero cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 relative z-10">
        {cheapest && (
          <StrategyCard
            label="Cheapest Strategy"
            labelColor="#f59e0b"
            borderClass="border-amber-500/30 bg-white/[0.02]"
            candidate={cheapest.candidate}
            cost={cheapest.total_cost}
            makespan={cheapest.makespan}
            description="Minimizes financial expenditure; ideal for non-critical background jobs."
            delay={0.1}
          />
        )}

        {fastest && (
          <StrategyCard
            label="Fastest Strategy"
            labelColor="#38bdf8"
            borderClass="border-sky-500/30 bg-white/[0.02]"
            candidate={fastest.candidate}
            cost={fastest.total_cost}
            makespan={fastest.makespan}
            description={
              hasTimeSavings
                ? `${pctFaster}% faster (−${timeDelta.toFixed(1)}s) for +$${costDelta.toFixed(4)} vs cheapest.`
                : 'Maximizes throughput for SLA-critical pipelines.'
            }
            delay={0.2}
          />
        )}

        {balanced && (
          <StrategyCard
            label="Recommended Balance"
            labelColor="#c084fc"
            borderClass="border-purple-500/30 bg-white/[0.02]"
            candidate={balanced.candidate}
            cost={balanced.total_cost}
            makespan={balanced.makespan}
            description="Minimum normalized Euclidean distance to optimal (min cost, min time)."
            delay={0.3}
            isFeatured
            badge={
              <span className="badge-success text-[10px] shrink-0">Ideal Tradeoff</span>
            }
          />
        )}
      </div>

      {/* Provider health notice */}
      <AnimatePresence>
        {provider_errors && provider_errors.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs flex items-center gap-2 relative z-10"
          >
            <span>⚠️</span>
            <span>
              Note: Provider pricing API lookups for {provider_errors.join(', ').toUpperCase()} were
              unavailable during this sweep. Results represent active participating clouds.
            </span>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}
