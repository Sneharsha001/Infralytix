/**
 * Infralytix — Multi-Cloud Cost Comparison Page.
 *
 * Provides a live interactive form to configure compute and storage workloads,
 * queries POST /api/v1/cost-comparison concurrently across AWS, Azure, and GCP,
 * and renders comparative cards sorted cheapest-first alongside Gemini AI recommendations.
 */

import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiClient } from '@/lib/api-client'

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

const PROVIDER_META: Record<
  string,
  { name: string; tag: string; borderClass: string; badgeClass: string }
> = {
  aws: {
    name: 'Amazon Web Services',
    tag: 'AWS EC2',
    borderClass: 'border-amber-500/30 hover:border-amber-500/60',
    badgeClass: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
  },
  azure: {
    name: 'Microsoft Azure',
    tag: 'Azure VMs',
    borderClass: 'border-sky-500/30 hover:border-sky-500/60',
    badgeClass: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
  },
  gcp: {
    name: 'Google Cloud Platform',
    tag: 'GCP Compute',
    borderClass: 'border-blue-500/30 hover:border-blue-500/60',
    badgeClass: 'bg-blue-500/15 text-blue-300 ring-blue-500/30',
  },
}

export const CostComparisonPage: React.FC = () => {
  const [formData, setFormData] = useState<FormState>({
    vcpu: 4,
    ram_gb: 16,
    storage_gb: 100,
    region: 'us-east',
    hours_per_month: 730,
  })

  const [isLoading, setIsLoading] = useState<boolean>(false)
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

  const applyPreset = (vcpu: number, ram_gb: number, storage_gb: number) => {
    setFormData((prev) => ({
      ...prev,
      vcpu,
      ram_gb,
      storage_gb,
    }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.post<CloudComparisonResponse>(
        '/cost-comparison',
        formData
      )
      setData(response.data)
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Failed to communicate with cost comparison service. Please check network connectivity.'
      setError(msg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center px-4 py-8 md:py-12">
      {/* ── Top Navigation Bar ─────────────────────────────────────────── */}
      <div className="w-full max-w-5xl mb-8 flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center font-bold text-white shadow-lg shadow-brand-500/30">
            IX
          </div>
          <div>
            <Link to="/" className="text-xl font-bold gradient-text tracking-tight hover:opacity-90">
              Infralytix
            </Link>
            <div className="text-[11px] uppercase tracking-wider text-neutral-400 font-medium">
              Multi-Cloud Intelligence Platform
            </div>
          </div>
        </div>

        <nav className="flex items-center gap-2 text-sm">
          <Link
            to="/cost-comparison"
            className="px-3.5 py-1.5 rounded-lg bg-white/10 text-white font-medium border border-white/10 shadow-sm"
          >
            Cost Comparison
          </Link>
          <Link
            to="/workflows"
            className="px-3.5 py-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Workflow Optimizer
          </Link>
          <Link
            to="/dashboard"
            className="px-3.5 py-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Dashboard
          </Link>
        </nav>
      </div>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header className="w-full max-w-5xl text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-brand-500/15 text-brand-300 ring-1 ring-brand-500/30 mb-4">
          <span>Infralytix Multi-Cloud Engine</span>
          <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
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
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">Workload Specifications</h2>
              <p className="text-xs text-neutral-400">
                Define the computational profile, block storage volume, and target deployment region.
              </p>
            </div>

            {/* Quick Presets */}
            <div className="flex items-center gap-2 text-xs">
              <span className="text-neutral-500">Presets:</span>
              <button
                type="button"
                onClick={() => applyPreset(2, 4, 50)}
                className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 transition-colors"
              >
                Micro (2v/4G)
              </button>
              <button
                type="button"
                onClick={() => applyPreset(4, 16, 100)}
                className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 transition-colors"
              >
                Standard (4v/16G)
              </button>
              <button
                type="button"
                onClick={() => applyPreset(8, 32, 250)}
                className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-neutral-300 transition-colors"
              >
                High-Mem (8v/32G)
              </button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {/* vCPU */}
              <div>
                <label htmlFor="vcpu" className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  vCPU Cores
                </label>
                <input
                  id="vcpu"
                  name="vcpu"
                  type="number"
                  min="1"
                  max="256"
                  required
                  value={formData.vcpu}
                  onChange={handleInputChange}
                  className="input-field"
                  placeholder="e.g. 4"
                />
              </div>

              {/* RAM */}
              <div>
                <label htmlFor="ram_gb" className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  RAM (GB)
                </label>
                <input
                  id="ram_gb"
                  name="ram_gb"
                  type="number"
                  min="1"
                  max="3904"
                  required
                  value={formData.ram_gb}
                  onChange={handleInputChange}
                  className="input-field"
                  placeholder="e.g. 16"
                />
              </div>

              {/* Storage */}
              <div>
                <label htmlFor="storage_gb" className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  Storage (GB)
                </label>
                <input
                  id="storage_gb"
                  name="storage_gb"
                  type="number"
                  min="0"
                  max="65536"
                  value={formData.storage_gb}
                  onChange={handleInputChange}
                  className="input-field"
                  placeholder="e.g. 100"
                />
              </div>

              {/* Region */}
              <div className="sm:col-span-2 lg:col-span-1">
                <label htmlFor="region" className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  Target Region
                </label>
                <select
                  id="region"
                  name="region"
                  value={formData.region}
                  onChange={handleInputChange}
                  className="input-field bg-neutral-900 cursor-pointer"
                >
                  {REGION_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value} className="bg-neutral-900 text-white">
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Hours / Month */}
              <div>
                <label htmlFor="hours_per_month" className="block text-xs font-semibold text-neutral-300 mb-1.5">
                  Hours / Month
                </label>
                <input
                  id="hours_per_month"
                  name="hours_per_month"
                  type="number"
                  min="1"
                  max="744"
                  required
                  value={formData.hours_per_month}
                  onChange={handleInputChange}
                  className="input-field"
                  placeholder="730 (24x7)"
                />
              </div>
            </div>

            {/* Submit Bar */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-white/10">
              <span className="text-xs text-neutral-400">
                Queries live AWS EC2 &amp; Azure Retail APIs + Google Cloud Billing simultaneously.
              </span>
              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary w-full sm:w-auto px-8 py-3 text-sm font-semibold shadow-lg shadow-brand-600/20"
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

      {/* ── Loading State ─────────────────────────────────────────────────── */}
      {isLoading && (
        <section className="w-full max-w-5xl mb-12 text-center py-10 animate-fade-in">
          <div className="inline-block p-4 rounded-2xl bg-white/5 border border-white/10 mb-6 shadow-xl">
            <div className="w-10 h-10 border-4 border-brand-500/30 border-t-brand-500 rounded-full animate-spin mx-auto mb-3" />
            <h3 className="text-lg font-bold text-white mb-1">
              Evaluating Multi-Cloud Pricing...
            </h3>
            <p className="text-xs text-neutral-400 max-w-md mx-auto">
              Querying live AWS EC2 Price List API, Microsoft Azure Retail Prices API, and GCP
              Cloud Billing concurrently. This takes a few seconds to parse live regional catalogues.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card p-6 h-64 skeleton" />
            <div className="glass-card p-6 h-64 skeleton" />
            <div className="glass-card p-6 h-64 skeleton" />
          </div>
        </section>
      )}

      {/* ── Results Cards ─────────────────────────────────────────────────── */}
      {!isLoading && data && (
        <section className="w-full max-w-5xl mb-12 animate-fade-in">
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

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            {data.estimates.map((est, idx) => {
              const meta = PROVIDER_META[est.provider.toLowerCase()] || {
                name: est.provider.toUpperCase(),
                tag: est.provider.toUpperCase(),
                borderClass: 'border-white/15',
                badgeClass: 'bg-white/10 text-white',
              }

              const isCheapest = idx === 0 && !est.error && est.monthly_cost_low > 0
              const isStaticGCP =
                est.provider.toLowerCase() === 'gcp' &&
                (est.notes?.toLowerCase().includes('static') ||
                  est.notes?.toLowerCase().includes('reference'))

              return (
                <div
                  key={est.provider}
                  className={`glass-card p-6 flex flex-col justify-between relative transition-all duration-200 ${
                    isCheapest
                      ? 'border-emerald-500/60 ring-2 ring-emerald-500/20 bg-emerald-950/10 shadow-lg shadow-emerald-500/10'
                      : meta.borderClass
                  }`}
                >
                  {/* Top Badges */}
                  <div className="flex items-center justify-between gap-2 mb-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ring-1 ${meta.badgeClass}`}
                    >
                      {meta.tag}
                    </span>

                    <div className="flex items-center gap-1.5">
                      {isCheapest && (
                        <span className="badge-success text-[11px] font-semibold">
                          ★ Lowest Cost
                        </span>
                      )}
                      {isStaticGCP && (
                        <span className="badge-warning text-[10px]" title="Static fallback dataset active">
                          Reference Pricing
                        </span>
                      )}
                      {est.error && (
                        <span className="badge-danger text-[10px]">
                          Unavailable
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Provider & Matched Machine */}
                  <div className="mb-4">
                    <h3 className="text-sm font-semibold text-neutral-400 mb-1">
                      {meta.name}
                    </h3>
                    <div className="text-lg md:text-xl font-mono font-bold text-white tracking-tight">
                      {est.error ? '—' : est.instance_type_matched}
                    </div>
                  </div>

                  {/* Price Section */}
                  <div className="my-3 py-3 border-y border-white/10">
                    {est.error ? (
                      <div className="text-xs text-red-400 font-mono py-2">
                        {est.error}
                      </div>
                    ) : (
                      <>
                        <div className="flex items-baseline gap-1">
                          <span className="text-3xl md:text-4xl font-extrabold text-white">
                            ${est.monthly_cost_low.toFixed(2)}
                          </span>
                          <span className="text-xs text-neutral-400">/ mo</span>
                        </div>
                        <div className="text-[11px] text-neutral-500 mt-1">
                          {est.monthly_cost_low === est.monthly_cost_high
                            ? `On-demand estimate (${est.currency})`
                            : `Range: $${est.monthly_cost_low.toFixed(2)} – $${est.monthly_cost_high.toFixed(2)} ${est.currency}`}
                        </div>
                      </>
                    )}
                  </div>

                  {/* Storage & Region Breakdown */}
                  {est.notes && !est.error && (
                    <div className="text-xs text-neutral-400 bg-white/[0.02] p-2.5 rounded-lg border border-white/5 space-y-1">
                      <div className="text-[10px] uppercase font-semibold tracking-wider text-neutral-500">
                        Line Item Notes
                      </div>
                      <p className="line-clamp-3 leading-relaxed text-neutral-300">
                        {est.notes}
                      </p>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* ── AI Recommendation Highlighted Section ──────────────────────── */}
          {data.ai_suggestion && (
            <div className="glass-card p-6 md:p-8 border-brand-500/30 bg-brand-950/15 relative overflow-hidden shadow-xl">
              <div className="flex items-center gap-2 mb-3">
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-ping" />
                <span className="badge-info text-xs font-semibold">
                  AI Architectural Recommendation
                </span>
              </div>
              <h3 className="text-lg font-bold text-white mb-2">
                Workload Analysis &amp; Deployment Trade-offs
              </h3>
              <p className="text-sm md:text-base text-neutral-200 leading-relaxed">
                {data.ai_suggestion}
              </p>
            </div>
          )}
        </section>
      )}

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <footer className="w-full max-w-5xl text-center text-xs text-neutral-600 border-t border-white/5 pt-6 mt-auto">
        Infralytix Cloud Intelligence Platform — Real-time price catalog ingestion.
      </footer>
    </div>
  )
}

export default CostComparisonPage
