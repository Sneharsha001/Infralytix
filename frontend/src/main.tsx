/**
 * Infralytix — React Entry Point
 *
 * Bootstraps the React application.
 * StrictMode is enabled in development only (enforced by Vite).
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

const root = document.getElementById('root')

if (!root) {
  throw new Error(
    '[Infralytix] Failed to find root element. ' +
    'Ensure index.html contains <div id="root"></div>.'
  )
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
