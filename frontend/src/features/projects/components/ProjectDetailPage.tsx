/**
 * Infralytix — ProjectDetailPage Component.
 *
 * Detailed Repository Intelligence analysis view showing:
 *   - Language breakdown bar & stats
 *   - Non-empty LOC & total files
 *   - Detected dependency manifests & libraries
 *   - Framework & infrastructure fingerprinting
 *   - Agent run history timeline
 */

import React, { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { projectsApi } from '../api'
import { AgentRun, Project, RepositoryAnalysisResult } from '../types'
import { AIInsightsPanel } from './AIInsightsPanel'

// Color map for language progress bar
const LANGUAGE_COLORS: Record<string, string> = {
  Python: '#3b82f6', // blue-500
  TypeScript: '#06b6d4', // cyan-500
  JavaScript: '#eab308', // yellow-500
  Go: '#14b8a6', // teal-500
  Rust: '#f97316', // orange-500
  Java: '#ef4444', // red-500
  HTML: '#ec4899', // pink-500
  CSS: '#8b5cf6', // purple-500
  Shell: '#10b981', // emerald-500
  JSON: '#64748b', // slate-500
  YAML: '#a855f7', // purple-500
}

export const ProjectDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [geminiRun, setGeminiRun] = useState<AgentRun | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loadData = async (projectId: string) => {
    try {
      setIsLoading(true)
      const [projData, runsData] = await Promise.all([
        projectsApi.getById(projectId),
        projectsApi.getRuns(projectId),
      ])
      setProject(projData)
      setRuns(runsData)
      // Try to load existing AI analysis (may 404 if not run yet -- that is fine)
      try {
        const aiRun = await projectsApi.getAnalysis(projectId)
        setGeminiRun(aiRun)
      } catch {
        // No AI analysis yet -- that's fine
      }
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Project not found.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (id) {
      loadData(id)
    }
  }, [id])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!id || !e.target.files || !e.target.files[0]) return

    const file = e.target.files[0]
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setUploadError('Only .zip repository archives are accepted.')
      return
    }

    try {
      setIsUploading(true)
      setUploadError(null)
      const newRun = await projectsApi.uploadArchive(id, file)
      setRuns((prev) => [newRun, ...prev])
      // Reload project to refresh archive_filename and latest_run
      const updated = await projectsApi.getById(id)
      setProject(updated)
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : 'Failed to upload archive.')
    } finally {
      setIsUploading(false)
    }
  }

  const handleDelete = async () => {
    if (!project || !window.confirm(`Delete project "${project.name}" permanently?`)) {
      return
    }

    try {
      await projectsApi.delete(project.id)
      navigate('/projects', { replace: true })
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete project')
    }
  }

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto space-y-6 animate-pulse">
        <div className="h-8 bg-white/10 rounded w-1/4" />
        <div className="h-40 glass-card skeleton" />
        <div className="grid grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 glass-card skeleton" />
          ))}
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="max-w-xl mx-auto my-16 text-center glass-card p-10">
        <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 flex items-center justify-center mx-auto mb-4">
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-white mb-2">Project Not Found</h3>
        <p className="text-xs text-neutral-400 mb-6">
          The requested project does not exist or you do not have permission to view it.
        </p>
        <Link to="/projects" className="btn-primary text-xs shadow-brand">
          ← Back to Projects
        </Link>
      </div>
    )
  }

  const latestRepoRun = runs.find((r) => r.agent_type === 'repository') ?? project?.latest_run ?? null
  const analysis = latestRepoRun?.output_data as RepositoryAnalysisResult | null | undefined

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-fade-in">
      {/* ── Breadcrumb & Top Bar ─────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-neutral-400 mb-1">
            <Link to="/projects" className="hover:text-white transition-colors">
              Projects
            </Link>
            <span>/</span>
            <span className="text-brand-300 font-mono">{project.name}</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            {project.name}
            {latestRepoRun?.status === 'completed' && (
              <span className="badge-success text-xs">Analyzed</span>
            )}
          </h2>
          <p className="text-xs text-neutral-400 mt-1 max-w-2xl">
            {project.description || 'No description provided.'}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-3 shrink-0">
          <label className="btn-primary text-xs shadow-brand cursor-pointer">
            <input
              type="file"
              accept=".zip"
              disabled={isUploading}
              onChange={handleFileUpload}
              className="hidden"
            />
            {isUploading ? (
              <span className="flex items-center gap-2">
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Analyzing Archive...
              </span>
            ) : (
              <span>↑ Upload / Re-analyze Zip</span>
            )}
          </label>

          <button
            onClick={handleDelete}
            className="btn-secondary text-xs text-red-400 hover:text-red-300 border-red-500/20 hover:border-red-500/40"
          >
            Delete Project
          </button>
        </div>
      </div>

      {uploadError && (
        <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs">
          {uploadError}
        </div>
      )}

      {/* ── AI Insights Panel ──────────────────────────────────────────────── */}
      <AIInsightsPanel
        projectId={project.id}
        hasRepository={!!project.archive_filename}
        existingRun={geminiRun}
        onAnalysisComplete={(run) => {
          setGeminiRun(run)
          setRuns((prev) => [run, ...prev])
        }}
      />

      {/* ── Top Metric Cards ─────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <div className="glass-card p-6">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-neutral-400 mb-2">
            Total Lines of Code
          </div>
          <div className="text-3xl font-bold text-white">
            {analysis?.total_loc ? analysis.total_loc.toLocaleString() : '0'}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">Non-empty source code lines</div>
        </div>

        <div className="glass-card p-6">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-neutral-400 mb-2">
            Files Analyzed
          </div>
          <div className="text-3xl font-bold text-white">
            {analysis?.total_files ? analysis.total_files.toLocaleString() : '0'}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">Recognized source extensions</div>
        </div>

        <div className="glass-card p-6">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-neutral-400 mb-2">
            Dominant Language
          </div>
          <div className="text-3xl font-bold text-brand-300">
            {analysis?.primary_language || 'None'}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">By line of code volume</div>
        </div>

        <div className="glass-card p-6">
          <div className="text-[10px] uppercase font-semibold tracking-wider text-neutral-400 mb-2">
            Detected Frameworks
          </div>
          <div className="text-3xl font-bold text-emerald-400">
            {analysis?.detected_frameworks ? analysis.detected_frameworks.length : '0'}
          </div>
          <div className="text-[11px] text-neutral-500 mt-1">Identified via dependencies</div>
        </div>
      </div>

      {/* ── Language Breakdown Section ───────────────────────────────────── */}
      {analysis && analysis.languages && analysis.languages.length > 0 ? (
        <div className="glass-card p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-white tracking-tight">Language Distribution</h3>
            <span className="text-xs text-neutral-400 font-mono">
              {analysis.languages.length} languages detected
            </span>
          </div>

          {/* Stacked Progress Bar */}
          <div className="w-full h-4 bg-white/5 rounded-full overflow-hidden flex border border-white/10 p-0.5">
            {analysis.languages.map((l) => (
              <div
                key={l.language}
                style={{
                  width: `${Math.max(l.percentage, 1)}%`,
                  backgroundColor: LANGUAGE_COLORS[l.language] || '#94a3b8',
                }}
                className="h-full first:rounded-l-full last:rounded-r-full transition-all duration-500 hover:opacity-90"
                title={`${l.language}: ${l.percentage}% (${l.loc.toLocaleString()} LOC)`}
              />
            ))}
          </div>

          {/* Language Breakdown Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
            {analysis.languages.map((l) => (
              <div key={l.language} className="p-3 rounded-xl bg-white/[0.02] border border-white/5">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: LANGUAGE_COLORS[l.language] || '#94a3b8' }}
                  />
                  <span className="text-xs font-semibold text-white truncate">{l.language}</span>
                </div>
                <div className="text-xs font-mono text-neutral-300">
                  {l.percentage}% <span className="text-neutral-500">({l.loc.toLocaleString()} LOC)</span>
                </div>
                <div className="text-[10px] text-neutral-500">{l.file_count} files</div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="glass-card p-12 text-center border-dashed border-white/15">
          <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mx-auto mb-3">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <h4 className="text-base font-semibold text-white mb-1">No repository archive uploaded</h4>
          <p className="text-xs text-neutral-400 max-w-md mx-auto mb-4">
            Upload a .zip export of your codebase to run deterministic static analysis, detect frameworks, and compute LOC metrics.
          </p>
          <label className="btn-primary text-xs shadow-brand cursor-pointer inline-flex items-center">
            <input
              type="file"
              accept=".zip"
              disabled={isUploading}
              onChange={handleFileUpload}
              className="hidden"
            />
            {isUploading ? 'Analyzing...' : 'Upload Repository Archive (.zip)'}
          </label>
        </div>
      )}

      {/* ── Frameworks & Dependencies Dual Grid ─────────────────────────── */}
      {analysis && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Frameworks Card */}
          <div className="glass-card p-6">
            <h4 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-400" />
              Detected Frameworks & Libraries
            </h4>
            {analysis.detected_frameworks.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {analysis.detected_frameworks.map((fw) => (
                  <span
                    key={fw}
                    className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs font-medium text-white flex items-center gap-1.5 shadow-sm"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {fw}
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-neutral-400">No common frameworks recognized.</p>
            )}
          </div>

          {/* Manifests Card */}
          <div className="glass-card p-6">
            <h4 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              Dependency Manifests
            </h4>
            {analysis.dependency_files.length > 0 ? (
              <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                {analysis.dependency_files.map((man) => (
                  <div
                    key={man.filename}
                    className="p-3 rounded-xl bg-white/[0.02] border border-white/10 text-xs"
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <span className="font-mono text-emerald-400 font-semibold">
                        {man.filename}
                      </span>
                      <span className="badge-neutral text-[10px] uppercase">
                        {man.package_manager}
                      </span>
                    </div>
                    {man.dependencies.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {man.dependencies.slice(0, 10).map((dep) => (
                          <span
                            key={dep}
                            className="px-2 py-0.5 rounded bg-white/5 text-[10px] font-mono text-neutral-300"
                          >
                            {dep}
                          </span>
                        ))}
                        {man.dependencies.length > 10 && (
                          <span className="text-[10px] text-neutral-500 self-center">
                            +{man.dependencies.length - 10} more
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-neutral-400">No dependency manifests found in archive.</p>
            )}
          </div>
        </div>
      )}

      {/* ── Agent Run History Timeline ───────────────────────────────────── */}
      <div className="glass-card p-6 sm:p-8">
        <h4 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-purple-400" />
          Agent Execution History
        </h4>

        {runs.length === 0 ? (
          <p className="text-xs text-neutral-400">No analysis runs recorded yet.</p>
        ) : (
          <div className="divide-y divide-white/5">
            {runs.map((r) => (
              <div key={r.id} className="py-3.5 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-brand-400" />
                  <div>
                    <div className="text-xs font-semibold text-white capitalize">
                      {r.agent_type} Intelligence Run
                    </div>
                    <div className="text-[10px] text-neutral-500 font-mono">
                      Run ID: {r.id.substring(0, 8)}... •{' '}
                      {new Date(r.created_at).toLocaleString()}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {r.status === 'completed' && (
                    <span className="badge-success text-[10px]">Completed</span>
                  )}
                  {r.status === 'running' && (
                    <span className="badge-info text-[10px]">Running...</span>
                  )}
                  {r.status === 'pending' && (
                    <span className="badge-neutral text-[10px]">Pending</span>
                  )}
                  {r.status === 'failed' && (
                    <span className="badge-danger text-[10px]">Failed</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
