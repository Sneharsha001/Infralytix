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
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { AppShell, ProtectedRoute, PageTransition } from '@/components/layout'
import { AuthProvider, LoginPage, RegisterPage } from '@/features/auth'
import { CostEstimatorPage } from '@/features/cost'
import { CostComparisonPage } from '@/features/cost-comparison'
import { DashboardPage } from '@/features/dashboard'
import { ProjectDetailPage, ProjectsListPage } from '@/features/projects'
import { WorkloadUploadPage } from '@/features/workload-upload/WorkloadUploadPage'
import { WorkflowOptimizerPage } from '@/features/workflows'

const AnimatedRoutes: React.FC = () => {
  const location = useLocation()

  return (
    <AnimatePresence mode="wait" initial={false}>
      <Routes location={location} key={location.pathname}>
        {/* Public Tools */}
        <Route path="/" element={<PageTransition routeKey={location.pathname}><CostComparisonPage /></PageTransition>} />
        <Route path="/cost-comparison" element={<PageTransition routeKey={location.pathname}><CostComparisonPage /></PageTransition>} />
        <Route path="/workflows" element={<PageTransition routeKey={location.pathname}><WorkflowOptimizerPage /></PageTransition>} />
        <Route path="/upload-workload" element={<PageTransition routeKey={location.pathname}><WorkloadUploadPage /></PageTransition>} />

        {/* Authentication */}
        <Route path="/login" element={<PageTransition routeKey={location.pathname}><LoginPage /></PageTransition>} />
        <Route path="/register" element={<PageTransition routeKey={location.pathname}><RegisterPage /></PageTransition>} />

        {/* Protected Application Workspace */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<PageTransition routeKey={location.pathname}><DashboardPage /></PageTransition>} />
            <Route path="/projects" element={<PageTransition routeKey={location.pathname}><ProjectsListPage /></PageTransition>} />
            <Route path="/projects/:id" element={<PageTransition routeKey={location.pathname}><ProjectDetailPage /></PageTransition>} />
            <Route path="/cost" element={<PageTransition routeKey={location.pathname}><CostEstimatorPage /></PageTransition>} />
          </Route>
        </Route>

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AnimatePresence>
  )
}

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AnimatedRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
