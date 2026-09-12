/**
 * Infralytix — Custom Task Node for React Flow DAG Preview.
 *
 * Glassmorphic card with:
 * - Category color-coded border + badge
 * - Smooth hover shadow lift matching the dark theme
 * - Brand-colored connection handles
 * - Subtle entry transition via CSS (React Flow doesn't support Framer Motion directly)
 */

import React, { memo } from 'react'
import { Handle, NodeProps, Position } from 'reactflow'
import { TaskCategory, WorkflowTaskInput } from '../types'

const CATEGORY_STYLES: Record<
  TaskCategory,
  { label: string; badge: string; border: string; handleColor: string; glow: string }
> = {
  cpu_bound: {
    label: 'CPU Bound',
    badge: 'bg-sky-500/15 text-sky-300 ring-1 ring-sky-500/30',
    border: 'border-sky-500/35',
    handleColor: '#38bdf8',
    glow: '0 0 16px -2px rgba(56,189,248,0.18)',
  },
  io_bound: {
    label: 'I/O Bound',
    badge: 'bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30',
    border: 'border-amber-500/35',
    handleColor: '#fbbf24',
    glow: '0 0 16px -2px rgba(251,191,36,0.18)',
  },
  memory_bound: {
    label: 'Memory Bound',
    badge: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30',
    border: 'border-emerald-500/35',
    handleColor: '#34d399',
    glow: '0 0 16px -2px rgba(52,211,153,0.18)',
  },
  gpu_bound: {
    label: 'GPU Bound',
    badge: 'bg-purple-500/15 text-purple-300 ring-1 ring-purple-500/35',
    border: 'border-purple-500/40',
    handleColor: '#c084fc',
    glow: '0 0 16px -2px rgba(192,132,252,0.22)',
  },
}

export const TaskNode: React.FC<NodeProps<WorkflowTaskInput>> = memo(({ data }) => {
  const meta = CATEGORY_STYLES[data.category] || CATEGORY_STYLES.cpu_bound

  return (
    <div
      className={[
        'relative min-w-[210px] max-w-[240px] rounded-xl border backdrop-blur-sm',
        'bg-neutral-900/90 shadow-lg',
        'transition-all duration-200',
        'hover:border-white/25 hover:bg-neutral-800/90',
        meta.border,
      ].join(' ')}
      style={{
        boxShadow: `0 4px 20px -4px rgba(0,0,0,0.5), ${meta.glow}`,
      }}
      onMouseEnter={(e) => {
        ;(e.currentTarget as HTMLDivElement).style.boxShadow =
          `0 8px 28px -4px rgba(0,0,0,0.6), ${meta.glow}`
      }}
      onMouseLeave={(e) => {
        ;(e.currentTarget as HTMLDivElement).style.boxShadow =
          `0 4px 20px -4px rgba(0,0,0,0.5), ${meta.glow}`
      }}
    >
      {/* Target handle */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          width: 10,
          height: 10,
          background: meta.handleColor,
          border: '2px solid #0f172a',
          left: -5,
        }}
      />

      <div className="p-3.5 space-y-2">
        {/* Category badge + time */}
        <div className="flex items-start justify-between gap-1.5">
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${meta.badge}`}>
            {meta.label}
          </span>
          <span className="text-[10px] font-mono text-neutral-500 shrink-0">
            {data.baseline_time_seconds}s
          </span>
        </div>

        {/* Task name */}
        <div className="font-semibold text-sm text-white truncate leading-tight" title={data.name}>
          {data.name}
        </div>

        {/* Task ID */}
        <div className="text-[10px] font-mono text-neutral-500 truncate">
          {data.id}
        </div>

        {/* Resource footer */}
        <div className="flex items-center justify-between text-[11px] pt-2 border-t border-white/[0.07] font-mono">
          <span className="text-neutral-400">{data.baseline_vcpu} vCPU</span>
          <span className="text-neutral-400">{data.baseline_ram_gb} GB</span>
        </div>
      </div>

      {/* Source handle */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          width: 10,
          height: 10,
          background: meta.handleColor,
          border: '2px solid #0f172a',
          right: -5,
        }}
      />
    </div>
  )
})

TaskNode.displayName = 'TaskNode'
