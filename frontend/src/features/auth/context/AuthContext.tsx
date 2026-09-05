/**
 * Infralytix — AuthContext & useAuth Hook.
 *
 * Keeps current user and JWT access token in memory.
 * Uses the HttpOnly refresh token cookie on mount to stay logged in after page refresh.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'
import { setAccessToken, setOnSessionExpired } from '@/lib/api-client'
import {
  getMeApi,
  loginApi,
  logoutApi,
  refreshTokenApi,
  registerApi,
} from '../api'
import {
  AuthContextType,
  LoginPayload,
  RegisterPayload,
  User,
} from '../types'

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const handleSessionExpired = useCallback(() => {
    setUser(null)
    setToken(null)
    setAccessToken(null)
  }, [])

  useEffect(() => {
    setOnSessionExpired(handleSessionExpired)
  }, [handleSessionExpired])

  const refreshSession = useCallback(async (): Promise<boolean> => {
    try {
      const tokenRes = await refreshTokenApi()
      setAccessToken(tokenRes.access_token)
      setToken(tokenRes.access_token)

      const userRes = await getMeApi()
      setUser(userRes)
      return true
    } catch {
      handleSessionExpired()
      return false
    } finally {
      setIsLoading(false)
    }
  }, [handleSessionExpired])

  // On initial load: attempt silent refresh via HttpOnly cookie
  useEffect(() => {
    refreshSession()
  }, [refreshSession])

  const login = async (payload: LoginPayload): Promise<void> => {
    setIsLoading(true)
    try {
      const tokenRes = await loginApi(payload)
      setAccessToken(tokenRes.access_token)
      setToken(tokenRes.access_token)

      const userRes = await getMeApi()
      setUser(userRes)
    } finally {
      setIsLoading(false)
    }
  }

  const register = async (payload: RegisterPayload): Promise<void> => {
    setIsLoading(true)
    try {
      await registerApi(payload)
      // Automatically log the user in following successful registration
      await login({ email: payload.email, password: payload.password })
    } finally {
      setIsLoading(false)
    }
  }

  const logout = async (): Promise<void> => {
    setIsLoading(true)
    try {
      await logoutApi()
    } finally {
      handleSessionExpired()
      setIsLoading(false)
    }
  }

  const value: AuthContextType = {
    user,
    accessToken,
    isAuthenticated: !!user && !!accessToken,
    isLoading,
    login,
    register,
    logout,
    refreshSession,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
