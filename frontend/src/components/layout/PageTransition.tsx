/**
 * Infralytix — PageTransition Component.
 *
 * Wraps each route's content in an AnimatePresence motion.div to produce a
 * crossfade + subtle vertical slide on every route change.
 *
 * Respects prefers-reduced-motion: when the user has requested reduced motion,
 * all durations are set to 0ms so the swap is instant with no visual flicker.
 */

import React from 'react'
import { motion, useReducedMotion } from 'framer-motion'

interface PageTransitionProps {
  children: React.ReactNode
  /** Unique key that changes on route change, triggering AnimatePresence */
  routeKey: string
}

export const PageTransition: React.FC<PageTransitionProps> = ({ children, routeKey }) => {
  const shouldReduce = useReducedMotion()

  const variants = {
    initial: { opacity: 0, y: shouldReduce ? 0 : 8 },
    enter:   { opacity: 1, y: 0,
                transition: { duration: shouldReduce ? 0 : 0.25, ease: 'easeOut' } },
    exit:    { opacity: 0, y: shouldReduce ? 0 : -4,
                transition: { duration: shouldReduce ? 0 : 0.15 } },
  }

  return (
    <motion.div
      key={routeKey}
      initial="initial"
      animate="enter"
      exit="exit"
      variants={variants}
      style={{ width: '100%' }}
    >
      {children}
    </motion.div>
  )
}
