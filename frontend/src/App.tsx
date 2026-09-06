/**
 * Infralytix — Main Application Router.
 *
 * Implements the routing hierarchy:
 *   - /login: User authentication
 *   - /register: User registration
 *   - /dashboard: Protected dashboard view within AppShell
 *   - /projects: Project list
 *   - /projects/:id: Project detail
 *   - /cost: Multi-cloud cost estimator
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
import { ProjectDetailPage, ProjectsListPage } from '@/features/projects'
import { CostEstimatorPage } from '@/features/cost'

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
              <Route path="/projects" element={<ProjectsListPage />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route path="/cost" element={<CostEstimatorPage />} />
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
