/**
 * Infralytix — DashboardPage Component.
 *
 * Implements the empty-state dashboard showing stat cards, quick start guides,
 * and system telemetry using the .glass-card design system tokens.
 */

import React from 'react'
import { useAuth } from '@/features/auth'

export const DashboardPage: React.FC = () => {
  const { user } = useAuth()

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* ── Welcome Banner ───────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-brand-400 font-semibold mb-1">
            Simulation Control Center
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
            Welcome back, <span className="gradient-text">{user?.name || 'Developer'}</span>
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Configure DAG workflows and benchmark scheduling algorithms across simulated cloud tiers.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button className="btn-secondary text-sm">
            Documentation
          </button>
          <button className="btn-primary text-sm shadow-brand">
            + New Simulation
          </button>
        </div>
      </div>

      {/* ── Stat Metric Cards ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>ACTIVE WORKFLOWS</span>
            <span className="badge-neutral text-[10px]">DAG</span>
          </div>
          <div className="text-3xl font-bold text-white mb-1">0</div>
          <div className="text-xs text-neutral-400">Ready for workflow ingestion</div>
        </div>

        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>VM POOLS</span>
            <span className="badge-neutral text-[10px]">Compute</span>
          </div>
          <div className="text-3xl font-bold text-white mb-1">0</div>
          <div className="text-xs text-neutral-400">0 Total MIPS capacity</div>
        </div>

        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>SCHEDULER RUNS</span>
            <span className="badge-info text-[10px]">Algorithm 2</span>
          </div>
          <div className="text-3xl font-bold text-white mb-1">0</div>
          <div className="text-xs text-neutral-400">Cost-aware Max-Min ready</div>
        </div>

        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>RESOURCE EFFICIENCY</span>
            <span className="badge-success text-[10px]">Optimal</span>
          </div>
          <div className="text-3xl font-bold text-emerald-400 mb-1">-- %</div>
          <div className="text-xs text-neutral-400">Pending baseline execution</div>
        </div>
      </div>

      {/* ── Empty State Hero ─────────────────────────────────────────────── */}
      <div className="glass-card p-12 text-center relative overflow-hidden border-dashed border-white/15">
        <div className="absolute -top-24 -left-24 w-72 h-72 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -right-24 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="max-w-md mx-auto relative z-10">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-6 shadow-inner">
            <svg
              className="w-8 h-8 text-brand-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
              />
            </svg>
          </div>

          <h3 className="text-xl font-semibold mb-2">No projects or workflows yet</h3>
          <p className="text-sm text-neutral-400 mb-8 leading-relaxed">
            Infralytix simulates and schedules complex Directed Acyclic Graph (DAG) task workloads
            across heterogeneous virtual machine pools using the Cost-Aware Max-Min algorithm.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button className="btn-primary w-full sm:w-auto">
              Upload Workflow DAG
            </button>
            <button className="btn-secondary w-full sm:w-auto">
              Configure VM Pool
            </button>
          </div>
        </div>
      </div>

      {/* ── Architecture Telemetry ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h4 className="text-base font-semibold mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Backend Engine Status
          </h4>
          <p className="text-xs text-neutral-400 mb-4">
            Directly connected to FastAPI backend services with JWT authentication and session rotation.
          </p>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1.5 border-b border-white/5">
              <span className="text-neutral-400">Authenticated User</span>
              <span className="font-mono text-neutral-200">{user?.email}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-white/5">
              <span className="text-neutral-400">Role Authority</span>
              <span className="font-mono text-brand-300 capitalize">{user?.role}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-neutral-400">Session Security</span>
              <span className="badge-success text-[10px]">HttpOnly Cookie + Memory JWT</span>
            </div>
          </div>
        </div>

        <div className="glass-card p-6">
          <h4 className="text-base font-semibold mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-brand-400" />
            Sprint Roadmap
          </h4>
          <p className="text-xs text-neutral-400 mb-4">
            Next milestone features ready for implementation:
          </p>
          <ul className="space-y-2.5 text-xs text-neutral-300">
            <li className="flex items-center gap-2">
              <span className="badge-neutral text-[10px]">Sprint 2</span>
              <span>Workflow DAG Upload & Topological Cycle Detection</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="badge-neutral text-[10px]">Sprint 2</span>
              <span>VM Pool Provisioning & Cost-per-1000MI Model</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="badge-neutral text-[10px]">Sprint 3</span>
              <span>Advanced Cost-Aware Max-Min Algorithm Execution</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}
