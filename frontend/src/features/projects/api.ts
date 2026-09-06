/**
 * Infralytix — Projects API Client Service.
 */

import { apiClient } from '../../lib/api-client'
import {
  AgentRun,
  CreateProjectPayload,
  Project,
  UpdateProjectPayload,
} from './types'

export const projectsApi = {
  /** List all projects owned by authenticated user */
  async list(): Promise<Project[]> {
    const { data } = await apiClient.get<Project[]>('/projects')
    return data
  },

  /** Get single project by ID (includes latest_run) */
  async getById(id: string): Promise<Project> {
    const { data } = await apiClient.get<Project>(`/projects/${id}`)
    return data
  },

  /** Create new project */
  async create(payload: CreateProjectPayload): Promise<Project> {
    const { data } = await apiClient.post<Project>('/projects', payload)
    return data
  },

  /** Update project */
  async update(id: string, payload: UpdateProjectPayload): Promise<Project> {
    const { data } = await apiClient.patch<Project>(`/projects/${id}`, payload)
    return data
  },

  /** Delete project and clean up files */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/projects/${id}`)
  },

  /** Upload repository zip archive and trigger static analysis */
  async uploadArchive(id: string, file: File): Promise<AgentRun> {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await apiClient.post<AgentRun>(`/projects/${id}/upload`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  /** Get execution runs history for project */
  async getRuns(id: string): Promise<AgentRun[]> {
    const { data } = await apiClient.get<AgentRun[]>(`/projects/${id}/agent-runs`)
    return data
  },

  /** Trigger Gemini AI analysis on the latest repository upload */
  async triggerAnalysis(id: string): Promise<AgentRun> {
    const { data } = await apiClient.post<AgentRun>(`/projects/${id}/analyze`)
    return data
  },

  /** Fetch the latest AI insight result for a project */
  async getAnalysis(id: string): Promise<AgentRun> {
    const { data } = await apiClient.get<AgentRun>(`/projects/${id}/analysis`)
    return data
  },
}

