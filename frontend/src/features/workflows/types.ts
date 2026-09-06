/**
 * Infralytix — Workflow Feature Types.
 *
 * Types for workflow DAG definitions, validation results,
 * instance evaluation, and multi-cloud Pareto optimization output.
 */

export type TaskCategory = 'cpu_bound' | 'io_bound' | 'memory_bound' | 'gpu_bound'

export interface WorkflowTaskInput {
  id: string
  name: string
  category: TaskCategory
  baseline_time_seconds: number
  baseline_vcpu: number
  baseline_ram_gb: number
  depends_on: string[]
}

export interface WorkflowCreateInput {
  tasks: WorkflowTaskInput[]
}

export interface ValidationFeedback {
  isValid: boolean
  errors: string[]
  taskCount: number
  peakVcpu: number
  peakRamGb: number
  totalBaselineSeconds: number
}

export interface InstanceSpec {
  vcpu: number
  ram_gb: number
  hourly_price_usd: number
  has_gpu: boolean
}

export interface TaskEvaluation {
  task_id: string
  scaled_time_seconds: number
  cost_usd: number
  is_compatible: boolean
  notes: string | null
}

export interface WorkflowEvaluation {
  makespan_seconds: number
  total_cost_usd: number
  is_fully_compatible: boolean
  task_evaluations: TaskEvaluation[]
}

export interface CandidateResult {
  provider: 'aws' | 'azure' | 'gcp' | string
  instance_type: string
  instance_spec: InstanceSpec
  evaluation: WorkflowEvaluation
  provider_error: string | null
}

export interface ParetoPoint {
  candidate: CandidateResult
  total_cost: number
  makespan: number
  label: string | null
}

export interface WorkflowOptimizeResult {
  pareto_front: ParetoPoint[]
  all_candidates: CandidateResult[]
  provider_errors: string[]
  candidates_evaluated: number
  candidates_pareto: number
  ai_summary: string | null
}
