/**
 * Infralytix — DashboardPage Component.
 *
 * Live project metrics and intelligence dashboard integrating with backend APIs.
 */

import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '@/features/auth'
import { projectsApi, Project, NewProjectModal } from '@/features/projects'

export const DashboardPage: React.FC = () => {
  const { user } = useAuth()
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const loadProjects = async () => {
    try {
      setIsLoading(true)
      const data = await projectsApi.list()
      setProjects(data)
    } catch {
      // Non-blocking for dashboard view
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  const totalLoc = projects.reduce((acc, p) => {
    const data = p.latest_run?.output_data
    return acc + (data && 'total_loc' in data ? (data.total_loc || 0) : 0)
  }, 0)

  const totalAnalyzed = projects.filter(
    (p) => p.latest_run?.status === 'completed'
  ).length

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-fade-in">
      {/* ── Welcome Banner ───────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-brand-400 font-semibold mb-1">
            Developer Infrastructure OS
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
            Welcome back, <span className="gradient-text">{user?.name || 'Developer'}</span>
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Repository intelligence, static code analytics, and cloud scheduling control center.
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <Link to="/projects" className="btn-secondary text-sm">
            All Projects
          </Link>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary text-sm shadow-brand"
          >
            + New Project
          </button>
        </div>
      </div>

      {/* ── Stat Metric Cards ────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>REPOSITORY WORKSPACES</span>
            <span className="badge-info text-[10px]">Phase 1</span>
          </div>
          <div className="text-3xl font-bold text-white mb-1">
            {isLoading ? '...' : projects.length}
          </div>
          <div className="text-xs text-neutral-400">Active project workspaces</div>
        </div>

        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>ANALYZED REPOSITORIES</span>
            <span className="badge-success text-[10px]">Static</span>
          </div>
          <div className="text-3xl font-bold text-emerald-400 mb-1">
            {isLoading ? '...' : totalAnalyzed}
          </div>
          <div className="text-xs text-neutral-400">Completed intelligence runs</div>
        </div>

        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>TOTAL CODE VOLUME</span>
            <span className="badge-neutral text-[10px]">LOC</span>
          </div>
          <div className="text-3xl font-bold text-brand-300 mb-1">
            {isLoading ? '...' : totalLoc.toLocaleString()}
          </div>
          <div className="text-xs text-neutral-400">Non-empty lines evaluated</div>
        </div>

        <div className="glass-card-hover p-6">
          <div className="flex items-center justify-between text-neutral-400 text-xs font-medium mb-3">
            <span>ENGINE PIPELINE</span>
            <span className="badge-success text-[10px]">Active</span>
          </div>
          <div className="text-3xl font-bold text-purple-400 mb-1">v0.1.0</div>
          <div className="text-xs text-neutral-400">Deterministic Analyzer v1</div>
        </div>
      </div>

      {/* ── Recent Projects / Empty State ─────────────────────────────────── */}
      {projects.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-white">Recent Workspaces</h3>
            <Link to="/projects" className="text-xs text-brand-400 hover:underline">
              View all ({projects.length}) →
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {projects.slice(0, 3).map((p) => {
              const analysis =
                p.latest_run?.output_data && 'total_loc' in p.latest_run.output_data
                  ? p.latest_run.output_data
                  : undefined
              return (
                <div key={p.id} className="glass-card p-5 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="badge-neutral text-[10px] font-mono">
                        {p.repo_name || 'custom-repo'}
                      </span>
                      {p.latest_run?.status === 'completed' && (
                        <span className="badge-success text-[10px]">Ready</span>
                      )}
                    </div>
                    <h4 className="text-base font-bold text-white mb-1 truncate">{p.name}</h4>
                    <p className="text-xs text-neutral-400 line-clamp-2 mb-4">
                      {p.description || 'No description provided.'}
                    </p>

                    <div className="text-xs text-neutral-300 space-y-1 mb-4">
                      <div className="flex justify-between">
                        <span className="text-neutral-500">Language:</span>
                        <span className="font-semibold">{analysis?.primary_language || 'Pending'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-neutral-500">Lines of Code:</span>
                        <span className="font-mono">
                          {analysis?.total_loc ? analysis.total_loc.toLocaleString() : '—'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <Link
                    to={`/projects/${p.id}`}
                    className="btn-primary text-xs py-1.5 justify-center"
                  >
                    View Intelligence →
                  </Link>
                </div>
              )
            })}
          </div>
        </div>
      ) : (
        /* Empty State Hero */
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

            <h3 className="text-xl font-semibold mb-2">No projects created yet</h3>
            <p className="text-sm text-neutral-400 mb-8 leading-relaxed">
              Initialize a project workspace and upload a repository zip to extract static code
              intelligence, language statistics, and framework detection.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => setIsModalOpen(true)}
                className="btn-primary w-full sm:w-auto shadow-brand"
              >
                + Create Project Workspace
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Architecture Telemetry ───────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="glass-card p-6">
          <h4 className="text-base font-semibold mb-3 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            Backend Engine Status
          </h4>
          <p className="text-xs text-neutral-400 mb-4">
            Connected to FastAPI backend services with JWT authentication and repository intelligence.
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
            Platform Capabilities
          </h4>
          <p className="text-xs text-neutral-400 mb-4">
            Active features:
          </p>
          <ul className="space-y-2.5 text-xs text-neutral-300">
            <li className="flex items-center gap-2">
              <span className="badge-success text-[10px]">Live</span>
              <span>Deterministic Repository Intelligence &amp; LOC Counter</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="badge-success text-[10px]">Live</span>
              <span>Framework Fingerprinting (FastAPI, React, Docker, etc.)</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="badge-success text-[10px]">Live</span>
              <span>AI Agent Multi-Step Workflow Orchestration</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="badge-success text-[10px]">Live</span>
              <Link to="/cost" className="text-brand-400 hover:underline font-semibold">
                Multi-Cloud Cost Estimator →
              </Link>
            </li>
          </ul>
        </div>
      </div>

      {/* Modal */}
      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={(newP) => setProjects((prev) => [newP, ...prev])}
      />
    </div>
  )
}
