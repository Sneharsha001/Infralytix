/**
 * CostEstimatorPage — Main page for the multi-cloud cost comparison tool.
 *
 * Layout:
 *   - Left column (md:1/3): WorkloadForm
 *   - Right column (md:2/3): ComparisonTable + AISuggestion
 *
 * Empty state: prompt card before first estimate.
 * Error state: inline error message.
 */

import React, { useState } from 'react'
import { costApi } from '../api'
import type { CostEstimateRequest, CostEstimateResponse, CostEstimatorState } from '../types'
import { AISuggestion } from './AISuggestion'
import { ComparisonTable } from './ComparisonTable'
import { WorkloadForm } from './WorkloadForm'

const INITIAL_STATE: CostEstimatorState = {
  isLoading: false,
  error: null,
  result: null,
}

export const CostEstimatorPage: React.FC = () => {
  const [state, setState] = useState<CostEstimatorState>(INITIAL_STATE)

  const handleEstimate = async (req: CostEstimateRequest) => {
    setState({ isLoading: true, error: null, result: null })
    try {
      const result: CostEstimateResponse = await costApi.estimate(req)
      setState({ isLoading: false, error: null, result })
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Failed to compute estimate. Please try again.'
      setState({ isLoading: false, error: msg, result: null })
    }
  }

  const { isLoading, error, result } = state

  return (
    <div className="max-w-7xl mx-auto space-y-8 animate-fade-in">
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div>
        <div className="text-xs uppercase tracking-widest text-brand-400 font-semibold mb-1">
          Infrastructure Cost Intelligence
        </div>
        <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
          Multi-Cloud{' '}
          <span className="gradient-text">Cost Estimator</span>
        </h2>
        <p className="text-sm text-neutral-400 mt-1 max-w-2xl">
          Compare AWS, GCP, and Azure compute costs for your workload.
          Get an AI-powered recommendation to choose the best provider.
        </p>
      </div>

      {/* ── Main Layout ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-start">
        {/* Left: Form */}
        <div className="glass-card p-6">
          <h3 className="text-base font-semibold mb-5 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-400" />
            Workload Specification
          </h3>
          <WorkloadForm onSubmit={handleEstimate} isLoading={isLoading} />
        </div>

        {/* Right: Results */}
        <div className="md:col-span-2 space-y-5">
          {/* Loading skeleton */}
          {isLoading && (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="glass-card p-5 space-y-3">
                  <div className="skeleton h-5 w-32 rounded" />
                  <div className="skeleton h-3 w-full rounded" />
                  <div className="skeleton h-3 w-4/5 rounded" />
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="glass-card p-6 border-red-500/20 bg-red-500/5">
              <div className="flex items-start gap-3">
                <span className="text-red-400 text-xl">⚠</span>
                <div>
                  <p className="text-sm font-semibold text-red-400 mb-1">Estimation Failed</p>
                  <p className="text-xs text-neutral-400">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Result */}
          {result && !isLoading && (
            <>
              {/* Workload label */}
              {result.workload_label && (
                <div className="flex items-center gap-2">
                  <span className="badge-neutral text-xs">{result.workload_label}</span>
                  <span className="text-xs text-neutral-500">
                    {new Date(result.created_at).toLocaleString()}
                  </span>
                </div>
              )}

              {/* Comparison cards */}
              <ComparisonTable
                providers={result.result.providers}
                cheapestProvider={result.result.cheapest_provider}
              />

              {/* AI suggestion */}
              <AISuggestion
                suggestion={result.result.ai_suggestion}
                cheapestProvider={result.result.cheapest_provider}
              />
            </>
          )}

          {/* Empty state */}
          {!result && !isLoading && !error && (
            <div
              className="glass-card p-12 text-center relative overflow-hidden
                         border-dashed border-white/10"
            >
              <div className="absolute -top-16 -right-16 w-48 h-48 bg-brand-500/8 rounded-full blur-3xl pointer-events-none" />
              <div className="absolute -bottom-16 -left-16 w-48 h-48 bg-emerald-500/8 rounded-full blur-3xl pointer-events-none" />

              <div className="relative z-10 max-w-sm mx-auto">
                <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10
                                flex items-center justify-center mx-auto mb-5">
                  <svg
                    className="w-7 h-7 text-brand-400"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <h4 className="text-lg font-semibold mb-2">Ready to Compare</h4>
                <p className="text-sm text-neutral-400 leading-relaxed">
                  Configure your workload requirements on the left and click{' '}
                  <strong className="text-neutral-200">Run Cost Estimate</strong> to
                  compare AWS, GCP, and Azure pricing with an AI recommendation.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
