/**
 * Infralytix — Authentication API Functions.
 */

import { apiClient } from '@/lib/api-client'
import { LoginPayload, RegisterPayload, TokenResponse, User } from './types'

export const loginApi = async (payload: LoginPayload): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/auth/login', payload)
  return response.data
}

export const registerApi = async (payload: RegisterPayload): Promise<User> => {
  const response = await apiClient.post<User>('/auth/register', payload)
  return response.data
}

export const refreshTokenApi = async (): Promise<TokenResponse> => {
  const response = await apiClient.post<TokenResponse>('/auth/refresh', {})
  return response.data
}

export const logoutApi = async (): Promise<void> => {
  await apiClient.post('/auth/logout', {})
}

export const getMeApi = async (): Promise<User> => {
  const response = await apiClient.get<User>('/auth/me')
  return response.data
}
