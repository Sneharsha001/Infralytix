/**
 * Infralytix — Project & Repository Intelligence Types.
 */

export interface LanguageStat {
  language: string
  extension: string
  file_count: number
  loc: number
  percentage: number
}

export interface DependencyFile {
  filename: string
  package_manager: string
  dependencies: string[]
}

export interface RepositoryAnalysisResult {
  total_files: number
  total_loc: number
  primary_language: string | null
  languages: LanguageStat[]
  dependency_files: DependencyFile[]
  detected_frameworks: string[]
}

// ── AI Insight Types (Phase 2) ─────────────────────────────────────────────

export interface CodeHealthScore {
  overall: number           // 0–100
  maintainability: number
  complexity: number
  test_coverage_estimate: number
  documentation: number
}

export interface ArchitectureInsight {
  category: 'pattern' | 'concern' | 'recommendation'
  title: string
  description: string
  severity: 'info' | 'warning' | 'critical'
}

export interface AIInsightResult {
  summary: string
  health_score: CodeHealthScore
  insights: ArchitectureInsight[]
  tech_debt_indicators: string[]
  recommended_next_steps: string[]
}

// ── Agent Run ───────────────────────────────────────────────────────────────

export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface AgentRun {
  id: string
  project_id: string
  agent_type: string
  status: AgentRunStatus
  output_data?: RepositoryAnalysisResult | AIInsightResult | null
  error_message?: string | null
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  user_id: string
  name: string
  description?: string | null
  repo_name?: string | null
  archive_filename?: string | null
  created_at: string
  updated_at: string
  latest_run?: AgentRun | null
}

export interface CreateProjectPayload {
  name: string
  description?: string
  repo_name?: string
}

export interface UpdateProjectPayload {
  name?: string
  description?: string
  repo_name?: string
}
