/**
 * AISuggestion — Renders the Gemini AI recommendation panel.
 * Styled with a gradient accent to feel distinct from the data panels.
 */

import React from 'react'
import type { CloudProvider } from '../types'
import { ProviderBadge } from './ProviderBadge'

interface Props {
  suggestion: string
  cheapestProvider: CloudProvider
}

export const AISuggestion: React.FC<Props> = ({ suggestion, cheapestProvider }) => {
  return (
    <div
      id="ai-suggestion-panel"
      className="relative overflow-hidden rounded-2xl border border-brand-500/20
                 bg-gradient-to-br from-brand-950/40 via-brand-900/20 to-transparent p-6"
    >
      {/* Background glow */}
      <div className="absolute -top-10 -right-10 w-40 h-40 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center gap-3 mb-4 relative z-10">
        <div className="w-8 h-8 rounded-lg bg-brand-500/15 border border-brand-500/25
                        flex items-center justify-center shrink-0">
          <svg
            className="w-4 h-4 text-brand-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
            />
          </svg>
        </div>
        <div>
          <div className="text-xs text-brand-400 font-semibold uppercase tracking-widest">
            AI Recommendation
          </div>
          <div className="text-[10px] text-neutral-500">Powered by Gemini</div>
        </div>
        <div className="ml-auto">
          <ProviderBadge provider={cheapestProvider} size="sm" />
        </div>
      </div>

      {/* Suggestion text */}
      <p className="text-sm text-neutral-200 leading-relaxed relative z-10">
        {suggestion}
      </p>

      {/* Disclaimer */}
      <p className="text-[10px] text-neutral-600 mt-4 relative z-10">
        ⓘ Estimates are based on public on-demand pricing and do not include
        reserved-instance discounts, data-transfer costs, or managed-service fees.
      </p>
    </div>
  )
}
