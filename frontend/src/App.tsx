/**
 * Infralytix — Multi-Cloud Cost Comparison App.
 *
 * Dedicated single-page interface for live multi-cloud cost evaluation.
 */

import React from 'react'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { CostComparisonPage } from '@/features/cost-comparison'

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<CostComparisonPage />} />
        <Route path="*" element={<CostComparisonPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
