/**
 * Infralytix — 3D Scene Ambient Static Fallback.
 *
 * Lightweight, zero-WebGL fallback rendered during Suspense loading,
 * on devices without WebGL support, or when WebGL context creation fails.
 */

import React from 'react'

interface SceneFallbackProps {
  variant?: 'compare' | 'detect' | 'optimize'
}

export const SceneFallback: React.FC<SceneFallbackProps> = ({ variant = 'compare' }) => {
  const accentHues = {
    compare: {
      primary: '#882ECA',
      secondary: '#36136E',
      highlight: '#FF9900',
    },
    detect: {
      primary: '#882ECA',
      secondary: '#61D29A',
      highlight: '#A855F7',
    },
    optimize: {
      primary: '#882ECA',
      secondary: '#0078D4',
      highlight: '#61D29A',
    },
  }[variant]

  return (
    <div
      className="absolute inset-0 w-full h-full pointer-events-none overflow-hidden select-none -z-10"
      aria-hidden="true"
      style={{
        background: `radial-gradient(ellipse 80% 60% at 50% 25%, #242547 0%, #0c0a1a 70%, #06050d 100%)`,
      }}
    >
      {/* Ambient Radial Glows */}
      <div
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] h-[350px] rounded-full blur-[110px] opacity-35 transition-opacity duration-1000"
        style={{ background: accentHues.primary }}
      />
      <div
        className="absolute top-1/3 left-1/3 w-[400px] h-[300px] rounded-full blur-[130px] opacity-25"
        style={{ background: accentHues.secondary }}
      />
      <div
        className="absolute top-1/4 right-1/3 w-[350px] h-[250px] rounded-full blur-[120px] opacity-20"
        style={{ background: accentHues.highlight }}
      />

      {/* Abstract Faint Constellation Network */}
      <svg
        className="absolute inset-0 w-full h-full opacity-20"
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 1000 600"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <linearGradient id="fallbackGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#882ECA" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#36136E" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        {/* Node connections */}
        <line x1="500" y1="200" x2="350" y2="300" stroke="url(#fallbackGrad)" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="500" y1="200" x2="650" y2="280" stroke="url(#fallbackGrad)" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="350" y1="300" x2="650" y2="280" stroke="url(#fallbackGrad)" strokeWidth="1" strokeOpacity="0.4" />
        <line x1="500" y1="200" x2="520" y2="380" stroke="url(#fallbackGrad)" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="350" y1="300" x2="520" y2="380" stroke="url(#fallbackGrad)" strokeWidth="1" strokeOpacity="0.4" />
        <line x1="650" y1="280" x2="520" y2="380" stroke="url(#fallbackGrad)" strokeWidth="1" strokeOpacity="0.4" />

        {/* Abstract Node Rings */}
        <circle cx="500" cy="200" r="14" fill="#882ECA" fillOpacity="0.25" stroke="#882ECA" strokeWidth="1.5" />
        <circle cx="500" cy="200" r="5" fill="#fff" fillOpacity="0.8" />

        <circle cx="350" cy="300" r="10" fill="#FF9900" fillOpacity="0.25" stroke="#FF9900" strokeWidth="1.5" />
        <circle cx="350" cy="300" r="4" fill="#FF9900" fillOpacity="0.9" />

        <circle cx="650" cy="280" r="10" fill="#0078D4" fillOpacity="0.25" stroke="#0078D4" strokeWidth="1.5" />
        <circle cx="650" cy="280" r="4" fill="#0078D4" fillOpacity="0.9" />

        <circle cx="520" cy="380" r="10" fill="#4285F4" fillOpacity="0.25" stroke="#4285F4" strokeWidth="1.5" />
        <circle cx="520" cy="380" r="4" fill="#4285F4" fillOpacity="0.9" />
      </svg>
    </div>
  )
}
