/**
 * Infralytix — AI Architectural Verdict Component.
 *
 * A hero-weight conclusion card that renders the multi-cloud decision verdict:
 * 1. Consistent currency rounding (exact 2 decimal places in headline and rationale).
 * 2. Proper brand capitalization for all dynamically interpolated provider names.
 * 3. Dynamic Cost Advantage metric driven by actual comparison delta (no hardcoded 100%).
 * 4. Genuinely data-driven decision criteria (Spec Sizing, Region Presence, Storage Parity).
 * 5. Clean separation of supporting architectural rationale and caveats/trade-offs.
 */

import React, { useMemo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
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

/** Normalized brand display name helper */
export const getProviderDisplayName = (provider?: string): string => {
  if (!provider) return ''
  const key = provider.toLowerCase().trim()
  if (key === 'aws') return 'Amazon Web Services'
  if (key === 'azure') return 'Microsoft Azure'
  if (key === 'gcp' || key === 'google' || key === 'google cloud' || key === 'google cloud platform') {
    return 'Google Cloud Platform'
  }
  return provider.toUpperCase()
}

/** Short uppercase brand name helper */
export const getProviderShortName = (provider?: string): string => {
  if (!provider) return ''
  const key = provider.toLowerCase().trim()
  if (key === 'aws') return 'AWS'
  if (key === 'azure') return 'Azure'
  if (key === 'gcp' || key === 'google' || key === 'google cloud' || key === 'google cloud platform') {
    return 'GCP'
  }
  return provider.toUpperCase()
}

/** Format region value into human-readable label */
const formatRegionLabel = (regionCode: string): string => {
  const map: Record<string, string> = {
    'us-east': 'US East',
    'us-west': 'US West',
    'eu-west': 'Europe West',
    'us': 'US Central',
    'eu': 'Europe',
    'asia': 'Asia Pacific',
  }
  return map[regionCode.toLowerCase()] || regionCode.toUpperCase()
}

/** Hardware spec parser to evaluate exact vs approximate match */
interface HardwareSpec {
  vcpus: number
  ramGb: number
}

function parseInstanceHardware(sku: string): HardwareSpec | null {
  const s = sku.toLowerCase().trim()

  // GCP standard naming: e2-standard-4, n2-standard-8, c2-standard-4
  const gcpStd = /(?:e2|n2|c2)-standard-(\d+)/.exec(s)
  if (gcpStd) {
    const v = parseInt(gcpStd[1], 10)
    return { vcpus: v, ramGb: v * 4 }
  }
  const gcpHighMem = /(?:e2|n2)-highmem-(\d+)/.exec(s)
  if (gcpHighMem) {
    const v = parseInt(gcpHighMem[1], 10)
    return { vcpus: v, ramGb: v * 8 }
  }
  const gcpHighCpu = /(?:e2|n2)-highcpu-(\d+)/.exec(s)
  if (gcpHighCpu) {
    const v = parseInt(gcpHighCpu[1], 10)
    return { vcpus: v, ramGb: v * 1 }
  }
  if (s === 'e2-micro') return { vcpus: 2, ramGb: 1 }
  if (s === 'e2-small') return { vcpus: 2, ramGb: 2 }
  if (s === 'e2-medium') return { vcpus: 2, ramGb: 4 }

  // AWS standard naming: t3.xlarge, t4g.2xlarge, m6i.large, c6i.xlarge
  const awsXLarge = /[a-z0-9]+\.(\d+)?xlarge/.exec(s)
  if (awsXLarge) {
    const mult = awsXLarge[1] ? parseInt(awsXLarge[1], 10) : 1
    const v = mult * 4
    const isCompute = s.startsWith('c')
    const isMemory = s.startsWith('r')
    const r = isCompute ? v * 2 : isMemory ? v * 8 : v * 4
    return { vcpus: v, ramGb: r }
  }
  if (s.endsWith('.large')) {
    const isCompute = s.startsWith('c')
    const isMemory = s.startsWith('r')
    return { vcpus: 2, ramGb: isCompute ? 4 : isMemory ? 16 : 8 }
  }
  if (s.endsWith('.medium')) return { vcpus: 2, ramGb: 4 }
  if (s.endsWith('.small')) return { vcpus: 2, ramGb: 2 }
  if (s.endsWith('.micro')) return { vcpus: 2, ramGb: 1 }
  if (s.endsWith('.nano')) return { vcpus: 2, ramGb: 0.5 }

  // Azure standard naming: Standard_D4s_v5, Standard_B2s, Standard_F4s_v2
  const azMatch = /standard_([a-z])(\d+)(m?s)?/i.exec(s)
  if (azMatch) {
    const series = azMatch[1].toUpperCase()
    const v = parseInt(azMatch[2], 10)
    const isMemory = series === 'E'
    const isCompute = series === 'F'
    const r = isMemory ? v * 8 : isCompute ? v * 2 : v * 4
    return { vcpus: v, ramGb: r }
  }

  return null
}

export const AIVerdictCard: React.FC<AIVerdictCardProps> = ({
  estimates,
  aiSuggestion,
  region,
  vcpu,
  ramGb,
}) => {
  // ── Calculate Winner, Runner-up & Savings Delta ────────────────────────────
  const {
    winner,
    runnerUp,
    savingsDelta,
    formattedSavings,
    winnerStyle,
    winnerDisplayName,
    runnerUpDisplayName,
    mainBody,
    tradeOffs,
    costAdvantage,
    specCriteria,
    regionCriteria,
    storageCriteria,
  } = useMemo(() => {
    const valid = [...estimates]
      .filter((e) => !e.error && e.monthly_cost_low > 0)
      .sort((a, b) => a.monthly_cost_low - b.monthly_cost_low)

    const win = valid[0] || estimates[0]
    const run = valid[1]

    let delta = 0
    if (win && run && run.monthly_cost_low > win.monthly_cost_low) {
      delta = run.monthly_cost_low - win.monthly_cost_low
    }

    // Exact formatted currency value derived once for consistency
    const savingsStr = delta > 0 ? delta.toFixed(2) : '0.00'

    const key = win?.provider.toLowerCase() || 'gcp'
    const style = PROVIDER_STYLES[key] || PROVIDER_STYLES.gcp
    const winName = getProviderDisplayName(win?.provider)
    const runName = getProviderDisplayName(run?.provider)
    const runShort = getProviderShortName(run?.provider)

    // ── Metric 1: Cost Advantage (Calculated dynamically from real data) ───
    let costBadge = '0.0%'
    let costBar = 0
    let costSubtext = 'Equal pricing across providers'
    let costValue = `$${win.monthly_cost_low.toFixed(2)}/mo`

    if (delta > 0 && run && run.monthly_cost_low > 0) {
      const pct = ((delta / run.monthly_cost_low) * 100)
      costBadge = `+${pct.toFixed(1)}%`
      costBar = Math.min(Math.max(Math.round(pct), 10), 100)
      costValue = `-$${savingsStr}/mo`
      costSubtext = `Save $${savingsStr}/mo vs ${runShort}`
    } else if (valid.length === 1) {
      costBadge = 'Best Rate'
      costBar = 100
      costSubtext = 'Sole available catalog match'
    }

    // ── Metric 2: Spec Sizing (Conditional on parsed hardware vs requested) ─
    const parsedHw = parseInstanceHardware(win.instance_type_matched)
    let specBadge = 'Exact'
    let specBar = 100
    const specValue = win.instance_type_matched
    let specSubtext = `100% matched to ${vcpu}v / ${ramGb}GB`

    if (parsedHw) {
      const vcpuDiff = parsedHw.vcpus - vcpu
      const ramDiff = parsedHw.ramGb - ramGb
      if (vcpuDiff === 0 && Math.abs(ramDiff) <= 0.5) {
        specBadge = 'Exact'
        specBar = 100
        specSubtext = `Exact ${parsedHw.vcpus} vCPU · ${parsedHw.ramGb} GB RAM`
      } else if (vcpuDiff >= 0 && ramDiff >= 0) {
        specBadge = '+Headroom'
        specBar = 100
        specSubtext = `Includes headroom (${parsedHw.vcpus}v / ${parsedHw.ramGb}GB)`
      } else {
        specBadge = 'Approximate'
        specBar = 80
        specSubtext = `Closest match (${parsedHw.vcpus}v / ${parsedHw.ramGb}GB)`
      }
    } else {
      if (win.instance_type_matched === 'unavailable' || win.error) {
        specBadge = 'No Match'
        specBar = 0
        specSubtext = 'No instance met requirements'
      } else {
        specBadge = 'Approximate'
        specBar = 85
        specSubtext = `${vcpu} vCPU / ${ramGb} GB target`
      }
    }

    // ── Metric 3: Region Presence (Conditional on notes & catalog type) ─────
    const notesLower = (win.notes || '').toLowerCase()
    let regionBadge = 'Live API'
    let regionBar = 100
    let regionValue = formatRegionLabel(region)
    let regionSubtext = 'Direct regional catalog ingest'

    const regionMatch = /Region:\s*([a-zA-Z0-9_-]+)/i.exec(win.notes || '')
    if (regionMatch && regionMatch[1]) {
      regionValue = regionMatch[1]
    }

    if (notesLower.includes('reference') || notesLower.includes('static')) {
      regionBadge = 'Reference'
      regionBar = 60
      regionSubtext = 'Static pricing dataset'
    } else if (win.error) {
      regionBadge = 'Offline'
      regionBar = 0
      regionSubtext = 'Region unavailable'
    }

    // ── Metric 4: Storage Parity (Conditional on notes & requested volume) ─
    let storageBadge = 'Not Req.'
    let storageBar = 40
    let storageValue = 'Compute Only'
    let storageSubtext = '0 GB volume specified'

    if (notesLower.includes('storage:')) {
      storageBadge = 'Included'
      storageBar = 100
      storageSubtext = 'Block storage item verified'
      if (notesLower.includes('gp3')) {
        storageValue = 'EBS gp3'
      } else if (notesLower.includes('premium ssd')) {
        storageValue = 'Premium SSD'
      } else if (notesLower.includes('pd-balanced')) {
        storageValue = 'pd-balanced'
      } else {
        storageValue = 'Block SSD'
      }
    }

    // ── Parse AI suggestion into main conclusion vs trade-offs/caveats ─────
    let body = aiSuggestion.trim()
    let caveats: string | null = null

    // Ensure proper brand name capitalization within suggestion body
    body = body
      .replace(/\baws\b/g, 'AWS')
      .replace(/\bgcp\b/g, 'GCP')
      .replace(/\bazure\b/g, 'Azure')

    const caveatRegex =
      /(?:Note that|However,|Trade-off|Consider|Keep in mind|Factor in|Caveat|Be mindful of)([^.]*\..*)$/i
    const match = caveatRegex.exec(body)
    if (match && match[0]) {
      caveats = match[0].trim()
      body = body.replace(match[0], '').trim()
      if (!body) body = aiSuggestion
    }

    return {
      winner: win,
      runnerUp: run,
      savingsDelta: delta,
      formattedSavings: savingsStr,
      winnerStyle: style,
      winnerDisplayName: winName,
      runnerUpDisplayName: runName,
      runnerUpShortName: runShort,
      mainBody: body,
      tradeOffs: caveats,
      costAdvantage: { badge: costBadge, bar: costBar, value: costValue, subtext: costSubtext },
      specCriteria: { badge: specBadge, bar: specBar, value: specValue, subtext: specSubtext },
      regionCriteria: { badge: regionBadge, bar: regionBar, value: regionValue, subtext: regionSubtext },
      storageCriteria: { badge: storageBadge, bar: storageBar, value: storageValue, subtext: storageSubtext },
    }
  }, [estimates, aiSuggestion, region, vcpu, ramGb])

  const shouldReduce = useReducedMotion()

  if (!winner) return null

  return (
    <motion.div
      initial={shouldReduce ? { opacity: 1, y: 0, scale: 1 } : { opacity: 0, y: 34, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        duration: shouldReduce ? 0 : 0.65,
        delay: shouldReduce ? 0 : 0.48, // Enters last after the 3 cards have settled
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
      {!shouldReduce && (
        <motion.div
          initial={{ x: '-100%', opacity: 0 }}
          animate={{ x: '200%', opacity: [0, 0.8, 0] }}
          transition={{ duration: 1.4, delay: 0.6, ease: 'easeInOut' }}
          className="absolute inset-0 bg-gradient-to-r from-transparent via-white/15 to-transparent pointer-events-none -skew-x-12"
        />
      )}

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
          <span className="text-[var(--color-success)] font-medium">Verified Lowest TCO</span>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-neutral-400">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)]" />
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
          <div className="absolute -bottom-1.5 -right-1.5 w-6 h-6 rounded-full bg-[var(--color-success)] text-neutral-950 flex items-center justify-center shadow-md font-bold text-xs">
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
                <span style={{ color: winnerStyle.brandColor }}>{winnerDisplayName}</span> is your
                best fit — save{' '}
                <span className="text-[var(--color-success)] underline decoration-[var(--color-success)]/40 underline-offset-4">
                  ${formattedSavings}/mo
                </span>
              </>
            ) : (
              <>
                <span style={{ color: winnerStyle.brandColor }}>{winnerDisplayName}</span> delivers
                the optimal cloud profile
              </>
            )}
          </h3>

          <p className="text-xs md:text-sm text-neutral-300 mt-1.5 leading-relaxed">
            {savingsDelta > 0 && runnerUp ? (
              <>
                Saves <strong className="text-white">${formattedSavings}/mo</strong> over{' '}
                <strong className="text-white">{runnerUpDisplayName}</strong> while fulfilling your
                requested{' '}
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

      {/* ── Decision-Criteria Breakdown (Driven genuinely by data) ─────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-7 relative z-10">
        {/* Metric 1: Cost Advantage */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Cost Advantage</span>
            <span className="text-[var(--color-success)] font-bold">{costAdvantage.badge}</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div
              className="h-full rounded-full bg-[var(--color-success)] transition-all duration-500"
              style={{ width: `${costAdvantage.bar}%` }}
            />
          </div>
          <div className="text-xs font-semibold text-white truncate">
            {costAdvantage.value}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5 truncate">
            {costAdvantage.subtext}
          </div>
        </div>

        {/* Metric 2: Hardware / Compute Match */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Spec Sizing</span>
            <span className="text-cyan-400 font-bold">{specCriteria.badge}</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div
              className="h-full rounded-full bg-cyan-400 transition-all duration-500"
              style={{ width: `${specCriteria.bar}%` }}
            />
          </div>
          <div className="text-xs font-semibold font-mono text-white truncate">
            {specCriteria.value}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5 truncate">
            {specCriteria.subtext}
          </div>
        </div>

        {/* Metric 3: Regional Deployment */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Region Presence</span>
            <span
              className={`font-bold ${
                regionCriteria.badge === 'Live API' ? 'text-[var(--color-success)]' : 'text-amber-400'
              }`}
            >
              {regionCriteria.badge}
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                regionCriteria.badge === 'Live API' ? 'bg-[var(--color-success)]' : 'bg-amber-400'
              }`}
              style={{ width: `${regionCriteria.bar}%` }}
            />
          </div>
          <div className="text-xs font-semibold text-white truncate">
            {regionCriteria.value}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5 truncate">
            {regionCriteria.subtext}
          </div>
        </div>

        {/* Metric 4: Storage & Parity */}
        <div className="p-3.5 rounded-xl bg-white/[0.03] border border-white/10">
          <div className="flex items-center justify-between text-[11px] font-mono text-neutral-400 mb-1.5">
            <span>Storage Parity</span>
            <span
              className={`font-bold ${
                storageCriteria.badge === 'Included' ? 'text-blue-400' : 'text-neutral-400'
              }`}
            >
              {storageCriteria.badge}
            </span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-white/10 overflow-hidden mb-1.5">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                storageCriteria.badge === 'Included' ? 'bg-blue-400' : 'bg-neutral-600'
              }`}
              style={{ width: `${storageCriteria.bar}%` }}
            />
          </div>
          <div className="text-xs font-semibold text-white truncate">
            {storageCriteria.value}
          </div>
          <div className="text-[10px] text-neutral-500 mt-0.5 truncate">
            {storageCriteria.subtext}
          </div>
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
