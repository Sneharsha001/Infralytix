/**
 * Infralytix — ProjectsListPage Component.
 *
 * Displays all repository workspaces owned by the user, providing quick
 * intelligence metrics (LOC, language breakdown, frameworks) and modal for new creations.
 */

import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { projectsApi } from '../api'
import { Project } from '../types'
import { NewProjectModal } from './NewProjectModal'

export const ProjectsListPage: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchProjects = async () => {
    try {
      setIsLoading(true)
      const data = await projectsApi.list()
      setProjects(data)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch projects.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchProjects()
  }, [])

  const handleCreated = (newProject: Project) => {
    setProjects((prev) => [newProject, ...prev])
  }

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete project "${name}"?`)) {
      return
    }

    try {
      await projectsApi.delete(id)
      setProjects((prev) => prev.filter((p) => p.id !== id))
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete project')
    }
  }

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.repo_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-fade-in">
      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-brand-400 font-semibold mb-1">
            Repository Intelligence Hub
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight">
            Project Workspaces
          </h2>
          <p className="text-sm text-neutral-400 mt-1">
            Manage repositories, inspect architecture frameworks, and trigger static code analysis.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="btn-primary text-sm shadow-brand shrink-0"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          + New Project
        </button>
      </div>

      {/* ── Search & Filter Controls ─────────────────────────────────────── */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <input
            type="text"
            placeholder="Search projects by name, repo, or description..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field pl-10 text-xs"
          />
          <svg
            className="w-4 h-4 text-neutral-400 absolute left-3.5 top-3.5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* ── Loading Skeleton ─────────────────────────────────────────────── */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-card p-6 h-64 skeleton" />
          ))}
        </div>
      )}

      {/* ── Empty State ──────────────────────────────────────────────────── */}
      {!isLoading && projects.length === 0 && (
        <div className="glass-card p-12 text-center border-dashed border-white/15">
          <div className="w-16 h-16 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold mb-1">No Projects Found</h3>
          <p className="text-xs text-neutral-400 max-w-sm mx-auto mb-6">
            Get started by creating your first project workspace and uploading a repository archive for static analysis.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="btn-primary text-xs shadow-brand"
          >
            + Create Your First Project
          </button>
        </div>
      )}

      {/* ── Projects Grid ────────────────────────────────────────────────── */}
      {!isLoading && projects.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => {
            const analysis = project.latest_run?.output_data
            const hasRun = !!project.latest_run
            const isCompleted = project.latest_run?.status === 'completed'

            return (
              <div
                key={project.id}
                className="glass-card-hover p-6 flex flex-col justify-between group relative overflow-hidden"
              >
                {/* Glow accent */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/5 rounded-full blur-2xl group-hover:bg-brand-500/10 transition-colors pointer-events-none" />

                <div>
                  {/* Top Bar: Status & Repo badge */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="badge-neutral text-[10px] font-mono truncate max-w-[150px]">
                      {project.repo_name || 'custom-repo'}
                    </span>
                    {isCompleted ? (
                      <span className="badge-success text-[10px]">Ready</span>
                    ) : hasRun ? (
                      <span className="badge-info text-[10px] capitalize">
                        {project.latest_run?.status}
                      </span>
                    ) : (
                      <span className="badge-neutral text-[10px]">No Code Yet</span>
                    )}
                  </div>

                  {/* Title & Description */}
                  <h3 className="text-lg font-bold text-white group-hover:text-brand-300 transition-colors line-clamp-1 mb-1">
                    {project.name}
                  </h3>
                  <p className="text-xs text-neutral-400 line-clamp-2 mb-5">
                    {project.description || 'No description provided.'}
                  </p>

                  {/* Static Intelligence Quick Metrics */}
                  <div className="grid grid-cols-2 gap-3 py-3 border-y border-white/5 mb-5 bg-white/[0.01] rounded-xl px-3">
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                        Primary Lang
                      </div>
                      <div className="text-xs font-semibold text-white mt-0.5">
                        {analysis?.primary_language || '—'}
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wider text-neutral-500">
                        Total LOC
                      </div>
                      <div className="text-xs font-semibold text-white mt-0.5">
                        {analysis?.total_loc ? analysis.total_loc.toLocaleString() : '—'}
                      </div>
                    </div>
                  </div>

                  {/* Frameworks Badges */}
                  {analysis?.detected_frameworks && analysis.detected_frameworks.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mb-5">
                      {analysis.detected_frameworks.slice(0, 3).map((fw) => (
                        <span key={fw} className="badge-info text-[10px]">
                          {fw}
                        </span>
                      ))}
                      {analysis.detected_frameworks.length > 3 && (
                        <span className="badge-neutral text-[10px]">
                          +{analysis.detected_frameworks.length - 3} more
                        </span>
                      )}
                    </div>
                  )}
                </div>

                {/* Card Action Buttons */}
                <div className="flex items-center justify-between pt-2 border-t border-white/5">
                  <Link
                    to={`/projects/${project.id}`}
                    className="btn-primary text-xs py-1.5 px-3 shadow-sm"
                  >
                    Inspect Intelligence →
                  </Link>

                  <button
                    onClick={() => handleDelete(project.id, project.name)}
                    className="text-neutral-500 hover:text-red-400 transition-colors p-1"
                    title="Delete Project"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Modal */}
      <NewProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onCreated={handleCreated}
      />
    </div>
  )
}
