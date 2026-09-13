/**
 * Infralytix — Multi-Cloud Querying Hero Sequence.
 *
 * A cinematic, full-viewport parallel querying moment featuring:
 * 1. Ambient background treatment with animated gradient mesh and particle drift.
 * 2. 3 provider pods (AWS, Azure, GCP) with equal visual weight and racing progress bars.
 * 3. Sequential lock-in revealing real matched instance types and spring checkmark badges.
 * 4. Cinematic handoff transition (450ms scale-down & blur crossfade) to results.
 */

import React, { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { AwsIcon, AzureIcon, GcpIcon } from './BrandIcons'
import type { CloudComparisonResponse } from '../CostComparisonPage'

interface CloudQueryingHeroProps {
  data: CloudComparisonResponse | null
  onComplete: () => void
  onSkip?: () => void
}

type ProviderStatus = 'querying' | 'locked'

interface ProviderPodState {
  key: 'aws' | 'azure' | 'gcp'
  name: string
  tag: string
  Icon: React.FC<{ size?: number }>
  brandColor: string
  endpointLabel: string
  status: ProviderStatus
  progress: number
  matchedInstance?: string
  costLow?: number
}

export const CloudQueryingHero: React.FC<CloudQueryingHeroProps> = ({
  data,
  onComplete,
  onSkip,
}) => {
  const shouldReduce = useReducedMotion()
  const [awsLocked, setAwsLocked] = useState(shouldReduce ? true : false)
  const [azureLocked, setAzureLocked] = useState(shouldReduce ? true : false)
  const [gcpLocked, setGcpLocked] = useState(shouldReduce ? true : false)
  const [isHandoff, setIsHandoff] = useState(false)
  const [canSkip, setCanSkip] = useState(false)

  // Map incoming real data by provider
  const estimatesByProvider = useMemo(() => {
    if (!data?.estimates) return {}
    const map: Record<string, { instance: string; costLow: number; error: string | null }> = {}
    data.estimates.forEach((est) => {
      map[est.provider.toLowerCase()] = {
        instance: est.instance_type_matched,
        costLow: est.monthly_cost_low,
        error: est.error,
      }
    })
    return map
  }, [data])

  // Sequential progression / lock-in choreography
  useEffect(() => {
    if (shouldReduce) {
      setAwsLocked(true)
      setAzureLocked(true)
      setGcpLocked(true)
      setCanSkip(true)
      return
    }

    // Enable skip button after brief moment
    const skipTimer = setTimeout(() => setCanSkip(true), 600)

    // Provider 1 (AWS) locks in at 650ms if data is ready or minimum time
    const tAws = setTimeout(() => {
      setAwsLocked(true)
    }, 650)

    // Provider 2 (Azure) locks in at 1050ms
    const tAzure = setTimeout(() => {
      setAzureLocked(true)
    }, 1050)

    // Provider 3 (GCP) locks in at 1450ms
    const tGcp = setTimeout(() => {
      setGcpLocked(true)
    }, 1450)

    return () => {
      clearTimeout(skipTimer)
      clearTimeout(tAws)
      clearTimeout(tAzure)
      clearTimeout(tGcp)
    }
  }, [shouldReduce])

  // When all 3 are locked AND data has arrived from backend, trigger completion handoff
  useEffect(() => {
    if (awsLocked && azureLocked && gcpLocked && data) {
      if (shouldReduce) {
        onComplete()
        return
      }

      const handoffTimer = setTimeout(() => {
        setIsHandoff(true)
        const completeTimer = setTimeout(() => {
          onComplete()
        }, 420)
        return () => clearTimeout(completeTimer)
      }, 420)

      return () => clearTimeout(handoffTimer)
    }
  }, [awsLocked, azureLocked, gcpLocked, data, onComplete, shouldReduce])

  const handleSkip = () => {
    setIsHandoff(true)
    setTimeout(() => {
      if (onSkip) onSkip()
      else onComplete()
    }, 200)
  }

  const providers: ProviderPodState[] = [
    {
      key: 'aws',
      name: 'Amazon Web Services',
      tag: 'AWS EC2 & EBS',
      Icon: AwsIcon,
      brandColor: '#FF9900',
      endpointLabel: 'AWS Price List API (us-east-1)',
      status: awsLocked && data ? 'locked' : 'querying',
      progress: awsLocked ? 100 : 75,
      matchedInstance: estimatesByProvider['aws']?.instance,
      costLow: estimatesByProvider['aws']?.costLow,
    },
    {
      key: 'azure',
      name: 'Microsoft Azure',
      tag: 'Azure VMs & Disk',
      Icon: AzureIcon,
      brandColor: '#0078D4',
      endpointLabel: 'Azure Retail Prices API',
      status: azureLocked && data ? 'locked' : 'querying',
      progress: azureLocked ? 100 : 60,
      matchedInstance: estimatesByProvider['azure']?.instance,
      costLow: estimatesByProvider['azure']?.costLow,
    },
    {
      key: 'gcp',
      name: 'Google Cloud Platform',
      tag: 'GCP Compute Engine',
      Icon: GcpIcon,
      brandColor: '#4285F4',
      endpointLabel: 'GCP Cloud Billing Catalog',
      status: gcpLocked && data ? 'locked' : 'querying',
      progress: gcpLocked ? 100 : 45,
      matchedInstance: estimatesByProvider['gcp']?.instance,
      costLow: estimatesByProvider['gcp']?.costLow,
    },
  ]

  const allLocked = awsLocked && azureLocked && gcpLocked && !!data

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.96 }}
      animate={
        isHandoff
          ? { opacity: 0, scale: 0.97, filter: 'blur(10px)', y: -16 }
          : { opacity: 1, scale: 1, filter: 'blur(0px)', y: 0 }
      }
      transition={{ duration: 0.42, ease: 'easeInOut' }}
      className="w-full max-w-5xl my-8 relative z-20 select-none"
    >
      {/* ── Ambient Gradient Mesh Background ─────────────────────────────── */}
      <div className="absolute -inset-4 bg-gradient-to-r from-amber-500/10 via-cyan-500/10 to-blue-600/10 rounded-3xl blur-2xl pointer-events-none -z-10" />
      <div className="absolute top-1/2 left-1/4 -translate-y-1/2 w-72 h-72 bg-amber-500/8 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute top-1/2 right-1/4 -translate-y-1/2 w-72 h-72 bg-cyan-500/8 rounded-full blur-3xl pointer-events-none -z-10" />

      <div className="glass-card border border-brand-500/30 bg-neutral-950/90 p-6 md:p-10 rounded-3xl shadow-2xl relative overflow-hidden">
        {/* Subtle particle grid background */}
        <div className="particle-grid absolute inset-0 pointer-events-none -z-10" />

        {/* ── Header Row ─────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8 relative z-10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-brand-500/15 text-brand-300 ring-1 ring-brand-500/30 mb-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
              <span>Multi-Cloud Intelligence Engine</span>
              <span className="text-neutral-500">·</span>
              <span className="text-neutral-400 font-mono text-[11px]">Concurrent Execution</span>
            </div>
            <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Querying Cloud APIs in Parallel
            </h2>
            <p className="text-xs md:text-sm text-neutral-400 mt-1 max-w-xl leading-relaxed">
              Evaluating real-time on-demand compute rates and regional block storage catalogs
              across AWS, Azure, and Google Cloud simultaneously.
            </p>
          </div>

          {/* Quick Skip Button */}
          {canSkip && (
            <button
              type="button"
              onClick={handleSkip}
              className="inline-flex items-center gap-1.5 text-xs text-neutral-400 hover:text-white px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 transition-colors shrink-0"
            >
              <span>View Results</span>
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </button>
          )}
        </div>

        {/* ── 3-Provider Querying Grid ────────────────────────────────────── */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-8 relative z-10">
          {providers.map((provider, idx) => {
            const isLocked = provider.status === 'locked'

            return (
              <div
                key={provider.key}
                className={`
                  relative rounded-2xl p-5 border transition-all duration-300 overflow-hidden flex flex-col justify-between
                  ${
                    isLocked
                      ? 'bg-neutral-900/90 border-emerald-500/40 shadow-[0_0_24px_-4px_rgba(16,185,129,0.25)]'
                      : 'bg-neutral-900/60 border-white/10'
                  }
                `}
              >
                {/* Brand-tinted radial background glow */}
                <div
                  className="absolute -top-10 -right-10 w-32 h-32 rounded-full blur-2xl pointer-events-none opacity-25"
                  style={{ background: provider.brandColor }}
                />

                {/* Top: Icon + Status */}
                <div>
                  <div className="flex items-start justify-between gap-3 mb-4">
                    {/* Brand Icon with glowing ring */}
                    <div className="relative">
                      <motion.div
                        animate={
                          isLocked
                            ? { scale: [1, 1.12, 1] }
                            : { scale: [1, 1.06, 1], opacity: [0.7, 1, 0.7] }
                        }
                        transition={{ duration: 1.8, repeat: isLocked ? 0 : Infinity, ease: 'easeInOut' }}
                        className="w-12 h-12 rounded-xl flex items-center justify-center border shadow-lg"
                        style={{
                          background: `${provider.brandColor}18`,
                          borderColor: isLocked ? 'rgba(16, 185, 129, 0.5)' : `${provider.brandColor}50`,
                          boxShadow: isLocked
                            ? '0 0 16px rgba(16, 185, 129, 0.3)'
                            : `0 0 16px ${provider.brandColor}33`,
                        }}
                      >
                        <provider.Icon size={26} />
                      </motion.div>
                    </div>

                    {/* Status badge: Querying vs Locked In */}
                    <div className="pt-1">
                      <AnimatePresence mode="wait">
                        {isLocked ? (
                          <motion.div
                            key="locked"
                            initial={{ scale: 0, opacity: 0 }}
                            animate={{ scale: [0, 1.25, 1], opacity: 1 }}
                            transition={{ type: 'spring', stiffness: 450, damping: 18 }}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                          >
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                            </svg>
                            <span>Locked In</span>
                          </motion.div>
                        ) : (
                          <motion.div
                            key="querying"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-mono text-neutral-300 bg-white/5 border border-white/10"
                          >
                            <span
                              className="w-2 h-2 rounded-full animate-pulse"
                              style={{ background: provider.brandColor }}
                            />
                            <span>Querying…</span>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  {/* Provider Info */}
                  <div className="mb-3">
                    <div className="text-[11px] font-mono uppercase tracking-wider text-neutral-400">
                      {provider.tag}
                    </div>
                    <div className="text-base font-bold text-white leading-snug">
                      {provider.name}
                    </div>
                    <div className="text-[11px] text-neutral-500 truncate mt-0.5">
                      {provider.endpointLabel}
                    </div>
                  </div>
                </div>

                {/* Bottom: Progress Bar & Real Matched Instance */}
                <div className="mt-4 pt-3 border-t border-white/5">
                  {/* Real Matched Instance pill (revealed on lock-in) */}
                  <div className="min-h-[28px] mb-2.5 flex items-center">
                    <AnimatePresence mode="wait">
                      {isLocked && provider.matchedInstance ? (
                        <motion.div
                          key="instance"
                          initial={{ opacity: 0, y: 4 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3 }}
                          className="flex items-center justify-between w-full"
                        >
                          <span className="text-xs font-mono font-bold text-emerald-300 truncate max-w-[140px]">
                            {provider.matchedInstance}
                          </span>
                          {provider.costLow !== undefined && provider.costLow > 0 && (
                            <span className="text-xs font-mono text-neutral-300">
                              ${provider.costLow.toFixed(2)}/mo
                            </span>
                          )}
                        </motion.div>
                      ) : (
                        <motion.span
                          key="scanning"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 0.6 }}
                          className="text-[11px] font-mono text-neutral-500"
                        >
                          Matching instance SKU specs…
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Racing Animated Progress Bar */}
                  <div className="relative w-full h-1.5 rounded-full bg-white/10 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full"
                      style={{
                        background: isLocked
                          ? '#10b981'
                          : `linear-gradient(90deg, ${provider.brandColor}66, ${provider.brandColor})`,
                      }}
                      initial={{ width: '10%' }}
                      animate={{
                        width: isLocked ? '100%' : `${provider.progress}%`,
                      }}
                      transition={{
                        duration: isLocked ? 0.3 : 0.8 + idx * 0.25,
                        ease: 'easeInOut',
                      }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* ── Status Banner & Parity Notification ─────────────────────────── */}
        <div className="pt-4 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-neutral-400 relative z-10">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                allLocked ? 'bg-emerald-400' : 'bg-cyan-400 animate-ping'
              }`}
            />
            <span className="font-medium text-neutral-300">
              {allLocked
                ? 'All 3 Cloud Catalogues Evaluated · Calculating Architectural Parity'
                : 'Streaming parallel live responses from AWS, Azure & GCP…'}
            </span>
          </div>

          <div className="text-[11px] text-neutral-500 font-mono">
            {allLocked ? 'Revealing Comparison Matrix →' : 'Real-time telemetry'}
          </div>
        </div>
      </div>
    </motion.div>
  )
}
