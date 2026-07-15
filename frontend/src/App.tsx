/**
 * Infralytix — Root Application Component
 *
 * Sprint 0: Minimal placeholder with a branded launch screen.
 * Sprint 5: This will be replaced with React Router, layout shell,
 *           and feature-based routing.
 *
 * The launch screen serves as visual proof that the frontend
 * builds and serves correctly from the container.
 */

import type { FC } from 'react'

// ─── Inline SVG Icon (no icon library dependency yet) ────────────────────────
const InfraIcon: FC = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    fill="none"
    className="w-10 h-10"
    aria-hidden="true"
  >
    <path
      d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
      stroke="url(#grad)"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <defs>
      <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#60a5fa" />
        <stop offset="100%" stopColor="#a78bfa" />
      </linearGradient>
    </defs>
  </svg>
)

// ─── Agent Feature Cards ──────────────────────────────────────────────────────
interface AgentCardProps {
  icon: string
  title: string
  description: string
  status: 'coming-soon' | 'planned'
}

const AgentCard: FC<AgentCardProps> = ({ icon, title, description, status }) => (
  <div className="glass-card p-5 flex flex-col gap-3 group hover:border-brand-500/40 transition-all duration-300">
    <div className="flex items-start justify-between">
      <span className="text-2xl">{icon}</span>
      <span className="badge-neutral text-xs capitalize">{status.replace('-', ' ')}</span>
    </div>
    <div>
      <h3 className="text-sm font-semibold text-white">{title}</h3>
      <p className="text-xs text-neutral-400 mt-1 leading-relaxed">{description}</p>
    </div>
  </div>
)

// ─── Root App ────────────────────────────────────────────────────────────────
const App: FC = () => {
  const agents: AgentCardProps[] = [
    { icon: '🔍', title: 'Repo Analyzer', description: 'Detect languages, frameworks, and tech debt', status: 'coming-soon' },
    { icon: '🐳', title: 'Docker Generator', description: 'Generate production-ready Dockerfiles', status: 'coming-soon' },
    { icon: '⚙️', title: 'CI Generator', description: 'GitHub Actions workflows for your stack', status: 'coming-soon' },
    { icon: '🔒', title: 'Security Analyzer', description: 'Scan for vulnerabilities and secrets', status: 'planned' },
    { icon: '💰', title: 'Cost Estimator', description: 'Estimate AWS infrastructure costs', status: 'planned' },
    { icon: '🏗️', title: 'Architecture Generator', description: 'Generate architecture diagrams from code', status: 'planned' },
  ]

  return (
    <div className="min-h-screen bg-neutral-900 text-white flex flex-col">
      {/* Ambient background gradient */}
      <div
        className="fixed inset-0 pointer-events-none"
        aria-hidden="true"
        style={{
          background:
            'radial-gradient(ellipse 80% 50% at 50% -10%, rgba(59,130,246,0.08) 0%, transparent 70%)',
        }}
      />

      {/* ── Header ── */}
      <header className="relative z-10 flex items-center justify-between px-8 py-5 border-b border-white/8">
        <div className="flex items-center gap-3">
          <InfraIcon />
          <div>
            <span className="text-lg font-bold tracking-tight gradient-text">Infralytix</span>
            <span className="ml-2 badge-neutral text-xs">v0.1.0 · Sprint 0</span>
          </div>
        </div>
        <nav className="flex items-center gap-2" aria-label="Primary navigation">
          <a
            href="https://github.com/Sneharsha001/Infralytix"
            target="_blank"
            rel="noopener noreferrer"
            className="btn-ghost text-xs"
          >
            GitHub ↗
          </a>
          <button className="btn-primary text-xs" disabled>
            Sign In (Sprint 3)
          </button>
        </nav>
      </header>

      {/* ── Hero ── */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 py-20 text-center">
        <div className="animate-fade-up">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/25 text-brand-400 text-xs font-medium mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
            Foundation Sprint Complete — Backend Operational
          </div>

          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight mb-6 leading-tight">
            AI-Powered Developer
            <br />
            <span className="gradient-text">Infrastructure OS</span>
          </h1>

          <p className="text-lg text-neutral-400 max-w-2xl mx-auto mb-10 leading-relaxed">
            Infralytix is a multi-agent platform that analyzes your repositories,
            generates DevOps artifacts, audits security, and estimates cloud costs —
            all through specialized AI agents.
          </p>

          <div className="flex flex-wrap items-center justify-center gap-3">
            <button className="btn-primary" disabled>
              Get Started (Sprint 3)
            </button>
            <a
              href="http://localhost:8000/api/v1/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary"
            >
              API Docs ↗
            </a>
          </div>
        </div>

        {/* ── Stats Bar ── */}
        <div className="mt-16 w-full max-w-3xl grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Sprints Completed', value: '1/13' },
            { label: 'API Endpoints', value: '2' },
            { label: 'AI Agents', value: '6 planned' },
            { label: 'Stack', value: 'FastAPI + React' },
          ].map((stat) => (
            <div key={stat.label} className="glass-card p-4 text-center">
              <div className="text-xl font-bold text-brand-400">{stat.value}</div>
              <div className="text-xs text-neutral-500 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>

        {/* ── Agent Grid ── */}
        <section className="mt-16 w-full max-w-4xl" aria-labelledby="agents-heading">
          <h2 id="agents-heading" className="text-xl font-semibold mb-6 text-neutral-300">
            AI Agent Roadmap
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => (
              <AgentCard key={agent.title} {...agent} />
            ))}
          </div>
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-white/8 px-8 py-5 flex items-center justify-between text-xs text-neutral-500">
        <span>© 2025 Infralytix · Built for portfolio by Sneha Harsha</span>
        <span className="font-mono">Python 3.12 · FastAPI · React 19 · MySQL 8.4</span>
      </footer>
    </div>
  )
}

export default App
