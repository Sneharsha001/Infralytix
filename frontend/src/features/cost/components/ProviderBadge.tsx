/**
 * ProviderBadge — Cloud provider logo + name badge.
 * Uses SVG brand marks inline to avoid any external dependency.
 */

import React from 'react'
import type { CloudProvider } from '../types'

interface Props {
  provider: CloudProvider
  size?: 'sm' | 'md'
}

const AWS_LOGO = (
  <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
    <path d="M13.8 28.5c-.5.2-1 .3-1.6.3-1.6 0-2.5-.9-2.5-2.6V20H8v-1.5h1.7V16l2-.5v2h2.3V19h-2.3v5.9c0 .9.4 1.3 1.1 1.3.3 0 .6-.1.9-.2l.1 1.5z" fill="#FF9900"/>
    <path d="M19.6 28.6c-2.4 0-4-1.7-4-4.4s1.6-4.4 4-4.4 4 1.7 4 4.4-1.7 4.4-4 4.4zm0-7.3c-1.2 0-2 1.1-2 2.9s.8 2.9 2 2.9 2-1.1 2-2.9-.8-2.9-2-2.9z" fill="#FF9900"/>
    <path d="M33 28.4h-2l-1.2-4.5c-.2-.7-.4-1.6-.5-2.2h-.1c-.1.6-.3 1.5-.5 2.2l-1.2 4.5h-2l-2.5-8.8h2.1l1.1 4.5c.2.8.4 1.6.5 2.3h.1c.1-.7.3-1.5.5-2.3l1.2-4.5h1.9l1.2 4.5c.2.8.4 1.6.5 2.3h.1c.1-.7.3-1.5.5-2.3l1.1-4.5h2L33 28.4z" fill="#FF9900"/>
    <path d="M24 36.2C13.8 36.2 5.5 28.8 5.5 19.6S13.8 3 24 3s18.5 7.4 18.5 16.6c0 2.7-.7 5.2-1.9 7.5-.2.4-.7.5-1.1.3-.4-.2-.5-.7-.3-1.1 1.1-2 1.8-4.3 1.8-6.7C40.9 13.3 33.2 5.6 24 5.6S7.1 13.3 7.1 22.6c0 8.5 6.5 15.6 14.9 16.3-.4-1.4-.3-2.9.4-4.3.2-.4.7-.5 1.1-.3.4.2.5.7.3 1.1-.7 1.4-.6 3 .2 4.3.1.2.1.4 0 .6-.1.2-.3.4-.5.4-.5 0-1-.1-1.5-.1v-.4z" fill="#FF9900"/>
  </svg>
)

const GCP_LOGO = (
  <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
    <path d="M30.2 14H24v-2h8v8h-2v-4.6l-9.3 9.3-1.4-1.4 10.9-10.9z" fill="#4285F4"/>
    <path d="M24 10C16.3 10 10 16.3 10 24s6.3 14 14 14 14-6.3 14-14h-2c0 6.6-5.4 12-12 12S12 30.6 12 24 17.4 12 24 12v-2z" fill="#34A853"/>
    <path d="M38 24h-2c0-3.3-1.3-6.2-3.5-8.5l1.4-1.4C36.5 16.7 38 20.2 38 24z" fill="#FBBC05"/>
    <path d="M29.5 13.5C27.2 11.3 24.3 10 21 10v2c2.8 0 5.3 1.1 7.1 2.9l1.4-1.4z" fill="#EA4335"/>
  </svg>
)

const AZURE_LOGO = (
  <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full">
    <path d="M27.1 8L17 27.7l6.7 10.9H38L27.1 8z" fill="#0089D6"/>
    <path d="M10 38.6l7.9-14.1 5.1 8.8-5.5 5.3H10z" fill="#0089D6" opacity=".7"/>
    <path d="M17 8l-7 13.1 9.9 17.5h8.2L17 8z" fill="#0072C6"/>
  </svg>
)

const LOGOS: Record<CloudProvider, React.ReactNode> = {
  aws: AWS_LOGO,
  gcp: GCP_LOGO,
  azure: AZURE_LOGO,
}

const NAMES: Record<CloudProvider, string> = {
  aws: 'AWS',
  gcp: 'GCP',
  azure: 'Azure',
}

const COLORS: Record<CloudProvider, string> = {
  aws: 'bg-amber-500/10 border-amber-500/20 text-amber-400',
  gcp: 'bg-blue-500/10 border-blue-500/20 text-blue-400',
  azure: 'bg-sky-500/10 border-sky-500/20 text-sky-400',
}

const ICON_SIZES = { sm: 'w-4 h-4', md: 'w-6 h-6' }
const TEXT_SIZES = { sm: 'text-xs', md: 'text-sm' }

export const ProviderBadge: React.FC<Props> = ({ provider, size = 'md' }) => (
  <span
    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-semibold ${COLORS[provider]} ${TEXT_SIZES[size]}`}
  >
    <span className={ICON_SIZES[size]}>{LOGOS[provider]}</span>
    {NAMES[provider]}
  </span>
)
