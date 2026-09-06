/**
 * WorkloadForm — Left-panel form for specifying the workload to estimate.
 * Uses existing .input-field, .btn-primary, .glass-card design-system classes.
 */

import React, { useState } from 'react'
import type { CloudProvider, CostEstimateRequest, RegionPreference } from '../types'

interface Props {
  onSubmit: (req: CostEstimateRequest) => void
  isLoading: boolean
}

const ALL_PROVIDERS: { key: CloudProvider; label: string }[] = [
  { key: 'aws', label: 'Amazon Web Services' },
  { key: 'gcp', label: 'Google Cloud Platform' },
  { key: 'azure', label: 'Microsoft Azure' },
]

const REGIONS: { key: RegionPreference; label: string }[] = [
  { key: 'us', label: 'United States (us-east / us-central)' },
  { key: 'eu', label: 'Europe (eu-west / europe-west)' },
  { key: 'asia', label: 'Asia Pacific (ap-southeast / asia-east)' },
]

const INITIAL: CostEstimateRequest = {
  cpu_cores: 4,
  memory_gb: 16,
  storage_gb: 100,
  hours_per_month: 730,
  providers: ['aws', 'gcp', 'azure'],
  region_preference: 'us',
  workload_label: '',
}

export const WorkloadForm: React.FC<Props> = ({ onSubmit, isLoading }) => {
  const [form, setForm] = useState<CostEstimateRequest>(INITIAL)
  const [errors, setErrors] = useState<Partial<Record<keyof CostEstimateRequest, string>>>({})

  const setField = <K extends keyof CostEstimateRequest>(
    key: K,
    value: CostEstimateRequest[K]
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setErrors((prev) => ({ ...prev, [key]: undefined }))
  }

  const toggleProvider = (p: CloudProvider) => {
    setForm((prev) => {
      const has = prev.providers.includes(p)
      const next = has
        ? prev.providers.filter((x) => x !== p)
        : [...prev.providers, p]
      return { ...prev, providers: next }
    })
  }

  const validate = (): boolean => {
    const e: typeof errors = {}
    if (form.cpu_cores < 1) e.cpu_cores = 'Minimum 1 vCPU'
    if (form.memory_gb < 1) e.memory_gb = 'Minimum 1 GB'
    if (form.storage_gb < 0) e.storage_gb = 'Cannot be negative'
    if (form.hours_per_month < 1 || form.hours_per_month > 744)
      e.hours_per_month = '1–744 hours'
    if (form.providers.length === 0)
      e.providers = 'Select at least one provider' as never
    setErrors(e)
    return Object.keys(e).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (validate()) onSubmit(form)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" id="cost-estimator-form">
      {/* Label */}
      <div>
        <label htmlFor="workload-label" className="block text-xs text-neutral-400 mb-1.5 font-medium">
          Workload Label <span className="text-neutral-600">(optional)</span>
        </label>
        <input
          id="workload-label"
          type="text"
          className="input-field"
          placeholder="e.g. Web API — production"
          value={form.workload_label}
          maxLength={120}
          onChange={(e) => setField('workload_label', e.target.value)}
        />
      </div>

      {/* CPU + Memory */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="cpu-cores" className="block text-xs text-neutral-400 mb-1.5 font-medium">
            vCPU Cores
          </label>
          <input
            id="cpu-cores"
            type="number"
            min={1}
            max={256}
            className={`input-field ${errors.cpu_cores ? 'border-red-500' : ''}`}
            value={form.cpu_cores}
            onChange={(e) => setField('cpu_cores', Number(e.target.value))}
          />
          {errors.cpu_cores && (
            <p className="text-red-400 text-xs mt-1">{errors.cpu_cores}</p>
          )}
        </div>

        <div>
          <label htmlFor="memory-gb" className="block text-xs text-neutral-400 mb-1.5 font-medium">
            Memory (GB)
          </label>
          <input
            id="memory-gb"
            type="number"
            min={1}
            max={3904}
            className={`input-field ${errors.memory_gb ? 'border-red-500' : ''}`}
            value={form.memory_gb}
            onChange={(e) => setField('memory_gb', Number(e.target.value))}
          />
          {errors.memory_gb && (
            <p className="text-red-400 text-xs mt-1">{errors.memory_gb}</p>
          )}
        </div>
      </div>

      {/* Storage + Hours */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="storage-gb" className="block text-xs text-neutral-400 mb-1.5 font-medium">
            Storage (GB)
          </label>
          <input
            id="storage-gb"
            type="number"
            min={0}
            max={65536}
            className={`input-field ${errors.storage_gb ? 'border-red-500' : ''}`}
            value={form.storage_gb}
            onChange={(e) => setField('storage_gb', Number(e.target.value))}
          />
        </div>

        <div>
          <label htmlFor="hours-month" className="block text-xs text-neutral-400 mb-1.5 font-medium">
            Hours / Month
            <span className="text-neutral-600 ml-1">(730 = 24×7)</span>
          </label>
          <input
            id="hours-month"
            type="number"
            min={1}
            max={744}
            step={0.5}
            className={`input-field ${errors.hours_per_month ? 'border-red-500' : ''}`}
            value={form.hours_per_month}
            onChange={(e) => setField('hours_per_month', Number(e.target.value))}
          />
          {errors.hours_per_month && (
            <p className="text-red-400 text-xs mt-1">{errors.hours_per_month}</p>
          )}
        </div>
      </div>

      {/* Region */}
      <div>
        <label htmlFor="region" className="block text-xs text-neutral-400 mb-1.5 font-medium">
          Region Preference
        </label>
        <select
          id="region"
          className="input-field appearance-none"
          value={form.region_preference}
          onChange={(e) => setField('region_preference', e.target.value as RegionPreference)}
        >
          {REGIONS.map((r) => (
            <option key={r.key} value={r.key}>
              {r.label}
            </option>
          ))}
        </select>
      </div>

      {/* Providers */}
      <div>
        <p className="text-xs text-neutral-400 mb-2 font-medium">Compare Providers</p>
        {(errors.providers as string | undefined) && (
          <p className="text-red-400 text-xs mb-2">{errors.providers as string}</p>
        )}
        <div className="space-y-2">
          {ALL_PROVIDERS.map(({ key, label }) => (
            <label
              key={key}
              htmlFor={`provider-${key}`}
              className="flex items-center gap-3 p-3 rounded-xl bg-white/5 border border-white/10 cursor-pointer
                         hover:border-brand-500/40 transition-colors duration-150"
            >
              <input
                id={`provider-${key}`}
                type="checkbox"
                className="accent-brand-500 w-4 h-4"
                checked={form.providers.includes(key)}
                onChange={() => toggleProvider(key)}
              />
              <span className="text-sm text-neutral-200">{label}</span>
            </label>
          ))}
        </div>
      </div>

      <button
        id="run-estimate-btn"
        type="submit"
        className="btn-primary w-full shadow-brand"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            Computing…
          </>
        ) : (
          '⚡ Run Cost Estimate'
        )}
      </button>
    </form>
  )
}
