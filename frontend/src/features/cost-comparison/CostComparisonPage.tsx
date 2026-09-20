/**
 * Infralytix — Multi-Cloud Cost Comparison Page.
 *
 * Provides a live interactive form to configure compute and storage workloads,
 * queries POST /api/v1/cost-comparison concurrently across AWS, Azure, and GCP,
 * and renders comparative cards sorted cheapest-first alongside Gemini AI recommendations.
 *
 * Accepts optional React Router `state` from WorkloadUploadPage to pre-fill form
 * fields with AI-inferred workload values.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { useLocation } from 'react-router-dom'
import { apiClient } from '@/lib/api-client'
import { PublicNav } from '@/components/layout'
import type { WorkloadInferenceRouteState } from '@/features/workload-upload/types'
import { AwsIcon, AzureIcon, GcpIcon } from './components/BrandIcons'
import { CloudQueryingHero } from './components/CloudQueryingHero'
import { AIVerdictCard } from './components/AIVerdictCard'

export interface CloudCostEstimate {
  provider: string
  instance_type_matched: string
  monthly_cost_low: number
  monthly_cost_high: number
  currency: string
  notes: string | null
  error: string | null
}

export interface CloudComparisonResponse {
  estimates: CloudCostEstimate[]
  ai_suggestion: string
}

interface FormState {
  vcpu: number
  ram_gb: number
  storage_gb: number
  region: string
  hours_per_month: number
}

const REGION_OPTIONS = [
  { value: 'us-east', label: 'US East (N. Virginia — us-east-1 / eastus / us-east4)' },
  { value: 'us-west', label: 'US West (Oregon — us-west-2 / westus2 / us-west1)' },
  { value: 'eu-west', label: 'Europe West (Ireland / Frankfurt — eu-west-1 / westeurope)' },
  { value: 'us', label: 'US Central (Iowa / Default US)' },
  { value: 'eu', label: 'Europe (Default EU Datacenters)' },
  { value: 'asia', label: 'Asia Pacific (Singapore / Taiwan / Tokyo)' },
]

// ─── Provider brand metadata ─────────────────────────────────────────────────

const PROVIDER_META: Record<
  string,
  {
    name: string
    tag: string
    Icon: React.FC<{ size?: number }>
    iconColor: string
    borderGradient: string
    hoverShadow: string
  }
> = {
  aws: {
    name: 'Amazon Web Services',
    tag: 'AWS EC2',
    Icon: AwsIcon,
    iconColor: '#FF9900',
    borderGradient: 'provider-border-aws',
    hoverShadow: '0 8px 32px -4px rgba(255,153,0,0.22)',
  },
  azure: {
    name: 'Microsoft Azure',
    tag: 'Azure VMs',
    Icon: AzureIcon,
    iconColor: '#0089D6',
    borderGradient: 'provider-border-azure',
    hoverShadow: '0 8px 32px -4px rgba(0,137,214,0.22)',
  },
  gcp: {
    name: 'Google Cloud Platform',
    tag: 'GCP Compute',
    Icon: GcpIcon,
    iconColor: '#4285F4',
    borderGradient: 'provider-border-gcp',
    hoverShadow: '0 8px 32px -4px rgba(66,133,244,0.22)',
  },
}

// ─── Animated price counter ───────────────────────────────────────────────────

function usePriceCounter(target: number, durationMs = 700, delayMs = 0): number {
  const shouldReduce = useReducedMotion()
  const [display, setDisplay] = useState(shouldReduce ? target : 0)
  const rafRef = useRef<number>(0)
  const startRef = useRef<number | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (shouldReduce) {
      setDisplay(target)
      return
    }

    setDisplay(0)
    startRef.current = null

    const runAnimation = () => {
      const animate = (timestamp: number) => {
        if (startRef.current === null) startRef.current = timestamp
        const elapsed = timestamp - startRef.current
        const progress = Math.min(elapsed / durationMs, 1)
        const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
        setDisplay(eased * target)
        if (progress < 1) rafRef.current = requestAnimationFrame(animate)
        else setDisplay(target)
      }
      rafRef.current = requestAnimationFrame(animate)
    }

    if (delayMs > 0) {
      timerRef.current = setTimeout(runAnimation, delayMs)
    } else {
      runAnimation()
    }

    return () => {
      cancelAnimationFrame(rafRef.current)
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [target, durationMs, delayMs, shouldReduce])

  return shouldReduce ? target : display
}

const AnimatedPrice: React.FC<{ value: number; delayMs?: number }> = ({ value, delayMs = 0 }) => {
  const displayed = usePriceCounter(value, 700, delayMs)
  return <>{displayed.toFixed(2)}</>
}

// ─── Field Info Tooltip Component ─────────────────────────────────────────────

interface FieldTooltipProps {
  label: string
  content: string
}

const FieldTooltip: React.FC<FieldTooltipProps> = ({ label, content }) => {
  const [isOpen, setIsOpen] = useState(false)

  return (
    <span className="relative inline-flex items-center ml-1.5">
      <button
        type="button"
        aria-label={`Information regarding ${label}`}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setIsOpen(false)}
        className="w-3.5 h-3.5 rounded-full bg-white/10 hover:bg-[var(--color-accent-primary)]/25 text-neutral-400 hover:text-white text-[10px] font-mono flex items-center justify-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)] focus-visible:ring-offset-1 focus-visible:ring-offset-neutral-950"
      >
        i
      </button>

      {isOpen && (
        <div
          role="tooltip"
          className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-64 p-2.5 rounded-xl bg-neutral-900/95 border border-white/15 text-[11px] leading-relaxed text-neutral-200 shadow-2xl backdrop-blur-md z-30 pointer-events-none"
        >
          {content}
          <span className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-x-4 border-x-transparent border-t-4 border-t-neutral-900/95" />
        </div>
      )}
    </span>
  )
}

export const CostComparisonPage: React.FC = () => {
  const location = useLocation()
  const inferredState = location.state as WorkloadInferenceRouteState | null

  const [formData, setFormData] = useState<FormState>({
    vcpu: inferredState?.autoDetected ? inferredState.vcpu : 4,
    ram_gb: inferredState?.autoDetected ? inferredState.ram_gb : 16,
    storage_gb: inferredState?.autoDetected ? inferredState.storage_gb : 100,
    region: 'us-east',
    hours_per_month: 730,
  })

  const [lastQueriedData, setLastQueriedData] = useState<FormState | null>(null)

  const [autoDetectedBadge, setAutoDetectedBadge] = useState(
    inferredState?.autoDetected ?? false
  )

  // Sync form if router state changes (e.g. navigating back and forward)
  useEffect(() => {
    if (inferredState?.autoDetected) {
      setFormData((prev) => ({
        ...prev,
        vcpu: inferredState.vcpu,
        ram_gb: inferredState.ram_gb,
        storage_gb: inferredState.storage_gb,
      }))
      setAutoDetectedBadge(true)
    }
  }, [inferredState?.autoDetected]) // eslint-disable-line react-hooks/exhaustive-deps

  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isQuerying, setIsQuerying] = useState<boolean>(false)
  const [pendingData, setPendingData] = useState<CloudComparisonResponse | null>(null)
  const [data, setData] = useState<CloudComparisonResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'number' ? Math.max(0, parseFloat(value) || 0) : value,
    }))
  }

  const stepField = (name: 'vcpu' | 'ram_gb' | 'storage_gb' | 'hours_per_month', delta: number, min: number, max: number) => {
    setFormData((prev) => {
      const currentVal = prev[name]
      const newVal = Math.min(max, Math.max(min, currentVal + delta))
      return { ...prev, [name]: newVal }
    })
  }

  const applyPreset = (vcpu: number, ram_gb: number, storage_gb: number) => {
    setFormData((prev) => ({
      ...prev,
      vcpu,
      ram_gb,
      storage_gb,
    }))
  }

  const activePreset = useMemo<'micro' | 'standard' | 'high-mem' | null>(() => {
    if (formData.vcpu === 2 && formData.ram_gb === 4 && formData.storage_gb === 50) return 'micro'
    if (formData.vcpu === 4 && formData.ram_gb === 16 && formData.storage_gb === 100) return 'standard'
    if (formData.vcpu === 8 && formData.ram_gb === 32 && formData.storage_gb === 250) return 'high-mem'
    return null
  }, [formData.vcpu, formData.ram_gb, formData.storage_gb])

  const hasAnyChangesSinceRun = useMemo(() => {
    if (!lastQueriedData) return false
    return (
      lastQueriedData.vcpu !== formData.vcpu ||
      lastQueriedData.ram_gb !== formData.ram_gb ||
      lastQueriedData.storage_gb !== formData.storage_gb ||
      lastQueriedData.region !== formData.region ||
      lastQueriedData.hours_per_month !== formData.hours_per_month
    )
  }, [lastQueriedData, formData])

  // Real-time validation & contextual helpers
  const vcpuValidation = useMemo(() => {
    if (formData.vcpu < 1) return { type: 'error' as const, text: 'vCPU must be at least 1 core.' }
    if (formData.vcpu > 128) return { type: 'advisory' as const, text: 'Large compute (> 128 vCPUs) requires specialized bare-metal instances.' }
    return { type: 'helper' as const, text: 'Standard cloud instance range (1 to 128 vCPUs).' }
  }, [formData.vcpu])

  const ramValidation = useMemo(() => {
    if (formData.ram_gb < 1) return { type: 'error' as const, text: 'RAM must be at least 1 GB.' }
    const ratio = formData.vcpu > 0 ? formData.ram_gb / formData.vcpu : 0
    if (ratio < 1) return { type: 'advisory' as const, text: 'Low memory-to-core ratio (< 1 GB/core). Cloud instances typically offer 2–8 GB/core.' }
    if (ratio > 16) return { type: 'advisory' as const, text: 'High memory-to-core ratio (> 16 GB/core). Matches memory-optimized instance families.' }
    return { type: 'helper' as const, text: `Memory allocation (~${ratio.toFixed(1)} GB/core).` }
  }, [formData.ram_gb, formData.vcpu])

  const storageValidation = useMemo(() => {
    if (formData.storage_gb < 0) return { type: 'error' as const, text: 'Storage volume cannot be negative.' }
    if (formData.storage_gb === 0) return { type: 'advisory' as const, text: 'Compute only (0 GB attached block storage).' }
    if (formData.storage_gb > 16384) return { type: 'advisory' as const, text: 'Large volume (> 16 TB) may require multi-volume striping.' }
    return { type: 'helper' as const, text: 'Persistent block SSD (gp3 / managed disk / pd-balanced).' }
  }, [formData.storage_gb])

  const hoursValidation = useMemo(() => {
    if (formData.hours_per_month < 1) return { type: 'error' as const, text: 'Hours must be at least 1 hr/month.' }
    if (formData.hours_per_month > 744) return { type: 'error' as const, text: 'Maximum 744 hours in any calendar month (31d × 24h).' }
    if (formData.hours_per_month === 730) return { type: 'helper' as const, text: 'Continuous 24/7 run-rate (standard 730 hrs/month).' }
    const pct = Math.round((formData.hours_per_month / 730) * 100)
    return { type: 'helper' as const, text: `Scheduled runtime (~${pct}% monthly utilization).` }
  }, [formData.hours_per_month])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setIsQuerying(true)
    setPendingData(null)
    setError(null)
    setLastQueriedData({ ...formData })

    try {
      const response = await apiClient.post<CloudComparisonResponse>(
        '/cost-comparison',
        formData
      )
      setPendingData(response.data)
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Failed to communicate with cost comparison service. Please check network connectivity.'
      setError(msg)
      setIsQuerying(false)
      setIsLoading(false)
    }
  }

  const handleQueryComplete = useCallback(() => {
    if (pendingData) {
      setData(pendingData)
      setPendingData(null)
    }
    setIsQuerying(false)
    setIsLoading(false)
  }, [pendingData])

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: 'easeOut' }}
      className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center px-4 py-8 md:py-12"
    >
      {/* ── Top Navigation Bar ─────────────────────────────────────────── */}
      <PublicNav />

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="w-full max-w-5xl text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-[var(--color-accent-primary)]/15 text-violet-200 ring-1 ring-[var(--color-accent-primary)]/30 mb-4">
          <span>Infralytix Multi-Cloud Engine</span>
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-primary)] animate-pulse" />
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">
          Multi-Cloud <span className="gradient-text">Cost Comparison</span>
        </h1>
        <p className="text-neutral-400 text-sm md:text-base max-w-2xl mx-auto">
          Query live on-demand pricing across AWS EC2, Azure VMs, and Google Cloud Compute Engine
          simultaneously. Get instant workload cost parity and AI-backed architectural trade-offs.
        </p>
      </header>

      {/* ── Workload Configuration Form ──────────────────────────────────── */}
      <section className="w-full max-w-5xl mb-12">
        <div className="glass-card p-6 md:p-8 relative overflow-hidden shadow-2xl">
          {/* Subtle decorative glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-[var(--color-accent-primary)]/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">Workload Specifications</h2>
              <p className="text-xs text-neutral-400">
                Define the computational profile, block storage volume, and target deployment region.
              </p>
            </div>

            <div className="flex flex-col items-end gap-2">
              {/* Auto-detected badge */}
              {autoDetectedBadge && inferredState?.justification && (
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[var(--color-success)]/10 border border-[var(--color-success)]/20 text-[var(--color-success)] text-xs font-medium">
                  <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <span
                    title={inferredState.justification}
                    className="cursor-help"
                  >
                    Auto-detected from your project
                  </span>
                  <button
                    type="button"
                    onClick={() => setAutoDetectedBadge(false)}
                    className="text-[var(--color-success)]/70 hover:text-[var(--color-success)] ml-1 transition-colors"
                    aria-label="Dismiss auto-detected badge"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Quick Presets */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-neutral-500 font-medium">Presets:</span>
                <button
                  type="button"
                  onClick={() => applyPreset(2, 4, 50)}
                  className={`px-2.5 py-1 rounded-lg text-xs transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)] ${
                    activePreset === 'micro'
                      ? 'bg-[var(--color-accent-primary)]/25 text-white border border-[var(--color-accent-primary)]/50 shadow-sm shadow-[var(--color-accent-primary)]/20 font-semibold'
                      : 'bg-white/5 hover:bg-white/10 text-neutral-300 border border-transparent'
                  }`}
                  aria-pressed={activePreset === 'micro'}
                >
                  Micro (2v/4G)
                </button>
                <button
                  type="button"
                  onClick={() => applyPreset(4, 16, 100)}
                  className={`px-2.5 py-1 rounded-lg text-xs transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)] ${
                    activePreset === 'standard'
                      ? 'bg-[var(--color-accent-primary)]/25 text-white border border-[var(--color-accent-primary)]/50 shadow-sm shadow-[var(--color-accent-primary)]/20 font-semibold'
                      : 'bg-white/5 hover:bg-white/10 text-neutral-300 border border-transparent'
                  }`}
                  aria-pressed={activePreset === 'standard'}
                >
                  Standard (4v/16G)
                </button>
                <button
                  type="button"
                  onClick={() => applyPreset(8, 32, 250)}
                  className={`px-2.5 py-1 rounded-lg text-xs transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)] ${
                    activePreset === 'high-mem'
                      ? 'bg-[var(--color-accent-primary)]/25 text-white border border-[var(--color-accent-primary)]/50 shadow-sm shadow-[var(--color-accent-primary)]/20 font-semibold'
                      : 'bg-white/5 hover:bg-white/10 text-neutral-300 border border-transparent'
                  }`}
                  aria-pressed={activePreset === 'high-mem'}
                >
                  High-Mem (8v/32G)
                </button>
              </div>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* vCPU */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center">
                    <label htmlFor="vcpu" className="text-xs font-semibold text-neutral-300">
                      vCPU Cores
                    </label>
                    <FieldTooltip
                      label="vCPU Cores"
                      content="Virtual CPU cores allocated to execute your workload. Cloud providers size standard instances from 1 to 128 vCPUs."
                    />
                  </div>
                  {lastQueriedData && lastQueriedData.vcpu !== formData.vcpu && (
                    <span className="text-[10px] font-medium text-amber-300 bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.5 rounded-md">
                      Was {lastQueriedData.vcpu}
                    </span>
                  )}
                </div>
                <div className="relative flex items-center">
                  <input
                    id="vcpu"
                    name="vcpu"
                    type="number"
                    min="1"
                    max="256"
                    required
                    value={formData.vcpu}
                    onChange={handleInputChange}
                    className="input-field pr-16 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)]"
                    placeholder="e.g. 4"
                    aria-describedby="vcpu-helper"
                  />
                  <div className="absolute right-1.5 flex items-center gap-0.5 bg-neutral-800/80 rounded-lg p-0.5 border border-white/10">
                    <button
                      type="button"
                      onClick={() => stepField('vcpu', -1, 1, 256)}
                      disabled={formData.vcpu <= 1}
                      aria-label="Decrease vCPU"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      –
                    </button>
                    <button
                      type="button"
                      onClick={() => stepField('vcpu', 1, 1, 256)}
                      disabled={formData.vcpu >= 256}
                      aria-label="Increase vCPU"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      +
                    </button>
                  </div>
                </div>
                <p
                  id="vcpu-helper"
                  className={`text-[11px] mt-1.5 leading-snug transition-colors duration-150 ${
                    vcpuValidation.type === 'error'
                      ? 'text-red-400 font-medium'
                      : vcpuValidation.type === 'advisory'
                      ? 'text-amber-400 font-medium'
                      : 'text-neutral-400'
                  }`}
                >
                  {vcpuValidation.text}
                </p>
              </div>

              {/* RAM */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center">
                    <label htmlFor="ram_gb" className="text-xs font-semibold text-neutral-300">
                      RAM (GB)
                    </label>
                    <FieldTooltip
                      label="RAM"
                      content="System memory allocated. General-purpose cloud workloads typically require 2 to 4 GB per vCPU; in-memory caches and databases need more."
                    />
                  </div>
                  {lastQueriedData && lastQueriedData.ram_gb !== formData.ram_gb && (
                    <span className="text-[10px] font-medium text-amber-300 bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.5 rounded-md">
                      Was {lastQueriedData.ram_gb}G
                    </span>
                  )}
                </div>
                <div className="relative flex items-center">
                  <input
                    id="ram_gb"
                    name="ram_gb"
                    type="number"
                    min="1"
                    max="3904"
                    required
                    value={formData.ram_gb}
                    onChange={handleInputChange}
                    className="input-field pr-16 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)]"
                    placeholder="e.g. 16"
                    aria-describedby="ram-helper"
                  />
                  <div className="absolute right-1.5 flex items-center gap-0.5 bg-neutral-800/80 rounded-lg p-0.5 border border-white/10">
                    <button
                      type="button"
                      onClick={() => stepField('ram_gb', formData.ram_gb <= 8 ? -2 : -4, 1, 3904)}
                      disabled={formData.ram_gb <= 1}
                      aria-label="Decrease RAM"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      –
                    </button>
                    <button
                      type="button"
                      onClick={() => stepField('ram_gb', formData.ram_gb < 8 ? 2 : 4, 1, 3904)}
                      disabled={formData.ram_gb >= 3904}
                      aria-label="Increase RAM"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      +
                    </button>
                  </div>
                </div>
                <p
                  id="ram-helper"
                  className={`text-[11px] mt-1.5 leading-snug transition-colors duration-150 ${
                    ramValidation.type === 'error'
                      ? 'text-red-400 font-medium'
                      : ramValidation.type === 'advisory'
                      ? 'text-amber-400 font-medium'
                      : 'text-neutral-400'
                  }`}
                >
                  {ramValidation.text}
                </p>
              </div>

              {/* Storage */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center">
                    <label htmlFor="storage_gb" className="text-xs font-semibold text-neutral-300">
                      Storage (GB)
                    </label>
                    <FieldTooltip
                      label="Storage"
                      content="Persistent block storage volume attached to the instance (AWS EBS gp3, Azure Managed Disks, or GCP pd-balanced). Set to 0 for compute-only pricing."
                    />
                  </div>
                  {lastQueriedData && lastQueriedData.storage_gb !== formData.storage_gb && (
                    <span className="text-[10px] font-medium text-amber-300 bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.5 rounded-md">
                      Was {lastQueriedData.storage_gb}G
                    </span>
                  )}
                </div>
                <div className="relative flex items-center">
                  <input
                    id="storage_gb"
                    name="storage_gb"
                    type="number"
                    min="0"
                    max="65536"
                    value={formData.storage_gb}
                    onChange={handleInputChange}
                    className="input-field pr-16 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)]"
                    placeholder="e.g. 100"
                    aria-describedby="storage-helper"
                  />
                  <div className="absolute right-1.5 flex items-center gap-0.5 bg-neutral-800/80 rounded-lg p-0.5 border border-white/10">
                    <button
                      type="button"
                      onClick={() => stepField('storage_gb', -25, 0, 65536)}
                      disabled={formData.storage_gb <= 0}
                      aria-label="Decrease Storage"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      –
                    </button>
                    <button
                      type="button"
                      onClick={() => stepField('storage_gb', 25, 0, 65536)}
                      disabled={formData.storage_gb >= 65536}
                      aria-label="Increase Storage"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      +
                    </button>
                  </div>
                </div>
                <p
                  id="storage-helper"
                  className={`text-[11px] mt-1.5 leading-snug transition-colors duration-150 ${
                    storageValidation.type === 'error'
                      ? 'text-red-400 font-medium'
                      : storageValidation.type === 'advisory'
                      ? 'text-amber-400 font-medium'
                      : 'text-neutral-400'
                  }`}
                >
                  {storageValidation.text}
                </p>
              </div>

              {/* Region */}
              <div className="sm:col-span-2 lg:col-span-1">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center">
                    <label htmlFor="region" className="text-xs font-semibold text-neutral-300">
                      Target Region
                    </label>
                    <FieldTooltip
                      label="Target Region"
                      content="Cloud data center geography. Infrastructure availability, network latency, and regional power/tax rates cause on-demand pricing to vary by 10% to 25%."
                    />
                  </div>
                  {lastQueriedData && lastQueriedData.region !== formData.region && (
                    <span className="text-[10px] font-medium text-amber-300 bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.5 rounded-md">
                      Changed
                    </span>
                  )}
                </div>
                <select
                  id="region"
                  name="region"
                  value={formData.region}
                  onChange={handleInputChange}
                  className="input-field bg-neutral-900 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)]"
                  aria-describedby="region-helper"
                >
                  {REGION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value} className="bg-neutral-900 text-white">
                      {opt.label}
                    </option>
                  ))}
                </select>
                <p id="region-helper" className="text-[11px] mt-1.5 leading-snug text-neutral-400">
                  Regional catalogs vary up to 25% across locations.
                </p>
              </div>

              {/* Hours / Month */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center">
                    <label htmlFor="hours_per_month" className="text-xs font-semibold text-neutral-300">
                      Hours / Month
                    </label>
                    <FieldTooltip
                      label="Hours / Month"
                      content="Estimated operational hours per month. 730 hours is the cloud standard for full-time 24/7 continuous workloads (365 days × 24 hrs ÷ 12 months = 730)."
                    />
                  </div>
                  {lastQueriedData && lastQueriedData.hours_per_month !== formData.hours_per_month && (
                    <span className="text-[10px] font-medium text-amber-300 bg-amber-500/15 border border-amber-500/30 px-1.5 py-0.5 rounded-md">
                      Was {lastQueriedData.hours_per_month}h
                    </span>
                  )}
                </div>
                <div className="relative flex items-center">
                  <input
                    id="hours_per_month"
                    name="hours_per_month"
                    type="number"
                    min="1"
                    max="744"
                    required
                    value={formData.hours_per_month}
                    onChange={handleInputChange}
                    className="input-field pr-16 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)]"
                    placeholder="730 (24x7)"
                    aria-describedby="hours-helper"
                  />
                  <div className="absolute right-1.5 flex items-center gap-0.5 bg-neutral-800/80 rounded-lg p-0.5 border border-white/10">
                    <button
                      type="button"
                      onClick={() => stepField('hours_per_month', -24, 1, 744)}
                      disabled={formData.hours_per_month <= 1}
                      aria-label="Decrease Hours"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      –
                    </button>
                    <button
                      type="button"
                      onClick={() => stepField('hours_per_month', 24, 1, 744)}
                      disabled={formData.hours_per_month >= 744}
                      aria-label="Increase Hours"
                      className="w-5 h-6 rounded flex items-center justify-center text-neutral-300 hover:text-white hover:bg-white/10 disabled:opacity-30 disabled:hover:bg-transparent transition-colors text-xs font-bold focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--color-accent-primary)]"
                    >
                      +
                    </button>
                  </div>
                </div>
                <p
                  id="hours-helper"
                  className={`text-[11px] mt-1.5 leading-snug transition-colors duration-150 ${
                    hoursValidation.type === 'error'
                      ? 'text-red-400 font-medium'
                      : 'text-neutral-400'
                  }`}
                >
                  {hoursValidation.text}
                </p>
              </div>
            </div>

            {/* Submit Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/10">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2.5">
                <span className="text-xs text-neutral-400">
                  Queries live AWS EC2 &amp; Azure Retail APIs + Google Cloud Billing simultaneously.
                </span>
                {hasAnyChangesSinceRun && (
                  <span className="inline-flex items-center gap-1.5 text-xs text-amber-300 bg-amber-500/15 border border-amber-500/30 px-2.5 py-0.5 rounded-lg shadow-sm">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    Specifications modified since previous comparison run
                  </span>
                )}
              </div>
              <button
                type="submit"
                disabled={isLoading}
                style={{
                  background: 'linear-gradient(135deg, var(--color-accent-primary) 0%, var(--color-bg-elevated) 100%)',
                }}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-8 py-3 rounded-xl text-white text-sm font-semibold transition-all duration-200 ease-out hover:opacity-95 hover:brightness-110 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed shadow-[0_4px_20px_-2px_color-mix(in_srgb,var(--color-accent-primary)_35%,transparent)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                    Querying Cloud APIs...
                  </span>
                ) : (
                  'Compare Cloud Costs →'
                )}
              </button>
            </div>
          </form>
        </div>
      </section>

      {/* ── Error Banner ─────────────────────────────────────────────────── */}
      {error && (
        <div className="w-full max-w-5xl mb-8 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between">
          <span>{error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-xs underline hover:text-white"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Multi-Cloud Querying Hero Sequence ───────────────────────────── */}
      <AnimatePresence>
        {isQuerying && (
          <CloudQueryingHero
            data={pendingData}
            onComplete={handleQueryComplete}
            onSkip={handleQueryComplete}
          />
        )}
      </AnimatePresence>

      {/* ── Results Cards ──────────────────────────────────────────────────── */}
      <AnimatePresence>
        {!isQuerying && data && (
          <motion.section
            key="results"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="w-full max-w-5xl mb-12"
          >
            {/* Header row */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-white">Comparative Price Results</h2>
                <p className="text-xs text-neutral-400">
                  Sorted cheapest-first. Storage line items: EBS gp3 (AWS), Premium SSD (Azure), pd-balanced (GCP).
                </p>
              </div>
              <span className="badge-neutral text-xs">
                {data.estimates.filter((e) => !e.error).length} / {data.estimates.length} Providers Online
              </span>
            </div>

            {/* Provider cards — 3D tilt-and-settle staggered entrance */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8" style={{ perspective: 1200 }}>
              {data.estimates.map((est, idx) => {
                const key = est.provider.toLowerCase()
                const meta = PROVIDER_META[key] ?? {
                  name: est.provider.toUpperCase(),
                  tag: est.provider.toUpperCase(),
                  Icon: AwsIcon,
                  iconColor: '#9ca3af',
                  borderGradient: 'border-[color-mix(in_srgb,var(--color-bg-elevated)_65%,rgba(255,255,255,0.12))]',
                  hoverShadow: '0 8px 24px -4px color-mix(in srgb, var(--color-accent-primary) 20%, transparent)',
                }

                const isCheapest = idx === 0 && !est.error && est.monthly_cost_low > 0
                const isStaticGCP =
                  key === 'gcp' &&
                  (est.notes?.toLowerCase().includes('static') ||
                    est.notes?.toLowerCase().includes('reference'))

                return (
                  <motion.div
                    key={est.provider}
                    initial={{
                      opacity: 0,
                      y: 44,
                      rotateX: 14,
                      rotateY: idx === 0 ? -6 : idx === 2 ? 6 : 0,
                      scale: 0.93,
                    }}
                    animate={{
                      opacity: 1,
                      y: 0,
                      rotateX: 0,
                      rotateY: 0,
                      scale: 1,
                    }}
                    transition={{
                      duration: 0.55,
                      delay: idx * 0.11,
                      ease: [0.22, 1, 0.36, 1],
                    }}
                    whileHover={{
                      y: -4,
                      transition: { duration: 0.2, ease: [0.22, 1, 0.36, 1] },
                    }}
                    className={[
                      'relative flex flex-col justify-between rounded-2xl p-6 overflow-hidden',
                      'backdrop-blur-sm border',
                      isCheapest
                        ? 'border-[var(--color-success)]/50 shadow-[0_0_32px_-4px_rgba(97,210,154,0.30)]'
                        : `${meta.borderGradient} elev-1 hover:shadow-[var(--provider-shadow)]`,
                    ].join(' ')}
                    style={{
                      '--provider-shadow': meta.hoverShadow,
                      background: 'color-mix(in srgb, var(--color-bg-elevated) 28%, rgba(15,15,35,0.75))',
                      transformStyle: 'preserve-3d',
                    } as React.CSSProperties}
                    onMouseEnter={(e) => {
                      if (!isCheapest)
                        (e.currentTarget as HTMLElement).style.boxShadow = meta.hoverShadow
                    }}
                    onMouseLeave={(e) => {
                      if (!isCheapest)
                        (e.currentTarget as HTMLElement).style.boxShadow = ''
                    }}
                  >
                    {/* Cheapest animated shimmer border */}
                    {isCheapest && <div className="cheapest-shimmer" aria-hidden />}

                    {/* ── Top row: icon + tag + badges ── */}
                    <div className="flex items-start justify-between gap-2 mb-5 relative z-10">
                      {/* Icon + name block */}
                      <div className="flex items-center gap-2.5">
                        <div
                          className="flex items-center justify-center w-10 h-10 rounded-xl shrink-0"
                          style={{ background: `${meta.iconColor}1A` }}
                        >
                          <meta.Icon size={22} />
                        </div>
                        <div>
                          <div className="text-[10px] uppercase font-semibold tracking-widest text-neutral-500 leading-none mb-0.5">
                            {meta.tag}
                          </div>
                          <div className="text-[13px] font-semibold text-neutral-200 leading-snug">
                            {meta.name}
                          </div>
                        </div>
                      </div>

                      {/* Status badges */}
                      <div className="flex flex-col items-end gap-1 shrink-0 pt-0.5">
                        {isCheapest && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[var(--color-success)]/15 text-[var(--color-success)] ring-1 ring-[var(--color-success)]/40 whitespace-nowrap">
                            <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-success)] animate-pulse shrink-0" />
                            Lowest Cost
                          </span>
                        )}
                        {isStaticGCP && (
                          <span className="badge-warning text-[10px]" title="Static fallback dataset active">
                            Reference Pricing
                          </span>
                        )}
                        {est.error && <span className="badge-danger text-[10px]">Unavailable</span>}
                      </div>
                    </div>

                    {/* ── Instance type ── */}
                    <div className="mb-4 relative z-10">
                      <div className="text-[10px] uppercase tracking-widest text-neutral-600 font-semibold mb-1">
                        Matched instance
                      </div>
                      <div className="text-base md:text-lg font-mono font-bold text-white tracking-tight truncate">
                        {est.error ? <span className="text-red-400/70">—</span> : est.instance_type_matched}
                      </div>
                    </div>

                    {/* ── Price section ── */}
                    <div className="py-3 my-2 border-y border-white/[0.07] relative z-10">
                      {est.error ? (
                        <div className="text-xs text-red-400 font-mono py-1">{est.error}</div>
                      ) : (
                        <>
                          <div className="flex items-baseline gap-1">
                            <span
                              className={`text-3xl md:text-4xl font-extrabold tracking-tight ${
                                isCheapest ? 'text-[var(--color-success)]' : 'text-white'
                              }`}
                            >
                              $<AnimatedPrice value={est.monthly_cost_low} delayMs={idx * 110 + 150} />
                            </span>
                            <span className="text-xs text-neutral-500">/ mo</span>
                          </div>
                          <div className="text-[11px] text-neutral-600 mt-1">
                            {est.monthly_cost_low === est.monthly_cost_high
                              ? `On-demand estimate (${est.currency})`
                              : `Range: $${est.monthly_cost_low.toFixed(2)} – $${est.monthly_cost_high.toFixed(2)} ${est.currency}`}
                          </div>
                        </>
                      )}
                    </div>

                    {/* ── Line-item notes ── */}
                    {est.notes && !est.error && (
                      <div className="mt-3 text-xs text-neutral-400 bg-white/[0.03] p-2.5 rounded-lg border border-white/[0.05] space-y-1 relative z-10">
                        <div className="text-[10px] uppercase font-semibold tracking-wider text-neutral-600">
                          Line Item Notes
                        </div>
                        <p className="line-clamp-3 leading-relaxed text-neutral-300">{est.notes}</p>
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </div>

            {/* ── AI Architectural Verdict ── */}
            {data.ai_suggestion && (
              <AIVerdictCard
                estimates={data.estimates}
                aiSuggestion={data.ai_suggestion}
                region={formData.region}
                vcpu={formData.vcpu}
                ramGb={formData.ram_gb}
              />
            )}
          </motion.section>
        )}
      </AnimatePresence>


      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="w-full max-w-5xl text-center text-xs text-neutral-600 border-t border-white/5 pt-6 mt-auto">
        Infralytix Cloud Intelligence Platform — Real-time price catalog ingestion.
      </footer>
    </motion.div>
  )
}

export default CostComparisonPage
