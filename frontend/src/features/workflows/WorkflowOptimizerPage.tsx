/**
 * Infralytix — Multi-Cloud Workflow Optimizer Page.
 *
 * Provides:
 * 1. JSON workflow upload / paste interface with real-time client-side schema validation.
 * 2. Interactive React Flow DAG preview for validated dependency graphs.
 * 3. Multi-cloud Pareto sweep invocation across AWS, Azure, and GCP.
 * 4. Interactive Recharts scatter plot (Cost vs Makespan) with highlighted Pareto frontier.
 * 5. Highlighted Fastest / Cheapest / Best Balance candidate cards.
 * 6. AI-generated architectural plain-language summary.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { PublicNav } from '@/components/layout'
import { Hero3DCanvas } from '@/components/3d'
import { apiClient } from '@/lib/api-client'
import { AiSummaryCard } from './components/AiSummaryCard'
import { DagPreview } from './components/DagPreview'
import { ParetoScatterChart } from './components/ParetoScatterChart'
import { SAMPLE_WORKFLOWS } from './sampleWorkflows'
import { ValidationFeedback, WorkflowOptimizeResult, WorkflowTaskInput } from './types'
import { validateWorkflowJson } from './validation'

// ─── Staged loading status lines ─────────────────────────────────────────────

const LOADING_STAGES = [
  { label: 'Fetching live AWS EC2 price catalog…',    delay: 0 },
  { label: 'Fetching Azure Retail API pricing…',       delay: 600 },
  { label: 'Fetching GCP Cloud Billing rates…',        delay: 1100 },
  { label: 'Computing critical-path makespan DAG…',    delay: 1700 },
  { label: 'Filtering non-dominated Pareto frontier…', delay: 2300 },
  { label: 'Generating AI architectural summary…',     delay: 2900 },
]

const StagedLoader: React.FC = () => {
  const shouldReduce = useReducedMotion()
  const [activeStage, setActiveStage] = useState(shouldReduce ? LOADING_STAGES.length - 1 : 0)

  useEffect(() => {
    if (shouldReduce) return
    const timers = LOADING_STAGES.slice(1).map((s, i) =>
      setTimeout(() => setActiveStage(i + 1), s.delay)
    )
    return () => timers.forEach(clearTimeout)
  }, [shouldReduce])

  return (
    <div className="glass-card p-8 rounded-2xl space-y-6">
      <div className="flex flex-col items-center justify-center py-6 text-center space-y-4">
        <div className="relative">
          <div className="w-14 h-14 border-4 border-brand-500/20 border-t-brand-500 rounded-full animate-spin" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-6 h-6 border-2 border-indigo-400/30 border-t-indigo-400 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.7s' }} />
          </div>
        </div>
        <div>
          <div className="text-base font-bold text-white mb-1">
            Sweeping Live AWS, Azure &amp; GCP Pricing Catalogs…
          </div>
          <p className="text-xs text-neutral-400 max-w-md">
            Querying concurrent cloud rate APIs, shortlisting peak-sized compute candidates,
            computing category-aware makespan, and filtering non-dominated Pareto frontier.
          </p>
        </div>
      </div>

      {/* Staged status lines */}
      <div className="space-y-2 max-w-sm mx-auto">
        {LOADING_STAGES.map((stage, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: idx <= activeStage ? 1 : 0.2, x: 0 }}
            transition={{ duration: 0.35, delay: idx === 0 ? 0 : 0 }}
            className="flex items-center gap-2.5 text-xs"
          >
            <span
              className={[
                'w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-500',
                idx < activeStage
                  ? 'bg-[var(--color-success)]'
                  : idx === activeStage
                  ? 'bg-brand-400 animate-pulse'
                  : 'bg-neutral-700',
              ].join(' ')}
            />
            <span className={idx <= activeStage ? 'text-neutral-300' : 'text-neutral-600'}>
              {stage.label}
            </span>
          </motion.div>
        ))}
      </div>

      {/* Skeleton cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="skeleton h-24 rounded-xl" />
        <div className="skeleton h-24 rounded-xl" />
        <div className="skeleton h-24 rounded-xl" />
      </div>
      <div className="skeleton h-80 rounded-xl" />
    </div>
  )
}

const REGION_OPTIONS = [
  { value: 'us-east', label: 'US East (N. Virginia — us-east-1 / eastus / us-east4)' },
  { value: 'us-west', label: 'US West (Oregon — us-west-2 / westus2 / us-west1)' },
  { value: 'eu-west', label: 'Europe West (Ireland / Frankfurt — eu-west-1 / westeurope)' },
  { value: 'us', label: 'US Central (Iowa / Default US)' },
  { value: 'eu', label: 'Europe (Default EU Datacenters)' },
  { value: 'asia', label: 'Asia Pacific (Singapore / Taiwan / Tokyo)' },
]

export const WorkflowOptimizerPage: React.FC = () => {
  const [jsonInput, setJsonInput] = useState<string>(SAMPLE_WORKFLOWS.diamond_dag.json)
  const [region, setRegion] = useState<string>('us-east')
  const [activeTab, setActiveTab] = useState<'paste' | 'upload'>('paste')

  // Validation state
  const [validTasks, setValidTasks] = useState<WorkflowTaskInput[] | null>(null)
  const [validation, setValidation] = useState<ValidationFeedback>({
    isValid: false,
    errors: [],
    taskCount: 0,
    peakVcpu: 0,
    peakRamGb: 0,
    totalBaselineSeconds: 0,
  })

  // Sweep API state
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [result, setResult] = useState<WorkflowOptimizeResult | null>(null)
  const [apiError, setApiError] = useState<string | null>(null)

  // Run real-time client-side validation whenever JSON input changes
  useEffect(() => {
    const { parsed, feedback } = validateWorkflowJson(jsonInput)
    setValidTasks(parsed)
    setValidation(feedback)
  }, [jsonInput])

  // Handle File Upload
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result as string
      setJsonInput(content)
      setActiveTab('paste') // switch to paste tab to view content
    }
    reader.readAsText(file)
  }

  // Handle Drag & Drop
  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    e.stopPropagation()
    const file = e.dataTransfer.files?.[0]
    if (file && file.type.includes('json')) {
      const reader = new FileReader()
      reader.onload = (event) => {
        const content = event.target?.result as string
        setJsonInput(content)
        setActiveTab('paste')
      }
      reader.readAsText(file)
    }
  }, [])

  // Handle Form Submission: Query /api/v1/workflows/optimize
  const handleOptimize = async () => {
    if (!validTasks || !validation.isValid) return

    setIsLoading(true)
    setApiError(null)

    try {
      const response = await apiClient.post<WorkflowOptimizeResult>(
        '/workflows/optimize',
        {
          workflow: {
            tasks: validTasks,
          },
          region,
        }
      )
      setResult(response.data)
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { error?: { message?: string } } } })?.response?.data
          ?.error?.message ||
        (err as Error).message ||
        'Workflow Pareto optimization failed. Please verify connectivity and try again.'
      setApiError(errorMsg)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="relative min-h-screen bg-neutral-950 text-white flex flex-col items-center px-4 py-8 md:py-12 overflow-hidden">
      {/* ── Signature 3D Multi-Cloud Infrastructure Scene ───────────────── */}
      <Hero3DCanvas variant="optimize" />

      {/* ── Top Navigation Header ─────────────────────────────────────────── */}
      <PublicNav subtitle="Multi-Cloud Workflow Optimizer" />

      {/* ── Main Container ────────────────────────────────────────────────── */}
      <main className="w-full max-w-6xl space-y-8 relative z-10">
        {/* Title Banner */}
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <span className="badge-info text-xs font-semibold">
            Pareto Multi-Objective Scheduling
          </span>
          <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white">
            Workflow DAG Optimizer
          </h1>
          <p className="text-sm md:text-base text-neutral-400">
            Upload a workflow DAG to evaluate makespan and financial cost across AWS, Azure, and GCP
            catalogs, deriving the non-dominated Pareto efficiency frontier.
          </p>
        </div>

        {/* ── Workflow Input & Presets Section ────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left: JSON Input Card (5 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <div className="glass-card p-5 md:p-6 rounded-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-white/10 pb-3">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold text-white">Workflow Definition</span>
                  {validation.isValid ? (
                    <span className="badge-success text-[10px]">Valid Schema</span>
                  ) : (
                    <span className="badge-danger text-[10px]">Invalid Schema</span>
                  )}
                </div>

                {/* Tabs */}
                <div className="flex items-center gap-1 bg-white/5 p-1 rounded-lg border border-white/10 text-xs">
                  <button
                    type="button"
                    onClick={() => setActiveTab('paste')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      activeTab === 'paste'
                        ? 'bg-brand-600 text-white font-medium shadow-sm'
                        : 'text-neutral-400 hover:text-white'
                    }`}
                  >
                    Paste JSON
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveTab('upload')}
                    className={`px-2.5 py-1 rounded-md transition-all ${
                      activeTab === 'upload'
                        ? 'bg-brand-600 text-white font-medium shadow-sm'
                        : 'text-neutral-400 hover:text-white'
                    }`}
                  >
                    Upload File
                  </button>
                </div>
              </div>

              {/* Sample Workflow Selector */}
              <div>
                <div className="text-xs text-neutral-400 mb-2">Load Pre-configured Template:</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(SAMPLE_WORKFLOWS).map(([key, sample]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setJsonInput(sample.json)
                        setActiveTab('paste')
                      }}
                      className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-neutral-300 hover:text-white transition-all text-left"
                    >
                      {sample.name}
                    </button>
                  ))}
                </div>
              </div>

              {/* Input Modes */}
              {activeTab === 'paste' ? (
                <div className="space-y-1.5">
                  <label className="text-xs text-neutral-400">JSON Payload</label>
                  <textarea
                    value={jsonInput}
                    onChange={(e) => setJsonInput(e.target.value)}
                    rows={12}
                    className="w-full font-mono text-xs p-3.5 rounded-xl bg-neutral-950/80 border border-white/10 text-neutral-200 focus:outline-none focus:border-[var(--color-accent-primary)] focus:ring-1 focus:ring-[var(--color-accent-primary)]/50 resize-y leading-relaxed"
                    placeholder="Paste workflow JSON containing { tasks: [...] }..."
                  />
                </div>
              ) : (
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  className="border-2 border-dashed border-white/15 hover:border-[var(--color-accent-primary)]/50 rounded-xl p-8 text-center bg-white/[0.02] transition-colors cursor-pointer space-y-3"
                >
                  <div className="w-10 h-10 mx-auto rounded-full bg-[var(--color-accent-primary)]/10 flex items-center justify-center text-[var(--color-accent-primary)]">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-white">Choose a .json workflow file</span>
                    <p className="text-xs text-neutral-400 mt-1">or drag and drop here</p>
                  </div>
                  <input
                    type="file"
                    accept=".json,application/json"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="workflow-file-input"
                  />
                  <label
                    htmlFor="workflow-file-input"
                    className="btn-secondary text-xs px-4 py-1.5 cursor-pointer inline-block"
                  >
                    Browse Local File
                  </label>
                </div>
              )}

              {/* Validation Feedback Alert */}
              {!validation.isValid && validation.errors.length > 0 && (
                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/25 text-red-300 text-xs space-y-1">
                  <div className="font-semibold flex items-center gap-1.5">
                    <span>⚠️</span> Validation Errors:
                  </div>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-red-200">
                    {validation.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Success Metrics Banner */}
              {validation.isValid && (
                <div className="p-3 rounded-xl bg-[var(--color-success)]/10 border border-[var(--color-success)]/25 text-xs text-[var(--color-success)] flex flex-wrap items-center justify-between gap-2 font-mono">
                  <span>Tasks: {validation.taskCount}</span>
                  <span>Peak: {validation.peakVcpu} vCPU • {validation.peakRamGb} GB</span>
                  <span>Baseline: {validation.totalBaselineSeconds}s</span>
                </div>
              )}

              {/* Region & Action Controls */}
              <div className="space-y-3 pt-2 border-t border-white/10">
                <div>
                  <label className="block text-xs text-neutral-400 mb-1.5">
                    Target Geographic Region
                  </label>
                  <select
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    className="input-field py-2.5 text-xs"
                  >
                    {REGION_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value} className="bg-neutral-900 text-white">
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <button
                  type="button"
                  onClick={handleOptimize}
                  disabled={!validation.isValid || isLoading}
                  className="btn-primary w-full py-3 text-sm font-semibold shadow-lg shadow-[var(--color-accent-primary)]/25"
                >
                  {isLoading ? (
                    <span className="flex items-center gap-2">
                      <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Evaluating Multi-Cloud Pareto Sweep...
                    </span>
                  ) : (
                    'Run Pareto Optimization Sweep'
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Right: Interactive DAG Preview (6 cols) */}
          <div className="lg:col-span-6 space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Graph Topology Preview
              </h2>
              {validTasks && (
                <span className="text-xs text-neutral-400 font-mono">
                  {validTasks.length} {validTasks.length === 1 ? 'task' : 'tasks'}
                </span>
              )}
            </div>

            <DagPreview tasks={validTasks || []} />
          </div>
        </div>

        {/* ── API Error Notice ──────────────────────────────────────────────── */}
        {apiError && (
          <div className="glass-card p-4 rounded-xl border border-red-500/30 bg-red-950/20 text-red-300 text-sm flex items-center gap-3">
            <span className="text-lg">❌</span>
            <div>
              <div className="font-semibold">Optimization Sweep Failed</div>
              <div className="text-xs text-red-200 mt-0.5">{apiError}</div>
            </div>
          </div>
        )}

        {/* ── Loading State (staged status lines) ──────────────────────────── */}
        <AnimatePresence>
          {isLoading && (
            <motion.div
              key="loader"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35 }}
            >
              <StagedLoader />
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Pareto Sweep Results ──────────────────────────────────────────── */}
        <AnimatePresence>
          {result && !isLoading && (
            <motion.section
              key="results"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.45 }}
              className="space-y-6"
            >
              <ParetoScatterChart result={result} />
              <AiSummaryCard result={result} />
            </motion.section>
          )}
        </AnimatePresence>
      </main>

      {/* ── Footer ────────────────────────────────────────────────────────── */}
      <footer className="w-full max-w-6xl text-center text-xs text-neutral-500 border-t border-white/5 pt-6 mt-16">
        Infralytix Cloud Intelligence Platform — Multi-Objective DAG Scheduling &amp; Pareto Frontier Engine.
      </footer>
    </div>
  )
}

export default WorkflowOptimizerPage
