/**
 * Infralytix — Main Application Router.
 *
 * Implements the Sprint 5 routing hierarchy:
 *   - /login: User authentication
 *   - /register: User registration
 *   - /dashboard: Protected dashboard view within AppShell
 *   - / : Redirects to /dashboard
 *   - * : 404 fallback redirect to /dashboard
 */

import React from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'
import { AuthProvider, LoginPage, RegisterPage } from '@/features/auth'
import { AppShell, ProtectedRoute } from '@/components/layout'
import { DashboardPage } from '@/features/dashboard'

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public Authentication Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Application Routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>
          </Route>

          {/* Root & Fallback Redirection */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
