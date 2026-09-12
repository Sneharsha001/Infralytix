/**
 * Infralytix — Workload Upload Feature Types.
 */

export interface WorkloadInferenceResult {
  vcpu: number
  ram_gb: number
  storage_gb: number
  justification: string
}

/** State passed via React Router navigate() to CostComparisonPage */
export interface WorkloadInferenceRouteState {
  vcpu: number
  ram_gb: number
  storage_gb: number
  justification: string
  autoDetected: true
}
