/**
 * Infralytix — PublicNav Component.
 *
 * Shared sticky navigation bar for all public-facing pages (CostComparison,
 * WorkflowOptimizer, WorkloadUpload). Uses NavLink for automatic active-route
 * detection and the design-system .nav-link / .nav-link-active classes.
 */

import React from 'react'
import { Link, NavLink } from 'react-router-dom'

interface PublicNavProps {
  /** Subtitle shown beneath the Infralytix logo */
  subtitle?: string
}

export const PublicNav: React.FC<PublicNavProps> = ({
  subtitle = 'Multi-Cloud Intelligence Platform',
}) => {
  return (
    <header
      className="w-full max-w-6xl mx-auto mb-8 flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/10
                 sticky top-0 z-40 bg-neutral-950/80 backdrop-blur-md pt-6 px-0"
      style={{ boxShadow: '0 1px 0 rgba(255,255,255,0.06)' }}
    >
      {/* ── Brand ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div
          className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center font-bold text-white
                     transition-all duration-200 ease-out hover:shadow-brand-lg hover:scale-105"
          style={{ boxShadow: '0 0 16px rgba(59,130,246,0.20)' }}
        >
          IX
        </div>
        <div>
          <Link
            to="/"
            className="text-xl font-bold gradient-text tracking-tight hover:opacity-90 transition-opacity duration-200"
          >
            Infralytix
          </Link>
          <div className="text-[11px] uppercase tracking-wider text-neutral-400 font-medium">
            {subtitle}
          </div>
        </div>
      </div>

      {/* ── Navigation Links ─────────────────────────────────────────────── */}
      <nav className="flex items-center gap-1.5" aria-label="Main navigation">
        <NavLink
          to="/upload-workload"
          className={({ isActive }) =>
            ['nav-link flex items-center gap-1.5', isActive ? 'nav-link-active' : ''].join(' ')
          }
        >
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          Upload &amp; Detect
        </NavLink>

        <NavLink
          to="/cost-comparison"
          end
          className={({ isActive }) =>
            ['nav-link flex items-center gap-1.5', isActive ? 'nav-link-active' : ''].join(' ')
          }
        >
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Cost Comparison
        </NavLink>

        <NavLink
          to="/workflows"
          className={({ isActive }) =>
            ['nav-link flex items-center gap-1.5', isActive ? 'nav-link-active' : ''].join(' ')
          }
        >
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Workflow Optimizer
        </NavLink>

        <NavLink
          to="/dashboard"
          className={({ isActive }) =>
            ['nav-link flex items-center gap-1.5', isActive ? 'nav-link-active' : ''].join(' ')
          }
        >
          <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Dashboard
        </NavLink>
      </nav>
    </header>
  )
}
