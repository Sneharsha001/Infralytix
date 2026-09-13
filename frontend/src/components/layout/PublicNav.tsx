/**
 * Infralytix — PublicNav Component.
 *
 * Enhanced sticky navigation header featuring:
 * 1. Animated active-route pill: Framer Motion layoutId shared-element transition (~250ms spring).
 * 2. Multi-step flow breadcrumb: Contextual journey indicator [1. Detect → 2. Compare → 3. Optimize]
 *    with auto-detected active step and mid-flow badges.
 * 3. Living logo mark: Subtle breathing aura, glowing live dot, and micro-hover interaction.
 * 4. Scroll-aware header: Transitions between resting open layout and a compact, blurred floating bar.
 * 5. Keyboard accessibility: High-contrast focus rings and semantic ARIA navigation roles.
 * 6. Reduced-motion discipline: Instant non-animated fallbacks when prefers-reduced-motion is active.
 */

import React, { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { motion, useReducedMotion } from 'framer-motion'

interface PublicNavProps {
  /** Subtitle shown beneath the Infralytix logo */
  subtitle?: string
  /** Optional manual step override (1: Detect, 2: Compare, 3: Optimize) */
  currentStep?: 1 | 2 | 3
}

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  exact?: boolean
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/upload-workload',
    label: 'Upload & Detect',
    icon: (
      <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
      </svg>
    ),
  },
  {
    to: '/cost-comparison',
    label: 'Cost Comparison',
    exact: true,
    icon: (
      <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    to: '/workflows',
    label: 'Workflow Optimizer',
    icon: (
      <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    ),
  },
  {
    to: '/dashboard',
    label: 'Dashboard',
    icon: (
      <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
]

export const PublicNav: React.FC<PublicNavProps> = ({
  subtitle = 'Multi-Cloud Intelligence Platform',
  currentStep: propStep,
}) => {
  const location = useLocation()
  const shouldReduce = useReducedMotion()
  const [isScrolled, setIsScrolled] = useState(false)

  // ── Scroll awareness ─────────────────────────────────────────────────────────
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    handleScroll()
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // ── Flow step auto-detection ─────────────────────────────────────────────────
  const activeStep = useMemo<number | null>(() => {
    if (propStep) return propStep
    const path = location.pathname
    if (path.startsWith('/upload-workload')) return 1
    if (path === '/' || path.startsWith('/cost-comparison')) return 2
    if (path.startsWith('/workflows')) return 3
    return null
  }, [propStep, location.pathname])

  const isFromUpload = useMemo(() => {
    return Boolean(location.state && (location.state as Record<string, unknown>).inferredWorkload)
  }, [location.state])

  // Active route key for comparison
  const currentPath = location.pathname

  return (
    <header
      className={`w-full max-w-6xl mx-auto sticky z-40 transition-all duration-300 ease-out ${
        isScrolled
          ? 'top-3 my-2 py-2 px-4 md:px-5 rounded-2xl bg-neutral-950/90 backdrop-blur-xl border border-white/10 shadow-2xl shadow-black/70'
          : 'top-0 mb-8 pt-3 pb-5 px-1 border-b border-white/10 bg-neutral-950/40 backdrop-blur-md'
      }`}
      role="banner"
    >
      <div className="w-full flex flex-wrap items-center justify-between gap-3 md:gap-4">
        {/* ── Living Brand Moment ────────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          <Link
            to="/"
            className="group flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950 transition-transform duration-200"
            aria-label="Infralytix Homepage"
          >
            {/* Living Icon Mark */}
            <motion.div
              whileHover={shouldReduce ? {} : { scale: 1.06, rotate: 1 }}
              whileTap={shouldReduce ? {} : { scale: 0.96 }}
              transition={{ type: 'spring', stiffness: 400, damping: 22 }}
              className="relative w-9 h-9 rounded-xl flex items-center justify-center font-bold text-white shadow-lg overflow-hidden shrink-0 select-none"
              style={{
                background: 'linear-gradient(135deg, #2563EB 0%, #4F46E5 100%)',
                boxShadow: '0 0 16px rgba(59,130,246,0.30)',
              }}
            >
              {/* Subtle animated breathing aura */}
              {!shouldReduce && (
                <motion.div
                  animate={{
                    opacity: [0.25, 0.65, 0.25],
                    scale: [1, 1.12, 1],
                  }}
                  transition={{
                    duration: 3.5,
                    repeat: Infinity,
                    ease: 'easeInOut',
                  }}
                  className="absolute inset-0 bg-brand-400/40 blur-[8px] pointer-events-none"
                />
              )}

              {/* IX Monogram */}
              <span className="relative z-10 font-extrabold text-sm tracking-tight drop-shadow-sm">
                IX
              </span>

              {/* Living indicator dot */}
              <span
                className="absolute bottom-1 right-1 w-1.5 h-1.5 rounded-full bg-emerald-400 ring-1 ring-neutral-950 shadow-sm"
                title="System Operational"
              />
            </motion.div>

            {/* Brand Typography */}
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold gradient-text tracking-tight group-hover:opacity-90 transition-opacity duration-200">
                  Infralytix
                </span>
                <span className="hidden sm:inline-block badge-neutral text-[9px] font-mono uppercase px-1.5 py-0.5 border border-white/10">
                  AI OS
                </span>
              </div>
              <div className="text-[11px] uppercase tracking-wider text-neutral-400 font-medium truncate max-w-[210px]">
                {subtitle}
              </div>
            </div>
          </Link>
        </div>

        {/* ── Persistent Multi-Step Flow Breadcrumb ───────────────────────── */}
        {activeStep !== null && (
          <div
            className="hidden lg:flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/[0.03] border border-white/10 text-xs shadow-inner"
            aria-label="Workflow pipeline progress"
          >
            <span className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider mr-1">
              Flow:
            </span>

            {/* Step 1: Detect */}
            <Link
              to="/upload-workload"
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-400 ${
                activeStep === 1
                  ? 'bg-brand-500/20 text-brand-300 font-semibold border border-brand-500/40 shadow-[0_0_8px_rgba(59,130,246,0.25)]'
                  : activeStep > 1
                  ? 'text-emerald-400 hover:text-emerald-300'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <span
                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                  activeStep === 1
                    ? 'bg-brand-500 text-white'
                    : activeStep > 1
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-white/10 text-neutral-400'
                }`}
              >
                {activeStep > 1 ? '✓' : '1'}
              </span>
              <span>Detect</span>
            </Link>

            <span className="text-neutral-600 text-[10px] select-none">→</span>

            {/* Step 2: Compare */}
            <Link
              to="/cost-comparison"
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-400 ${
                activeStep === 2
                  ? 'bg-brand-500/20 text-brand-300 font-semibold border border-brand-500/40 shadow-[0_0_8px_rgba(59,130,246,0.25)]'
                  : activeStep > 2
                  ? 'text-emerald-400 hover:text-emerald-300'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <span
                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                  activeStep === 2
                    ? 'bg-brand-500 text-white'
                    : activeStep > 2
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-white/10 text-neutral-400'
                }`}
              >
                {activeStep > 2 ? '✓' : '2'}
              </span>
              <span>Compare</span>
              {activeStep === 2 && isFromUpload && (
                <span className="badge-success text-[9px] py-0 px-1 ml-0.5">Inferred</span>
              )}
            </Link>

            <span className="text-neutral-600 text-[10px] select-none">→</span>

            {/* Step 3: Optimize */}
            <Link
              to="/workflows"
              className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full transition-all duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-brand-400 ${
                activeStep === 3
                  ? 'bg-brand-500/20 text-brand-300 font-semibold border border-brand-500/40 shadow-[0_0_8px_rgba(59,130,246,0.25)]'
                  : 'text-neutral-400 hover:text-neutral-200'
              }`}
            >
              <span
                className={`w-3.5 h-3.5 rounded-full flex items-center justify-center text-[9px] font-bold ${
                  activeStep === 3
                    ? 'bg-brand-500 text-white'
                    : 'bg-white/10 text-neutral-400'
                }`}
              >
                3
              </span>
              <span>Optimize</span>
            </Link>
          </div>
        )}

        {/* ── Navigation Links with Animated Shared Pill ─────────────────── */}
        <nav
          className="flex items-center gap-1 p-1 rounded-2xl bg-white/[0.02] border border-white/5"
          aria-label="Main application navigation"
        >
          {NAV_ITEMS.map((item) => {
            const isCurrent =
              item.to === '/cost-comparison'
                ? currentPath === '/' || currentPath === '/cost-comparison'
                : currentPath.startsWith(item.to)

            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.exact}
                className={`relative px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-colors duration-200
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950
                  ${isCurrent ? 'text-white' : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.03]'}`}
                aria-current={isCurrent ? 'page' : undefined}
              >
                {/* Animated active shared-element pill */}
                {isCurrent && (
                  <motion.span
                    layoutId="activeNavPill"
                    className="absolute inset-0 rounded-xl bg-brand-600/30 border border-brand-500/40 shadow-[0_0_14px_rgba(59,130,246,0.30)]"
                    style={{ zIndex: 0 }}
                    transition={{
                      type: 'spring',
                      stiffness: shouldReduce ? 1000 : 380,
                      damping: shouldReduce ? 100 : 30,
                    }}
                  />
                )}

                <span className="relative z-10 flex items-center gap-1.5">
                  {item.icon}
                  <span>{item.label}</span>
                </span>
              </NavLink>
            )
          })}
        </nav>
      </div>
    </header>
  )
}

