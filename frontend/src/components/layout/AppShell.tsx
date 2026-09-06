/**
 * Infralytix — AppShell Layout.
 *
 * Provides the persistent sidebar, top header, and content canvas for protected pages.
 * Fully styled using the .glass-card and button system classes.
 */

import React from 'react'
import { Link, NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '@/features/auth'

export const AppShell: React.FC = () => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="min-h-screen flex bg-neutral-900 text-white selection:bg-brand-500 selection:text-white">
      {/* ── Sidebar ───────────────────────────────────────────────────────── */}
      <aside className="w-64 border-r border-white/10 bg-neutral-950/80 backdrop-blur-md flex flex-col justify-between shrink-0 sticky top-0 h-screen">
        <div>
          {/* Logo / Brand */}
          <div className="p-6 border-b border-white/10 flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-brand-600 flex items-center justify-center font-bold text-white shadow-lg shadow-brand-500/20">
              IX
            </div>
            <div>
              <Link to="/dashboard" className="text-lg font-bold gradient-text tracking-tight">
                Infralytix
              </Link>
              <div className="text-[10px] uppercase tracking-wider text-neutral-400 font-medium">
                Infrastructure OS
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-1">
            <NavLink
              to="/dashboard"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-brand'
                    : 'text-neutral-400 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
              </svg>
              Dashboard
            </NavLink>

            <NavLink
              to="/projects"
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-brand-600 text-white shadow-brand'
                    : 'text-neutral-400 hover:text-white hover:bg-white/5'
                }`
              }
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              Projects
            </NavLink>

            <div className="pt-4 pb-2 px-3 text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
              Simulation Modules
            </div>

            <span className="flex items-center justify-between px-3 py-2 rounded-xl text-sm text-neutral-400 cursor-not-allowed">
              <span className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Workflows (DAG)
              </span>
              <span className="text-[10px] badge-neutral">Sprint 2</span>
            </span>

            <span className="flex items-center justify-between px-3 py-2 rounded-xl text-sm text-neutral-400 cursor-not-allowed">
              <span className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
                VM Pools
              </span>
              <span className="text-[10px] badge-neutral">Sprint 2</span>
            </span>

            <span className="flex items-center justify-between px-3 py-2 rounded-xl text-sm text-neutral-400 cursor-not-allowed">
              <span className="flex items-center gap-3">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Scheduler Engine
              </span>
              <span className="text-[10px] badge-neutral">Sprint 3</span>
            </span>
          </nav>
        </div>

        {/* User Card at bottom */}
        <div className="p-4 border-t border-white/10 bg-white/[0.02]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-full bg-brand-500/20 border border-brand-500/40 flex items-center justify-center font-bold text-xs text-brand-300">
                {user?.name.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="truncate">
                <div className="text-sm font-medium truncate">{user?.name}</div>
                <div className="text-xs text-neutral-400 truncate">{user?.email}</div>
              </div>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="btn-secondary w-full py-2 text-xs text-neutral-300 hover:text-white"
          >
            Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main Layout (Topbar + Content) ─────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Topbar Header */}
        <header className="h-16 border-b border-white/10 bg-neutral-900/60 backdrop-blur-md px-8 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold tracking-tight">Workspace Overview</h1>
            <span className="badge-info text-[11px] capitalize">{user?.role}</span>
          </div>

          <div className="flex items-center gap-4">
            <span className="badge-success text-[11px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              API Connected
            </span>
          </div>
        </header>

        {/* Page Body Canvas */}
        <main className="flex-1 p-8 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
