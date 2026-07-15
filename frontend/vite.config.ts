import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  // ── Path Aliases ──────────────────────────────────────────────────────────
  // Enables: import { Button } from '@/components/ui/Button'
  // instead of: import { Button } from '../../components/ui/Button'
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@api': path.resolve(__dirname, './src/api'),
      '@components': path.resolve(__dirname, './src/components'),
      '@features': path.resolve(__dirname, './src/features'),
      '@hooks': path.resolve(__dirname, './src/hooks'),
      '@types': path.resolve(__dirname, './src/types'),
      '@utils': path.resolve(__dirname, './src/utils'),
    },
  },

  // ── Development Server ────────────────────────────────────────────────────
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    // Proxy API calls to the backend in development
    // This avoids CORS issues during local development
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },

  // ── Build ─────────────────────────────────────────────────────────────────
  build: {
    outDir: 'dist',
    sourcemap: false,        // Disable source maps in production (security)
    minify: 'esbuild',
    target: 'es2020',
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        // Split vendor chunks for better caching
        manualChunks: {
          'react-vendor': ['react', 'react-dom'],
          'router-vendor': ['react-router-dom'],
          'http-vendor': ['axios'],
        },
      },
    },
  },

  // ── Preview (production preview server) ───────────────────────────────────
  preview: {
    host: '0.0.0.0',
    port: 4173,
  },

  // ── Environment Variables ─────────────────────────────────────────────────
  // All VITE_ prefixed vars from .env are available in the app as import.meta.env.VITE_*
  envPrefix: 'VITE_',
})
