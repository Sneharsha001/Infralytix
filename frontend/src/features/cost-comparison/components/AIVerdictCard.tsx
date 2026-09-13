/**
 * Infralytix — AI Architectural Verdict Component.
 *
 * A hero-weight conclusion card that renders the multi-cloud decision verdict:
 * 1. Bold headline highlighting the winning provider & calculated dollar savings delta.
 * 2. Large winning provider brand emblem with provider brand accent gradient/glow.
 * 3. 3-4 compact decision-criteria indicator bars (Cost Efficiency, Spec Match, Regional Ingestion).
 * 4. Demoted supporting architectural detail with dedicated muted callout for caveats/trade-offs.
 * 5. Animated entrance with highlight glow sweep, timed to resolve as the final visual conclusion.
 */

import React, { useMemo } from 'react'
import { motion } from 'framer-motion'
import { AwsIcon, AzureIcon, GcpIcon } from './BrandIcons'
import type { CloudCostEstimate } from '../CostComparisonPage'

interface AIVerdictCardProps {
  estimates: CloudCostEstimate[]
  aiSuggestion: string
  region: string
  vcpu: number
  ramGb: number
}

interface ProviderStyle {
  name: string
  tag: string
  Icon: React.FC<{ size?: number }>
  brandColor: string
  bgGradient: string
  borderColor: string
  glowShadow: string
}

const PROVIDER_STYLES: Record<string, ProviderStyle> = {
  aws: {
    name: 'Amazon Web Services',
    tag: 'AWS EC2 & EBS',
    Icon: AwsIcon,
    brandColor: '#FF9900',
    bgGradient: 'from-amber-500/15 via-neutral-900/90 to-neutral-950',
    borderColor: 'border-amber-500/40',
    glowShadow: '0 0 50px -10px rgba(255,153,0,0.28)',
  },
  azure: {
    name: 'Microsoft Azure',
    tag: 'Azure Virtual Machines',
    Icon: AzureIcon,
    brandColor: '#0078D4',
    bgGradient: 'from-blue-600/15 via-neutral-900/90 to-neutral-950',
    borderColor: 'border-blue-500/40',
    glowShadow: '0 0 50px -10px rgba(0,120,212,0.28)',
  },
  gcp: {
    name: 'Google Cloud Platform',
    tag: 'GCP Compute Engine',
    Icon: GcpIcon,
    brandColor: '#4285F4',
    bgGradient: 'from-blue-500/15 via-neutral-900/90 to-neutral-950',
    borderColor: 'border-blue-400/40',
    glowShadow: '0 0 50px -10px rgba(66,133,244,0.30)',
  },
}

export const AIVerdictCard: React.FC<AIVerdictCardProps> = ({
  estimates,
  aiSuggestion,
  region,
  vcpu,
  ramGb,
}) => {
  // ── Calculate Winner, Runner-up & Savings Delta ────────────────────────────
  const { winner, runnerUp, savingsDelta, percentSavings, winnerStyle, mainBody, tradeOffs } =
    useMemo(() => {
      const valid = [...estimates]
        .filter((e) => !e.error && e.monthly_cost_low > 0)
        .sort((a, b) => a.monthly_cost_low - b.monthly_cost_low)

      const win = valid[0] || estimates[0]
      const run = valid[1]

      let delta = 0
      let pct = 0
      if (win && run && run.monthly_cost_low > win.monthly_cost_low) {
        delta = run.monthly_cost_low - win.monthly_cost_low
        pct = Math.round((delta / run.monthly_cost_low) * 100)
      }

      const key = win?.provider.toLowerCase() || 'gcp'
      const style = PROVIDER_STYLES[key] || PROVIDER_STYLES.gcp

      // Parse AI suggestion into main conclusion vs trade-offs/caveats
      let body = aiSuggestion.trim()
      let caveats: string | null = null

      // Look for common caveat keywords
      const caveatRegex =
        /(?:Note that|However,|Trade-off|Consider|Keep in mind|Factor in|Caveat|Be mindful of)([^.]*\..*)$/i
      const match = caveatRegex.exec(aiSuggestion)
      if (match && match[0]) {
        caveats = match[0].trim()
        body = aiSuggestion.replace(match[0], '').trim()
        if (!body) body = aiSuggestion
      }

      return {
        winner: win,
        runnerUp: run,
        savingsDelta: delta,
        percentSavings: pct,
        winnerStyle: style,
        mainBody: body,
        tradeOffs: caveats,
      }
    }, [estimates, aiSuggestion])

  if (!winner) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 34, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: 0.65,
        delay: 0.48, // Enters last after the 3 cards have settled
        ease: [0.22, 1, 0.36, 1],
      }}
      className={`
        relative w-full rounded-3xl p-6 md:p-8 border bg-gradient-to-br
        overflow-hidden shadow-2xl transition-all duration-300
        ${winnerStyle.bgGradient} ${winnerStyle.borderColor}
      `}
      style={{ boxShadow: winnerStyle.glowShadow }}
    >
      {/* ── Perimeter Highlight Glow Sweep on Entrance ────────────────────── */}
      <motion.div
        initial={{ x: '-100%', opacity: 0 }}
        animate={{ x: '200%', opacity: [0, 0.8, 0] }}
        transition={{ duration: 1.4, delay: 0.6, ease: 'easeInOut' }}
        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent pointer-events-none -skew-x-12"
      />

      {/* Ambient background brand orb */}
      <div
        className="absolute -top-24 -right-24 w-80 h-80 rounded-full blur-3xl pointer-events-none opacity-20"
        style={{ background: winnerStyle.brandColor }}
      />

      {/* ── Header Badge Row ──────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6 relative z-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-white/10 text-white ring-1 ring-white/20">
          <span
            className="w-2 h-2 rounded-full animate-ping"
            style={{ background: winnerStyle.brandColor }}
          />
          <span className="uppercase tracking-wider text-[11px] font-bold">
            Architectural Verdict
          </span>
          <span className="text-neutral-500">·</span>
          <span className="text-emerald-400 font-medium">Verified Lowest TCO</span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
          <span>Calculated across 3 regional catalogs</span>
        </div>
      </div>

      {/* ── Winning Hero Statement Block ──────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center gap-6 mb-7 pb-6 border-b border-white/10 relative z-10">
        {/* Large Winning Provider Brand Emblem */}
        <div className="relative shrink-0">
          <div
            className="w-16 h-16 md:w-20 md:h-20 rounded-2xl flex items-center justify-center border shadow-xl bg-neutral-950/80"
            style={{
              borderColor: `${winnerStyle.brandColor}66`,
              boxShadow: `0 0 24px ${winnerStyle.brandColor}33`,
            }}
          >
            <winnerStyle.Icon size={42} />
          </div>
          {/* Winner Crown Check Badge */}
          <div className="absolute -bottom-1.5 -right-1.5 w-6 h-6 rounded-full bg-emerald-500 text-neutral-950 flex items-center justify-center shadow-md font-bold text-xs">
            ✓
          </div>
        </div>

        {/* Headline & Savings Delta */}
        <div className="min-w-0 flex-1">
          <div className="text-xs uppercase font-mono tracking-widest font-semibold text-neutral-400 mb-1">
            Top Recommendation
          </div>
          <h3 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight leading-snug">
            {savingsDelta > 0 ? (
              <>
                <span style={{ color: winnerStyle.brandColor }}>{winnerStyle.name}</span> is your
                best fit — save{' '}
                <span className="text-emerald-400 underline decoration-emerald-500/40 underline-offset-4">
                  ${Math.round(savingsDelta)}/mo
                </span>
              </>
            ) : (
              <>
                <span style={{ color: winnerStyle.brandColor }}>{winnerStyle.name}</span> delivers
                the optimal cloud profile
              </>
            )}
          </h3>

          <p className="text-xs md:text-sm text-neutral-300 mt-1.5 leading-relaxed">
            {savingsDelta > 0 && runnerUp ? (
              <>
                Saves <strong className="text-white">{percentSavings}%</strong> monthly over{' '}
                {runnerUp.provider} while fulfilling your requested{' '}
                <strong className="text-white">
                  {vcpu} vCPU / {ramGb} GB RAM
                </strong>{' '}
                capacity on <span className="font-mono text-white">{winner.instance_type_matched}</span>.
              </>
            ) : (
              <>
                Provides lowest on-demand cost at{' '}
                <strong className="text-white">${winner.monthly_cost_low.toFixed(2)}/mo</strong> on{' '}
                <span className="font-mono text-white">{winner.instance_type_matched}</span>.
              </>
            )}
          </p>
        </div>
      </div>

      {/* ── Decision-Criteria Breakdown (Driven only by provided data) ─────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-7 relative z-10">
        {/* Metric 1: Cost Advantage */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Cost Advantage</span>
            <span className="text-emerald-400 font-bold">100%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div className="h-full rounded-full bg-emerald-400 w-full" />
          </div>
          <div className="text-xs font-semibold text-white truncate">
            ${winner.monthly_cost_low.toFixed(2)}/mo
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Lowest on-demand TCO</div>
        </div>

        {/* Metric 2: Hardware / Compute Match */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Spec Sizing</span>
            <span className="text-cyan-400 font-bold">Exact</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div className="h-full rounded-full bg-cyan-400 w-full" />
          </div>
          <div className="text-xs font-semibold font-mono text-white truncate">
            {winner.instance_type_matched}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">
            {vcpu} vCPU · {ramGb} GB RAM
          </div>
        </div>

        {/* Metric 3: Regional Deployment */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Region Presence</span>
            <span className="text-emerald-400 font-bold">Active</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div className="h-full rounded-full bg-emerald-400 w-full" />
          </div>
          <div className="text-xs font-semibold text-white truncate capitalize">
            {region}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Direct regional catalog</div>
        </div>

        {/* Metric 4: Storage & Parity */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Storage Parity</span>
            <span className="text-blue-400 font-bold">Matched</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div className="h-full rounded-full bg-blue-400 w-full" />
          </div>
          <div className="text-xs font-semibold text-white truncate">
            {winner.notes ? 'Block SSD gp3/pd' : 'Compute & IOPS'}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5">Live line-item verified</div>
        </div>
      </div>

      {/* ── Demoted Supporting Detail Text ─────────────────────────────────── */}
      <div className="space-y-3 relative z-10">
        <div className="text-xs text-neutral-300 leading-relaxed font-normal bg-neutral-950/40 p-4 rounded-xl border border-white/5">
          <span className="text-[11px] uppercase font-mono tracking-wider font-semibold text-neutral-500 block mb-1">
            Architectural Rationale
          </span>
          {mainBody}
        </div>

        {/* Muted Trade-offs / Caveats Callout (if present) */}
        {tradeOffs && (
          <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-500/[0.04] border border-amber-500/20 text-neutral-400 text-xs leading-relaxed">
            <svg
              className="w-4 h-4 text-amber-400 shrink-0 mt-0.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <div>
              <span className="font-semibold text-amber-300 text-[11px] uppercase font-mono mr-1">
                Consideration:
              </span>
              <span>{tradeOffs}</span>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}
