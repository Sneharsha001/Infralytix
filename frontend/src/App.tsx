/**
 * Infralytix — Main Application Router.
 *
 * Resolves the routing architecture across:
 * - Public Cloud Comparison (/ and /cost-comparison)
 * - Multi-Cloud Workflow DAG Optimizer (/workflows)
 * - Authentication (/login and /register)
 * - Protected Enterprise AppShell (/dashboard, /projects, /cost)
 */

import React from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell, ProtectedRoute } from '@/components/layout'
import { AuthProvider, LoginPage, RegisterPage } from '@/features/auth'
import { CostEstimatorPage } from '@/features/cost'
import { CostComparisonPage } from '@/features/cost-comparison'
import { DashboardPage } from '@/features/dashboard'
import { ProjectDetailPage, ProjectsListPage } from '@/features/projects'
import { WorkflowOptimizerPage } from '@/features/workflows'

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Tools */}
          <Route path="/" element={<CostComparisonPage />} />
          <Route path="/cost-comparison" element={<CostComparisonPage />} />
          <Route path="/workflows" element={<WorkflowOptimizerPage />} />

          {/* Authentication */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          {/* Protected Application Workspace */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/projects" element={<ProjectsListPage />} />
              <Route path="/projects/:id" element={<ProjectDetailPage />} />
              <Route path="/cost" element={<CostEstimatorPage />} />
            </Route>
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
