/**
 * Cost feature TypeScript types — mirrors backend app/schemas/cost.py exactly.
 */

export type CloudProvider = 'aws' | 'gcp' | 'azure'
export type RegionPreference = 'us' | 'eu' | 'asia'

// ─── Request ─────────────────────────────────────────────────────────────────

export interface CostEstimateRequest {
  cpu_cores: number
  memory_gb: number
  storage_gb: number
  hours_per_month: number
  providers: CloudProvider[]
  region_preference: RegionPreference
  workload_label: string
}

// ─── Response Sub-types ───────────────────────────────────────────────────────

export interface InstanceOption {
  instance_type: string
  vcpus: number
  memory_gb: number
  price_per_hour_usd: number
}

export interface StorageEstimate {
  storage_type: string
  price_per_gb_month_usd: number
  total_cost_usd: number
}

export interface ProviderEstimate {
  provider: CloudProvider
  provider_display: string
  region: string
  instance: InstanceOption
  compute_monthly_usd: number
  storage: StorageEstimate
  total_monthly_usd: number
  notes: string[]
}

export interface CostComparisonResult {
  providers: ProviderEstimate[]
  cheapest_provider: CloudProvider
  ai_suggestion: string
}

export interface CostEstimateResponse {
  id: string
  result: CostComparisonResult
  created_at: string
  workload_label: string
}

export interface CostEstimateListItem {
  id: string
  cheapest_provider: string
  total_monthly_usd: number
  workload_label: string
  created_at: string
}

// ─── UI State ─────────────────────────────────────────────────────────────────

export interface CostEstimatorState {
  isLoading: boolean
  error: string | null
  result: CostEstimateResponse | null
}
