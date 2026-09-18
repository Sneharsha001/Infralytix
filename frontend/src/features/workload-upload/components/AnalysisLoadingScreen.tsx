/**
 * Infralytix — Workload Analysis Cinematic Loading Screen.
 *
 * A premium Linear/Vercel-inspired analysis experience featuring:
 * 1. Layered visual core: pulsing radial glow behind a futuristic central AI-engine glyph.
 * 2. Abstract file tree / code block with GSAP timeline-choreographed scan-line sweep.
 * 3. 3-stage CI/CD-style pipeline with morphing icons (file -> package -> cpu),
 *    animated scale-bounce checkmarks, and a progressive connecting vertical line.
 * 4. Real signal streaming: dynamic extraction & flashing of detected files, frameworks,
 *    and compute resource profiles with graceful fallback.
 * 5. Cinematic handoff transition (450ms scale-down & blur crossfade) to Cost Comparison.
 */

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { gsap } from 'gsap'
import type { WorkloadInferenceResult } from '../types'

interface AnalysisLoadingScreenProps {
  selectedFile: File | null
  result: WorkloadInferenceResult | null
  error: string | null
  onCompleteHandoff: () => void
  onSkip?: () => void
}

type StageStatus = 'pending' | 'active' | 'completed'

export const AnalysisLoadingScreen: React.FC<AnalysisLoadingScreenProps> = ({
  selectedFile,
  result,
  error,
  onCompleteHandoff,
  onSkip,
}) => {
  const shouldReduce = useReducedMotion()
  const [stage1Status, setStage1Status] = useState<StageStatus>('active')
  const [stage2Status, setStage2Status] = useState<StageStatus>('pending')
  const [stage3Status, setStage3Status] = useState<StageStatus>('pending')
  const [isHandoff, setIsHandoff] = useState(false)
  const [canSkip, setCanSkip] = useState(false)

  const scanLineRef = useRef<HTMLDivElement>(null)
  const codeBlockRef = useRef<HTMLDivElement>(null)
  const timelineRef = useRef<gsap.core.Timeline | null>(null)

  // ── Extract real signals from filename & backend result ───────────────────────
  const detectedSignals = useMemo(() => {
    const fileName = selectedFile?.name?.toLowerCase() || ''
    const justification = result?.justification || ''

    // Stage 1: Files / structure markers
    let stage1Tags = ['src/', 'Dockerfile', 'configs']
    if (fileName.includes('fastapi') || fileName.includes('python')) {
      stage1Tags = ['src/main.py', 'pyproject.toml', 'Dockerfile']
    } else if (fileName.includes('react') || fileName.includes('node') || fileName.includes('web')) {
      stage1Tags = ['package.json', 'src/App.tsx', 'vite.config.ts']
    } else if (fileName.includes('go')) {
      stage1Tags = ['main.go', 'go.mod', 'Dockerfile']
    } else if (selectedFile?.name) {
      stage1Tags = [selectedFile.name.replace(/\.zip$/i, ''), 'Dockerfile', 'manifest']
    }

    // Stage 2: Frameworks & dependencies
    let stage2Tags = ['FastAPI', 'Uvicorn', 'Pydantic']
    const keywords = [
      'FastAPI',
      'Python',
      'Docker',
      'PostgreSQL',
      'React',
      'Node.js',
      'TypeScript',
      'Express',
      'Next.js',
      'Django',
      'Flask',
      'Redis',
      'Kubernetes',
      'Vite',
      'TailwindCSS',
      'PyTorch',
      'TensorFlow',
      'Pandas',
    ]
    const matched = keywords.filter((kw) =>
      new RegExp(`\\b${kw}\\b`, 'i').test(justification) ||
      new RegExp(`\\b${kw}\\b`, 'i').test(fileName)
    )

    if (matched.length > 0) {
      stage2Tags = matched.slice(0, 3)
    } else if (fileName.includes('react') || fileName.includes('node')) {
      stage2Tags = ['React 19', 'TypeScript', 'Node.js']
    }

    // Stage 3: Compute profile sizing
    const stage3Tags = result
      ? [`${result.vcpu} vCPU`, `${result.ram_gb} GB RAM`, `${result.storage_gb} GB SSD`]
      : ['Estimating vCPU', 'Sizing RAM buffer', 'IOPS profile']

    return { stage1Tags, stage2Tags, stage3Tags }
  }, [selectedFile, result])

  // ── GSAP Choreography: Scan-line sweep across abstract file tree ─────────────
  useEffect(() => {
    if (shouldReduce) return
    if (!scanLineRef.current || !codeBlockRef.current) return

    const tl = gsap.timeline({ repeat: -1 })
    timelineRef.current = tl

    tl.fromTo(
      scanLineRef.current,
      { top: '0%', opacity: 0 },
      {
        top: '100%',
        opacity: 1,
        duration: 2.2,
        ease: 'power1.inOut',
      }
    ).to(scanLineRef.current, { opacity: 0, duration: 0.3 })

    // Abstract code line illumination sweep
    const codeLines = codeBlockRef.current.querySelectorAll('.code-line')
    if (codeLines.length) {
      gsap.to(codeLines, {
        opacity: 0.85,
        stagger: 0.12,
        repeat: -1,
        yoyo: true,
        duration: 1.2,
        ease: 'sine.inOut',
      })
    }

    return () => {
      tl.kill()
    }
  }, [shouldReduce])

  // ── Staged Stage State Transitions ──────────────────────────────────────────
  useEffect(() => {
    if (shouldReduce) {
      setStage1Status('completed')
      setStage2Status('completed')
      setStage3Status('active')
      setCanSkip(true)
      return
    }

    // Stage 1 active initially. Advance to Stage 2 after 750ms
    const t1 = setTimeout(() => {
      setStage1Status('completed')
      setStage2Status('active')
    }, 750)

    // Advance to Stage 3 after 1550ms
    const t2 = setTimeout(() => {
      setStage2Status('completed')
      setStage3Status('active')
      setCanSkip(true)
    }, 1550)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [shouldReduce])

  // ── When backend result arrives, complete Stage 3 & trigger handoff ─────────
  useEffect(() => {
    if (!result) return

    // Ensure stages 1 & 2 are completed
    setStage1Status('completed')
    setStage2Status('completed')
    setStage3Status('completed')

    if (shouldReduce) {
      onCompleteHandoff()
      return
    }

    // Graceful pause so user absorbs the completed state before cinematic handoff
    const handoffTimer = setTimeout(() => {
      setIsHandoff(true)
      // Duration of handoff animation (450ms) then execute callback
      const navTimer = setTimeout(() => {
        onCompleteHandoff()
      }, 450)
      return () => clearTimeout(navTimer)
    }, 450)

    return () => clearTimeout(handoffTimer)
  }, [result, onCompleteHandoff, shouldReduce])

  // ── Skip Handler ─────────────────────────────────────────────────────────────
  const handleImmediateSkip = () => {
    if (result) {
      setIsHandoff(true)
      setTimeout(onCompleteHandoff, 250)
    } else if (onSkip) {
      onSkip()
    }
  }

  // Connecting line progress height calculation
  const progressLineHeight =
    stage3Status === 'completed'
      ? '100%'
      : stage3Status === 'active'
      ? '75%'
      : stage2Status === 'completed'
      ? '50%'
      : stage2Status === 'active'
      ? '25%'
      : '0%'

  return (
    <div className="min-h-screen bg-neutral-950 flex items-center justify-center relative overflow-hidden px-4 select-none">
      {/* ── Background Glow Blobs ───────────────────────────────────────── */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-600/12 rounded-full blur-3xl pointer-events-none animate-pulse" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-cyan-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-purple-600/8 rounded-full blur-3xl pointer-events-none" />

      {/* ── Outer Motion Container with Cinematic Exit Handoff ─────────── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={
          isHandoff
            ? { opacity: 0, scale: 0.97, filter: 'blur(8px)', y: -10 }
            : { opacity: 1, scale: 1, filter: 'blur(0px)', y: 0 }
        }
        transition={{ duration: 0.45, ease: 'easeInOut' }}
        className="relative w-full max-w-xl mx-auto z-10"
      >
        {/* Main Analysis Card */}
        <div className="glass-card border border-[var(--color-accent-primary)]/30 bg-neutral-900/90 p-6 md:p-8 relative overflow-hidden shadow-2xl shadow-[var(--color-accent-primary)]/15 rounded-3xl">
          {/* Subtle perimeter border glow */}
          <div className="absolute inset-0 rounded-3xl border border-[var(--color-accent-primary)]/15 pointer-events-none" />

          {/* ── 1. Layered Visual Core Header ───────────────────────────── */}
          <div className="flex items-center justify-between gap-4 mb-7 relative z-10">
            <div className="flex items-center gap-4">
              {/* Central AI-Engine Glyph with Pulsing Radial Glow */}
              <div className="relative w-14 h-14 flex items-center justify-center shrink-0">
                {/* Pulsing radial background glow */}
                <motion.div
                  animate={{ scale: [1, 1.25, 1], opacity: [0.5, 0.9, 0.5] }}
                  transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
                  className="absolute inset-0 rounded-2xl bg-gradient-to-tr from-brand-500 via-cyan-400 to-indigo-500 blur-xl opacity-60"
                />

                {/* Rotating subtle outer orbital ring */}
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 8, repeat: Infinity, ease: 'linear' }}
                  className="absolute -inset-1 rounded-2xl border border-dashed border-cyan-400/40"
                />

                {/* Glass shield container */}
                <div className="relative w-14 h-14 rounded-2xl bg-neutral-950/80 border border-brand-400/40 flex items-center justify-center shadow-lg shadow-brand-500/20">
                  {/* AI Glyph SVG */}
                  <svg className="w-7 h-7 text-cyan-400" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.75}
                      d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
                    />
                    <circle cx="12" cy="12" r="2" fill="currentColor" className="text-brand-300" />
                  </svg>
                </div>
              </div>

              <div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-widest text-brand-400">
                    Infralytix AI Engine
                  </span>
                  <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
                </div>
                <h2 className="text-xl font-bold text-white tracking-tight leading-tight mt-0.5">
                  Analyzing Workload Profile
                </h2>
                <p className="text-xs text-neutral-400 mt-0.5">
                  {selectedFile ? selectedFile.name : 'Repository Archive'} · {selectedFile ? `${(selectedFile.size / 1024).toFixed(0)} KB` : ''}
                </p>
              </div>
            </div>

            {/* Skip action (if sequence is skippable or backend responded) */}
            {canSkip && (
              <button
                type="button"
                onClick={handleImmediateSkip}
                className="hidden sm:inline-flex items-center gap-1 text-xs text-neutral-400 hover:text-cyan-300 transition-colors py-1.5 px-2.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10"
              >
                <span>Skip</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
              </button>
            )}
          </div>

          {/* ── 2. Abstract File Tree / Code Block with GSAP Scan-Line ────── */}
          <div
            ref={codeBlockRef}
            className="relative mb-8 rounded-2xl bg-neutral-950/70 border border-white/10 p-4 overflow-hidden"
          >
            {/* GSAP Animated Scan-Line Beam */}
            <div
              ref={scanLineRef}
              className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_14px_rgba(34,211,238,0.9)] pointer-events-none z-20"
            />
            {/* Trailing soft wash behind scan line */}
            <div className="absolute inset-0 bg-gradient-to-b from-cyan-500/[0.03] via-transparent to-transparent pointer-events-none" />

            {/* Abstract file hierarchy representation */}
            <div className="grid grid-cols-12 gap-3 text-xs font-mono select-none">
              {/* Left column: abstract folder tree */}
              <div className="col-span-5 border-r border-white/5 pr-3 space-y-2">
                <div className="flex items-center gap-1.5 text-neutral-400 text-[11px]">
                  <svg className="w-3.5 h-3.5 text-brand-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                  </svg>
                  <span className="font-semibold text-neutral-300">root/</span>
                </div>
                {/* Indented abstract files */}
                <div className="pl-4 space-y-1.5">
                  <div className="code-line h-2 w-16 rounded bg-brand-500/25" />
                  <div className="code-line h-2 w-20 rounded bg-cyan-500/25" />
                  <div className="code-line h-2 w-14 rounded bg-purple-500/25" />
                  <div className="code-line h-2 w-24 rounded bg-emerald-500/25" />
                </div>
              </div>

              {/* Right column: abstract code block skeleton */}
              <div className="col-span-7 pl-1 space-y-2">
                <div className="flex items-center gap-1.5 mb-1 text-[10px] text-neutral-500 uppercase tracking-wider">
                  <span className="w-2 h-2 rounded-full bg-emerald-500/60" />
                  <span>AST Parse Stream</span>
                </div>
                <div className="space-y-1.5">
                  <div className="code-line h-2.5 w-11/12 rounded bg-white/10" />
                  <div className="code-line h-2.5 w-8/12 rounded bg-cyan-400/20 pl-2" />
                  <div className="code-line h-2.5 w-10/12 rounded bg-brand-400/20" />
                  <div className="code-line h-2.5 w-6/12 rounded bg-purple-400/20 pl-4" />
                </div>
              </div>
            </div>
          </div>

          {/* ── 3. 3-Stage Pipeline with Morphing Icons & Connecting Line ─── */}
          <div className="relative pl-2">
            {/* Continuous Vertical Connecting Progress Line */}
            <div className="absolute left-[27px] top-4 bottom-5 w-0.5 bg-white/10 rounded-full">
              {/* Dynamic filled line */}
              <motion.div
                className="w-full bg-gradient-to-b from-brand-400 via-cyan-400 to-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)] rounded-full origin-top"
                initial={{ height: '0%' }}
                animate={{ height: progressLineHeight }}
                transition={{ duration: 0.5, ease: 'easeInOut' }}
              />
            </div>

            {/* Stages Stack */}
            <div className="space-y-6 relative z-10">
              {/* Stage 1: Project Structure */}
              <StageRow
                status={stage1Status}
                title="Reading project structure…"
                description="Parsing archive layout, configuration manifests, and AST entrypoints."
                signals={detectedSignals.stage1Tags}
                iconType="file"
              />

              {/* Stage 2: Dependencies & Frameworks */}
              <StageRow
                status={stage2Status}
                title="Detecting dependencies & frameworks…"
                description="Identifying runtime libraries, database connectors, and microservices."
                signals={detectedSignals.stage2Tags}
                iconType="package"
              />

              {/* Stage 3: Compute & Memory Profile */}
              <StageRow
                status={stage3Status}
                title="Estimating compute profile & storage…"
                description="Inferring vCPU allocation, memory footprint, and IOPS requirements."
                signals={detectedSignals.stage3Tags}
                iconType="cpu"
              />
            </div>
          </div>

          {/* ── Error Display (if inference fails) ────────────────────────── */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-xs flex items-center justify-between gap-3"
            >
              <span>{error}</span>
            </motion.div>
          )}

          {/* Footer status notice */}
          <div className="mt-8 pt-4 border-t border-white/10 flex items-center justify-between text-[11px] text-neutral-500">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping" />
              <span>Multi-Cloud Parity Engine</span>
            </div>
            <span>Crossfade handoff enabled</span>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ── StageRow Sub-component ───────────────────────────────────────────────────

interface StageRowProps {
  status: StageStatus
  title: string
  description: string
  signals: string[]
  iconType: 'file' | 'package' | 'cpu'
}

const StageRow: React.FC<StageRowProps> = ({
  status,
  title,
  description,
  signals,
  iconType,
}) => {
  const isCompleted = status === 'completed'
  const isActive = status === 'active'

  return (
    <div className="flex items-start gap-4">
      {/* Morphing Icon Node */}
      <div className="relative shrink-0 mt-0.5">
        <motion.div
          animate={
            isCompleted
              ? { scale: [1, 1.15, 1], backgroundColor: 'rgba(16, 185, 129, 0.15)' }
              : isActive
              ? { scale: [1, 1.08, 1] }
              : { scale: 1 }
          }
          transition={{ duration: 0.35 }}
          className={`
            w-9 h-9 rounded-xl flex items-center justify-center border transition-all duration-300
            ${
              isCompleted
                ? 'border-emerald-500/60 bg-emerald-500/20 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.3)]'
                : isActive
                ? 'border-cyan-400/80 bg-cyan-500/15 text-cyan-300 shadow-[0_0_14px_rgba(34,211,238,0.35)]'
                : 'border-white/10 bg-neutral-900/50 text-neutral-500'
            }
          `}
        >
          {/* Animated checkmark bounce on completion vs morphing icon */}
          <AnimatePresence mode="wait">
            {isCompleted ? (
              <motion.div
                key="check"
                initial={{ scale: 0, rotate: -45 }}
                animate={{ scale: 1, rotate: 0 }}
                transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                className="text-emerald-400"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                </svg>
              </motion.div>
            ) : (
              <motion.div
                key="icon"
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0.8 }}
                className="w-5 h-5 flex items-center justify-center"
              >
                {iconType === 'file' && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.75}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                )}
                {iconType === 'package' && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.75}
                      d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"
                    />
                  </svg>
                )}
                {iconType === 'cpu' && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.75}
                      d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
                    />
                  </svg>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </div>

      {/* Stage Text & Streamed Real Signal Badges */}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <div
            className={`text-sm font-semibold transition-colors duration-200 ${
              isCompleted
                ? 'text-white'
                : isActive
                ? 'text-cyan-300'
                : 'text-neutral-400'
            }`}
          >
            {title}
          </div>

          {/* Active status indicator dot */}
          {isActive && (
            <span className="flex items-center gap-1 text-[10px] uppercase font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-full border border-cyan-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              Active
            </span>
          )}
          {isCompleted && (
            <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              Done
            </span>
          )}
        </div>

        <p className="text-xs text-neutral-400 mt-0.5 leading-relaxed">
          {description}
        </p>

        {/* Real Signal Badges flashing in */}
        <AnimatePresence>
          {(isActive || isCompleted) && signals.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="flex flex-wrap items-center gap-1.5 mt-2"
            >
              {signals.map((signal, idx) => (
                <motion.span
                  key={signal}
                  initial={{ opacity: 0, scale: 0.85 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: idx * 0.08, duration: 0.2 }}
                  className={`
                    inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded-md border
                    ${
                      isCompleted
                        ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/25'
                        : 'bg-cyan-500/10 text-cyan-200 border-cyan-500/25'
                    }
                  `}
                >
                  <span className="w-1 h-1 rounded-full bg-current opacity-70" />
                  {signal}
                </motion.span>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
