/**
 * Cost feature API client — wraps the three backend cost endpoints.
 * Uses the shared axios instance from lib/api-client.ts.
 */

import { apiClient } from '@/lib/api-client'
import type {
  CostEstimateListItem,
  CostEstimateRequest,
  CostEstimateResponse,
} from './types'

export const costApi = {
  /** POST /cost/estimate — run a new comparison */
  estimate: async (body: CostEstimateRequest): Promise<CostEstimateResponse> => {
    const { data } = await apiClient.post<CostEstimateResponse>(
      '/cost/estimate',
      body
    )
    return data
  },

  /** GET /cost/estimates — list current user's saved estimates */
  list: async (): Promise<CostEstimateListItem[]> => {
    const { data } = await apiClient.get<CostEstimateListItem[]>('/cost/estimates')
    return data
  },

  /** GET /cost/estimates/{id} — retrieve one by ID */
  get: async (id: string): Promise<CostEstimateResponse> => {
    const { data } = await apiClient.get<CostEstimateResponse>(
      `/cost/estimates/${id}`
    )
    return data
  },
}
