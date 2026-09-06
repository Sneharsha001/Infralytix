/**
 * Infralytix — API Client (Axios).
 *
 * Configured simple Axios instance pointed at VITE_API_BASE_URL without auth handling.
 */

import axios from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export const apiClient = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Backward compatibility storage stubs (no auth handling active)
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

export default apiClient
