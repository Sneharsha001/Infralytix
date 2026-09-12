/**
 * Infralytix — Workload Upload & Auto-Detection Page.
 *
 * A full-screen upload flow that:
 *  1. Lets users drag-and-drop or browse for a repository .zip archive.
 *  2. On upload, shows a Framer Motion animated "Analyzing workload..." sequence
 *     with staged status lines and a pulsing code-particle background.
 *  3. On success, navigates to CostComparisonPage with inferred vcpu/ram/storage
 *     pre-filled via React Router state.
 *  4. On error, shows a dismissible error banner with a retry option.
 */

import React, { useCallback, useRef, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import { projectsApi } from '@/features/projects/api'
import { workloadUploadApi } from './api'

// ─── Types & Constants ────────────────────────────────────────────────────────

type UploadPhase = 'idle' | 'analyzing' | 'error'

const ANALYSIS_STAGES = [
  { id: 'tree',  label: 'Reading project structure…',   delay: 0 },
  { id: 'deps',  label: 'Detecting dependencies…',      delay: 1200 },
  { id: 'infer', label: 'Estimating compute profile…',  delay: 2400 },
]

// Pseudo file-tree lines shown in the animated background panel
const FAKE_TREE_LINES = [
  '├── src/',
  '│   ├── main.py',
  '│   ├── api/',
  '│   │   ├── routes.py',
  '│   │   └── models.py',
  '│   └── services/',
  '│       └── inference.py',
  '├── tests/',
  '│   ├── conftest.py',
  '│   └── test_api.py',
  '├── Dockerfile',
  '├── requirements.txt',
  '└── pyproject.toml',
]

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Animated staged status line */
const StageItem: React.FC<{ label: string; delay: number; isActive: boolean }> = ({
  label,
  delay,
  isActive,
}) => (
  <AnimatePresence>
    {isActive && (
      <motion.div
        key={label}
        initial={{ opacity: 0, x: -16, filter: 'blur(4px)' }}
        animate={{ opacity: 1, x: 0, filter: 'blur(0px)' }}
        exit={{ opacity: 0.4 }}
        transition={{ duration: 0.5, ease: 'easeOut', delay: delay / 1000 }}
        className="flex items-center gap-3 text-sm font-mono"
      >
        <motion.span
          animate={{ scale: [1, 1.3, 1], opacity: [0.6, 1, 0.6] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          className="w-2 h-2 rounded-full bg-brand-400 shrink-0"
        />
        <span className="text-neutral-200">{label}</span>
      </motion.div>
    )}
  </AnimatePresence>
)

/** Ghost code-tree lines behind the analysis panel */
const GhostTree: React.FC = () => (
  <div className="absolute inset-0 pointer-events-none overflow-hidden select-none">
    <div className="absolute left-6 top-8 font-mono text-[11px] text-brand-500/20 leading-6 space-y-0">
      {FAKE_TREE_LINES.map((line, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.6, 0.3] }}
          transition={{ duration: 1, delay: i * 0.08, repeat: Infinity, repeatDelay: 4 }}
        >
          {line}
        </motion.div>
      ))}
    </div>
    {/* Scanline overlay */}
    <div className="scan-line" />
  </div>
)

/** Horizontal scanning bar that sweeps top-to-bottom */
const ScanBeam: React.FC = () => (
  <motion.div
    className="absolute left-0 right-0 h-px bg-gradient-to-r from-transparent via-brand-400/60 to-transparent"
    initial={{ top: '0%' }}
    animate={{ top: ['0%', '100%', '0%'] }}
    transition={{ duration: 3.5, repeat: Infinity, ease: 'linear' }}
  />
)

// ─── Main Component ───────────────────────────────────────────────────────────

export const WorkloadUploadPage: React.FC = () => {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [phase, setPhase] = useState<UploadPhase>('idle')
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activeStages, setActiveStages] = useState<Set<string>>(new Set())

  // ── File validation helper ──────────────────────────────────────────────────
  const validateAndSet = useCallback((file: File): boolean => {
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Please select a valid .zip repository archive.')
      return false
    }
    if (file.size > 100 * 1024 * 1024) {
      setError('Archive is too large (max 100 MB). Consider excluding node_modules and build outputs.')
      return false
    }
    setError(null)
    setSelectedFile(file)
    return true
  }, [])

  // ── Drag-and-drop handlers ──────────────────────────────────────────────────
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }
  const handleDragLeave = () => setIsDragging(false)
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) validateAndSet(file)
  }
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) validateAndSet(file)
  }

  // ── Staged analysis animation ───────────────────────────────────────────────
  const runStagedAnimation = () => {
    ANALYSIS_STAGES.forEach(({ id, delay }) => {
      setTimeout(() => {
        setActiveStages((prev) => new Set([...prev, id]))
      }, delay)
    })
  }

  // ── Upload + Inference pipeline ─────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select a .zip archive before analyzing.')
      return
    }

    setPhase('analyzing')
    setActiveStages(new Set())
    runStagedAnimation()
    setError(null)

    try {
      // Step 1: Create a temporary project to satisfy the ownership check
      const tempProject = await projectsApi.create({
        name: `workload-inference-${Date.now()}`,
        description: 'Temporary project for workload inference',
      })

      // Step 2: Run inference (Gemini or heuristic fallback)
      const result = await workloadUploadApi.inferWorkload(tempProject.id, selectedFile)

      // Step 3: Clean up the temp project (best-effort, don't block on failure)
      projectsApi.delete(tempProject.id).catch(() => {/* ignore */})

      // Step 4: Navigate to Cost Comparison with pre-filled values
      navigate('/cost-comparison', {
        state: {
          vcpu: result.vcpu,
          ram_gb: result.ram_gb,
          storage_gb: result.storage_gb,
          justification: result.justification,
          autoDetected: true,
        },
      })
    } catch (err: unknown) {
      const msg =
        err instanceof Error
          ? err.message
          : 'Failed to analyze repository. Please try again or enter specs manually.'
      setError(msg)
      setPhase('error')
    }
  }

  const handleRetry = () => {
    setPhase('idle')
    setError(null)
    setActiveStages(new Set())
    setSelectedFile(null)
  }


  // ─── Render: Analyzing Phase ─────────────────────────────────────────────

  if (phase === 'analyzing') {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center relative overflow-hidden">
        {/* Ambient glow blobs */}
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-600/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-600/8 rounded-full blur-3xl pointer-events-none" />

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
          className="relative w-full max-w-lg mx-4"
        >
          {/* Main analysis panel */}
          <div className="glass-card border border-brand-500/20 bg-neutral-900/80 p-8 relative overflow-hidden shadow-2xl shadow-brand-500/10">
            <GhostTree />
            <ScanBeam />

            {/* Header */}
            <div className="relative z-10 mb-8">
              <div className="flex items-center gap-3 mb-4">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
                  className="w-8 h-8 border-2 border-brand-500/30 border-t-brand-400 rounded-full"
                />
                <div>
                  <div className="text-xs font-semibold uppercase tracking-widest text-brand-400 mb-0.5">
                    Infralytix AI Engine
                  </div>
                  <h2 className="text-lg font-bold text-white leading-tight">
                    Analyzing Workload…
                  </h2>
                </div>
              </div>

              <div className="h-px bg-gradient-to-r from-brand-500/40 via-brand-400/20 to-transparent mb-6" />

              {/* Staged status lines */}
              <div className="space-y-4">
                {ANALYSIS_STAGES.map(({ id, label, delay }) => (
                  <StageItem
                    key={id}
                    label={label}
                    delay={delay}
                    isActive={activeStages.has(id)}
                  />
                ))}
              </div>
            </div>

            {/* File being analyzed */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="relative z-10 mt-6 p-3 rounded-xl bg-white/[0.04] border border-white/8 flex items-center gap-3"
            >
              <div className="w-8 h-8 rounded-lg bg-brand-500/15 flex items-center justify-center shrink-0">
                <svg className="w-4 h-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="min-w-0">
                <div className="text-xs text-neutral-300 font-medium truncate">
                  {selectedFile?.name}
                </div>
                <div className="text-[11px] text-neutral-500 mt-0.5">
                  {selectedFile ? `${(selectedFile.size / 1024).toFixed(0)} KB` : ''}
                </div>
              </div>
            </motion.div>
          </div>

          {/* Particle dots grid (decorative) */}
          <div className="particle-grid absolute inset-0 pointer-events-none -z-10" />
        </motion.div>
      </div>
    )
  }

  // ─── Render: Idle / Error Phase ──────────────────────────────────────────
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center px-4 py-8 md:py-12">
      {/* Top Navigation Bar */}
      <div className="w-full max-w-3xl mb-8 flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center font-bold text-white shadow-lg shadow-brand-500/30">
            IX
          </div>
          <div>
            <Link to="/" className="text-xl font-bold gradient-text tracking-tight hover:opacity-90">
              Infralytix
            </Link>
            <div className="text-[11px] uppercase tracking-wider text-neutral-400 font-medium">
              Workload Detection
            </div>
          </div>
        </div>
        <nav className="flex items-center gap-2 text-sm">
          <Link
            to="/cost-comparison"
            className="px-3.5 py-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Cost Comparison
          </Link>
          <Link
            to="/workflows"
            className="px-3.5 py-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            Workflow Optimizer
          </Link>
        </nav>
      </div>

      {/* Page Header */}
      <header className="w-full max-w-3xl text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium bg-brand-500/15 text-brand-300 ring-1 ring-brand-500/30 mb-4">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          <span>AI-Powered Workload Detection</span>
        </div>
        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
          Upload Your Project &{' '}
          <span className="gradient-text">Auto-Detect Compute</span>
        </h1>
        <p className="text-neutral-400 text-sm md:text-base max-w-xl mx-auto">
          Drop your repository zip and let Infralytix infer the right vCPU, RAM, and storage
          profile — then jump straight to a live multi-cloud cost comparison.
        </p>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="w-full max-w-3xl mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={handleRetry}
              className="text-xs font-medium underline hover:text-white"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={() => setError(null)}
              className="text-xs underline hover:text-white"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}


      {/* Upload Card */}
      <section className="w-full max-w-3xl">
        <div className="glass-card p-8 md:p-10 relative overflow-hidden shadow-2xl">
          {/* Decorative glow */}
          <div className="absolute top-0 right-0 w-64 h-64 bg-brand-500/8 rounded-full blur-3xl pointer-events-none" />

          <div className="relative z-10">
            {/* Drop zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`
                relative cursor-pointer rounded-2xl border-2 border-dashed p-10 md:p-14 text-center
                transition-all duration-200
                ${isDragging
                  ? 'border-brand-400 bg-brand-500/10 scale-[1.01]'
                  : selectedFile
                    ? 'border-emerald-500/50 bg-emerald-500/5'
                    : 'border-white/15 hover:border-brand-500/50 hover:bg-white/[0.02]'
                }
              `}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".zip"
                className="hidden"
                onChange={handleFileChange}
                id="workload-upload-input"
              />

              <AnimatePresence mode="wait">
                {selectedFile ? (
                  <motion.div
                    key="file-selected"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="flex flex-col items-center gap-4"
                  >
                    {/* Zip icon */}
                    <div className="w-14 h-14 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center">
                      <svg className="w-7 h-7 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <div className="text-white font-semibold text-base mb-1 truncate max-w-xs">
                        {selectedFile.name}
                      </div>
                      <div className="text-neutral-400 text-sm">
                        {(selectedFile.size / 1024).toFixed(0)} KB — ready to analyze
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); setSelectedFile(null); setError(null) }}
                      className="text-xs text-neutral-500 hover:text-red-400 transition-colors underline"
                    >
                      Remove
                    </button>
                  </motion.div>
                ) : (
                  <motion.div
                    key="drop-prompt"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -8 }}
                    className="flex flex-col items-center gap-4"
                  >
                    {/* Upload icon */}
                    <motion.div
                      animate={isDragging ? { scale: 1.15, y: -4 } : { scale: 1, y: 0 }}
                      transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                      className="w-14 h-14 rounded-2xl bg-brand-500/15 border border-brand-500/30 flex items-center justify-center"
                    >
                      <svg className="w-7 h-7 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                          d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                    </motion.div>

                    <div>
                      <div className="text-white font-semibold text-base mb-1">
                        {isDragging ? 'Release to upload' : 'Drag & drop your repository'}
                      </div>
                      <div className="text-neutral-400 text-sm">
                        or{' '}
                        <span className="text-brand-400 font-medium">browse for a .zip file</span>
                      </div>
                    </div>

                    <div className="text-[11px] text-neutral-600 mt-1">
                      Supports standard repository archives · Max 100 MB
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Analyze CTA */}
            <div className="mt-6 flex flex-col sm:flex-row items-center gap-4 justify-between">
              <p className="text-xs text-neutral-500 max-w-sm">
                Your archive is analyzed locally on the server and deleted immediately after inference.
                No code is stored.
              </p>
              <button
                type="button"
                onClick={handleAnalyze}
                disabled={!selectedFile}
                className="btn-primary w-full sm:w-auto px-8 py-3 text-sm font-semibold shadow-lg shadow-brand-600/20"
              >
                Analyze & Detect Workload →
              </button>
            </div>

            {/* Divider with "or" */}
            <div className="flex items-center gap-4 my-8">
              <div className="h-px bg-white/10 flex-1" />
              <span className="text-xs text-neutral-500 font-medium">or skip upload</span>
              <div className="h-px bg-white/10 flex-1" />
            </div>

            {/* Manual entry shortcut */}
            <Link
              to="/cost-comparison"
              className="flex items-center justify-center gap-2 w-full px-6 py-3 rounded-xl border border-white/10 bg-white/[0.03] hover:bg-white/[0.06] hover:border-white/20 text-neutral-300 hover:text-white text-sm font-medium transition-all duration-150"
            >
              <svg className="w-4 h-4 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Enter specs manually instead
            </Link>
          </div>
        </div>

        {/* Feature highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          {[
            {
              icon: (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
              ),
              title: 'Static Analysis',
              desc: 'Reads file tree, LOC, and detected frameworks without executing code.',
            },
            {
              icon: (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M13 10V3L4 14h7v7l9-11h-7z" />
              ),
              title: 'Gemini Inference',
              desc: 'Gemini 1.5 Flash infers realistic vCPU, RAM, and storage from repo metadata.',
            },
            {
              icon: (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              ),
              title: 'Fully Editable',
              desc: 'All inferred values land as editable defaults — override any field before comparing.',
            },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="glass-card p-4 flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-brand-500/10 flex items-center justify-center shrink-0 mt-0.5">
                <svg className="w-4 h-4 text-brand-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  {icon}
                </svg>
              </div>
              <div>
                <div className="text-xs font-semibold text-white mb-0.5">{title}</div>
                <div className="text-[11px] text-neutral-500 leading-relaxed">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full max-w-3xl text-center text-xs text-neutral-600 border-t border-white/5 pt-6 mt-10">
        Infralytix Cloud Intelligence Platform — AI-powered workload profiling.
      </footer>
    </div>
  )
}

export default WorkloadUploadPage
