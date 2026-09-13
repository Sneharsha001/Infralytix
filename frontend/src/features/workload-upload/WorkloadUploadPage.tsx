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
import axios from 'axios'
import { AnimatePresence, motion } from 'framer-motion'
import { Link, useNavigate } from 'react-router-dom'
import { workloadUploadApi } from './api'

import { AnalysisLoadingScreen } from './components/AnalysisLoadingScreen'
import type { WorkloadInferenceResult } from './types'
import { PublicNav } from '@/components/layout'

// ─── Types & Constants ────────────────────────────────────────────────────────

type UploadPhase = 'idle' | 'analyzing' | 'error'

// ─── Main Component ───────────────────────────────────────────────────────────

export const WorkloadUploadPage: React.FC = () => {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [phase, setPhase] = useState<UploadPhase>('idle')
  const [isDragging, setIsDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [inferenceResult, setInferenceResult] = useState<WorkloadInferenceResult | null>(null)

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

  // ── Upload + Inference pipeline ─────────────────────────────────────────────
  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select a .zip archive before analyzing.')
      return
    }

    setPhase('analyzing')
    setInferenceResult(null)
    setError(null)

    try {
      // Run inference directly via public endpoint (no temp project or auth required)
      const result = await workloadUploadApi.inferWorkload(selectedFile)
      setInferenceResult(result)
    } catch (err: unknown) {
      let msg = 'Failed to analyze repository. Please try again or enter specs manually.'
      if (axios.isAxiosError(err)) {
        if (err.response?.data?.detail) {
          msg =
            typeof err.response.data.detail === 'string'
              ? err.response.data.detail
              : JSON.stringify(err.response.data.detail)
        } else if (err.message) {
          msg = err.message
        }
      } else if (err instanceof Error) {
        msg = err.message
      }
      setError(msg)
      setPhase('error')
    }
  }

  const handleHandoff = useCallback(() => {
    if (!inferenceResult) return
    navigate('/cost-comparison', {
      state: {
        vcpu: inferenceResult.vcpu,
        ram_gb: inferenceResult.ram_gb,
        storage_gb: inferenceResult.storage_gb,
        justification: inferenceResult.justification,
        autoDetected: true,
      },
    })
  }, [inferenceResult, navigate])

  const handleRetry = () => {
    setPhase('idle')
    setError(null)
    setInferenceResult(null)
    setSelectedFile(null)
  }

  // ─── Render: Analyzing Phase ─────────────────────────────────────────────

  if (phase === 'analyzing') {
    return (
      <AnalysisLoadingScreen
        selectedFile={selectedFile}
        result={inferenceResult}
        error={error}
        onCompleteHandoff={handleHandoff}
        onSkip={handleHandoff}
      />
    )
  }

  // ─── Render: Idle / Error Phase ──────────────────────────────────────────
  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center px-4 py-8 md:py-12">
      {/* Top Navigation Bar */}
      <PublicNav subtitle="Workload Detection" />

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
        <div className="glass-card p-8 md:p-10 relative overflow-hidden elev-3">
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
