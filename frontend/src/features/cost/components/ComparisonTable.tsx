/**
 * ComparisonTable — Renders per-provider cost cards sorted cheapest-first.
 * Highlights the cheapest provider with a branded "Best Value" badge.
 */

import React from 'react'
import type { ProviderEstimate } from '../types'
import { ProviderBadge } from './ProviderBadge'

interface Props {
  providers: ProviderEstimate[]
  cheapestProvider: string
}

function formatUSD(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

const PROVIDER_ACCENT: Record<string, string> = {
  aws:   'border-amber-500/30 hover:border-amber-500/60',
  gcp:   'border-blue-500/30 hover:border-blue-500/60',
  azure: 'border-sky-500/30 hover:border-sky-500/60',
}

const PROVIDER_GLOW: Record<string, string> = {
  aws:   'shadow-[0_0_20px_rgba(251,191,36,0.08)]',
  gcp:   'shadow-[0_0_20px_rgba(66,133,244,0.08)]',
  azure: 'shadow-[0_0_20px_rgba(14,165,233,0.08)]',
}

export const ComparisonTable: React.FC<Props> = ({ providers, cheapestProvider }) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-white">Cost Breakdown</h3>
        <span className="badge-neutral text-[10px]">Sorted by total cost ↑</span>
      </div>

      {providers.map((est, idx) => {
        const isCheapest = est.provider === cheapestProvider
        const accent = PROVIDER_ACCENT[est.provider] ?? ''
        const glow = isCheapest ? PROVIDER_GLOW[est.provider] ?? '' : ''

        return (
          <div
            key={est.provider}
            id={`provider-card-${est.provider}`}
            className={`glass-card p-5 border transition-all duration-200 ${accent} ${glow}`}
          >
            {/* Header row */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-neutral-500 text-xs font-mono">#{idx + 1}</span>
                <ProviderBadge provider={est.provider} size="md" />
                <span className="text-xs text-neutral-500">{est.region}</span>
              </div>
              <div className="flex items-center gap-2">
                {isCheapest && (
                  <span className="badge-success text-[10px] animate-pulse">
                    ✦ Best Value
                  </span>
                )}
                <span className="text-xl font-bold text-white">
                  {formatUSD(est.total_monthly_usd)}
                  <span className="text-xs text-neutral-400 font-normal">/mo</span>
                </span>
              </div>
            </div>

            {/* Instance info */}
            <div className="bg-white/3 rounded-xl p-3 mb-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-neutral-500">Instance Type</span>
                <span className="font-mono text-xs text-neutral-200 bg-white/5 px-2 py-0.5 rounded">
                  {est.instance.instance_type}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div>
                  <div className="text-base font-bold text-brand-300">{est.instance.vcpus}</div>
                  <div className="text-[10px] text-neutral-500">vCPUs</div>
                </div>
                <div>
                  <div className="text-base font-bold text-emerald-300">{est.instance.memory_gb} GB</div>
                  <div className="text-[10px] text-neutral-500">RAM</div>
                </div>
                <div>
                  <div className="text-base font-bold text-purple-300">
                    ${est.instance.price_per_hour_usd.toFixed(4)}
                  </div>
                  <div className="text-[10px] text-neutral-500">per hour</div>
                </div>
              </div>
            </div>

            {/* Cost breakdown */}
            <div className="space-y-1.5 text-xs mb-3">
              <div className="flex justify-between text-neutral-400">
                <span>Compute ({est.storage.storage_type ? '' : ''}</span>
                <span className="text-neutral-200">{formatUSD(est.compute_monthly_usd)}</span>
              </div>
              <div className="flex justify-between text-neutral-400">
                <span>
                  Storage ({est.storage.storage_type},&nbsp;
                  ${est.storage.price_per_gb_month_usd.toFixed(4)}/GB)
                </span>
                <span className="text-neutral-200">{formatUSD(est.storage.total_cost_usd)}</span>
              </div>
              <div className="h-px bg-white/5 my-1" />
              <div className="flex justify-between font-semibold text-white">
                <span>Monthly Total</span>
                <span>{formatUSD(est.total_monthly_usd)}</span>
              </div>
            </div>

            {/* Notes */}
            {est.notes.length > 0 && (
              <ul className="space-y-1">
                {est.notes.map((note, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-[10px] text-neutral-500">
                    <span className="mt-0.5 shrink-0">ⓘ</span>
                    {note}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )
}
