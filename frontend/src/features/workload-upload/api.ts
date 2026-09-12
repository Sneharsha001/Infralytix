/**
 * Infralytix — Workload Upload API Client.
 *
 * Calls POST /api/v1/projects/{id}/infer-workload with a zip archive
 * and returns the inferred compute resource profile.
 */

import { apiClient } from '@/lib/api-client'
import { WorkloadInferenceResult } from './types'

export const workloadUploadApi = {
  /**
   * Upload a repository zip and infer workload compute requirements.
   * Uses Gemini inference server-side; falls back to heuristics automatically.
   */
  async inferWorkload(projectId: string, file: File): Promise<WorkloadInferenceResult> {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await apiClient.post<WorkloadInferenceResult>(
      `/projects/${projectId}/infer-workload`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 60_000, // 60 s — analysis can take time on large archives
      },
    )
    return data
  },
}
