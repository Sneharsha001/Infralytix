/**
 * Infralytix — Custom Task Node for React Flow DAG Preview.
 *
 * Implements a glassmorphic card representing an individual workflow task,
 * with category badges, resource requirements, and connection handles.
 */

import React, { memo } from 'react'
import { Handle, NodeProps, Position } from 'reactflow'
import { TaskCategory, WorkflowTaskInput } from '../types'

const CATEGORY_STYLES: Record<
  TaskCategory,
  { label: string; badge: string; border: string }
> = {
  cpu_bound: {
    label: 'CPU Bound',
    badge: 'bg-sky-500/15 text-sky-300 ring-sky-500/30',
    border: 'border-sky-500/30',
  },
  io_bound: {
    label: 'I/O Bound',
    badge: 'bg-amber-500/15 text-amber-300 ring-amber-500/30',
    border: 'border-amber-500/30',
  },
  memory_bound: {
    label: 'Memory Bound',
    badge: 'bg-emerald-500/15 text-emerald-300 ring-emerald-500/30',
    border: 'border-emerald-500/30',
  },
  gpu_bound: {
    label: 'GPU Bound',
    badge: 'bg-purple-500/15 text-purple-300 ring-purple-500/30',
    border: 'border-purple-500/40',
  },
}

export const TaskNode: React.FC<NodeProps<WorkflowTaskInput>> = memo(({ data }) => {
  const meta = CATEGORY_STYLES[data.category] || CATEGORY_STYLES.cpu_bound

  return (
    <div
      className={`glass-card p-3.5 min-w-[210px] max-w-[240px] shadow-lg transition-all duration-200 hover:border-white/30 ${meta.border} bg-neutral-900/90`}
    >
      {/* Target handle (incoming dependency edges) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-2.5 !h-2.5 !bg-brand-400 !border-2 !border-neutral-900 !-left-1.5"
      />

      <div className="flex items-start justify-between gap-1.5 mb-2">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ring-1 ${meta.badge}`}
        >
          {meta.label}
        </span>
        <span className="text-[10px] font-mono text-neutral-400">
          {data.baseline_time_seconds}s
        </span>
      </div>

      <div className="font-semibold text-sm text-white truncate mb-1" title={data.name}>
        {data.name}
      </div>
      <div className="text-[11px] font-mono text-neutral-400 truncate mb-2.5">
        id: {data.id}
      </div>

      <div className="flex items-center justify-between text-[11px] text-neutral-300 pt-2 border-t border-white/10 font-mono">
        <span>{data.baseline_vcpu} vCPU</span>
        <span>{data.baseline_ram_gb} GB RAM</span>
      </div>

      {/* Source handle (outgoing edges to dependent tasks) */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-2.5 !h-2.5 !bg-brand-400 !border-2 !border-neutral-900 !-right-1.5"
      />
    </div>
  )
})

TaskNode.displayName = 'TaskNode'
