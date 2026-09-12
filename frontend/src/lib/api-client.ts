/**
 * Infralytix — API Client (Axios).
 *
 * Configured simple Axios instance pointed at VITE_API_BASE_URL without auth handling.
 */

import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

// In-memory access token storage
let _inMemoryToken: string | null = null
let _sessionCallback: (() => void) | null = null

export const setAccessToken = (token: string | null): void => {
  _inMemoryToken = token
}

export const getAccessToken = (): string | null => _inMemoryToken

export const setOnSessionExpired = (callback: () => void): void => {
  _sessionCallback = callback
}

export const _noop = (): void => {
  if (_sessionCallback) {
    _sessionCallback()
  }
}

// Attach access token to outgoing requests if authenticated
apiClient.interceptors.request.use((config) => {
  if (_inMemoryToken) {
    config.headers.Authorization = `Bearer ${_inMemoryToken}`
  }
  return config
})

export default apiClient
