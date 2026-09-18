import type { Config } from 'tailwindcss'

const config: Config = {
  // ── Purge/Content ──────────────────────────────────────────────────────────
  // Tailwind scans these files to remove unused CSS classes in production
  content: [
    './index.html',
    './src/**/*.{ts,tsx}',
  ],

  // ── Dark Mode ──────────────────────────────────────────────────────────────
  // 'class' strategy: dark mode is toggled by adding 'dark' class to <html>
  darkMode: 'class',

  theme: {
    extend: {
      // ── Brand Colors ────────────────────────────────────────────────────────
      colors: {
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',  // Primary brand color
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
          // New palette tokens
          base: 'var(--color-bg-base)',
          elevated: 'var(--color-bg-elevated)',
          accent: 'var(--color-accent-primary)',
          muted: 'var(--color-text-muted)',
          mutedLight: 'var(--color-text-muted-accessible, #C7ADB9)',
          success: 'var(--color-success)',
        },
        palette: {
          base: 'var(--color-bg-base)',
          elevated: 'var(--color-bg-elevated)',
          accent: 'var(--color-accent-primary)',
          muted: 'var(--color-text-muted)',
          mutedLight: 'var(--color-text-muted-accessible, #C7ADB9)',
          success: 'var(--color-success)',
        },
        // Neutral palette for backgrounds and text
        neutral: {
          850: '#1a1a2e',   // Deep dark background
          900: '#0f0f23',   // Darkest background
          950: '#070714',   // OLED black
        },
        // Semantic colors
        success: 'var(--color-success)',
        warning: '#f59e0b',
        danger:  '#ef4444',
        info:    '#3b82f6',
      },

      // ── Typography ──────────────────────────────────────────────────────────
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },

      // ── Spacing ─────────────────────────────────────────────────────────────
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      // ── Animations ──────────────────────────────────────────────────────────
      animation: {
        'fade-in':     'fadeIn 0.3s ease-out',
        'fade-up':     'fadeUp 0.4s ease-out',
        'slide-in':    'slideIn 0.3s ease-out',
        'pulse-slow':  'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow':   'spin 3s linear infinite',
        'bounce-soft': 'bounceSoft 2s infinite',
      },
      keyframes: {
        fadeIn: {
          '0%':   { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeUp: {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideIn: {
          '0%':   { opacity: '0', transform: 'translateX(-16px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        bounceSoft: {
          '0%, 100%': { transform: 'translateY(-4px)' },
          '50%':      { transform: 'translateY(0)' },
        },
      },

      // ── Opacity (Custom for glass effects) ──────────────────────────────────
      opacity: {
        '8': '0.08',
        '12': '0.12',
        '15': '0.15',
      },

      // ── Border Radius ────────────────────────────────────────────────────────
      borderRadius: {
        '4xl': '2rem',
      },

      // ── Box Shadow / Elevation System ────────────────────────────────────────
      // 4 named levels used identically everywhere — resting card, hover, focused, modal
      boxShadow: {
        // Elevation levels
        'elev-1': '0 2px 8px -2px rgba(0,0,0,0.40), 0 1px 3px -1px rgba(0,0,0,0.25)',
        'elev-2': '0 8px 24px -4px rgba(0,0,0,0.50), 0 4px 8px -2px rgba(0,0,0,0.30)',
        'elev-3': '0 16px 48px -8px rgba(0,0,0,0.60), 0 8px 16px -4px rgba(0,0,0,0.35)',
        'elev-4': '0 32px 80px -12px rgba(0,0,0,0.70), 0 16px 32px -8px rgba(0,0,0,0.40)',
        // Brand glow variants
        'brand':    '0 0 20px rgba(59, 130, 246, 0.30)',
        'brand-lg': '0 0 40px rgba(59, 130, 246, 0.45), 0 0 80px rgba(59, 130, 246, 0.15)',
        'glow':     '0 0 40px rgba(59, 130, 246, 0.15)',
        'inner-dark': 'inset 0 2px 4px rgba(0, 0, 0, 0.4)',
      },

      // ── Backdrop Blur ────────────────────────────────────────────────────────
      backdropBlur: {
        xs: '2px',
      },
    },
  },

  plugins: [],
}

export default config
