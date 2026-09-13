/**
 * Infralytix - PageTransition Component.
 *
 * Wraps each route content in a motion.div to produce a crossfade + subtle
 * vertical slide on every route change.
 * Reduced-motion: all durations = 0ms for instant, non-animated swap.
 */

import React from 'react'
import { motion, useReducedMotion } from 'framer-motion'

interface PageTransitionProps {
  children: React.ReactNode
  routeKey: string
}

export const PageTransition: React.FC<PageTransitionProps> = ({ children, routeKey }) => {
  const shouldReduce = useReducedMotion()
  const dur = shouldReduce ? 0 : 0.25
  const shift = shouldReduce ? 0 : 8
  const exitShift = shouldReduce ? 0 : -4

  return (
    <motion.div
      key={routeKey}
      initial={{ opacity: 0, y: shift }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: exitShift }}
      transition={{ duration: dur, ease: [0.25, 0.1, 0.25, 1] }}
      style={{ width: '100%' }}
    >
      {children}
    </motion.div>
  )
}