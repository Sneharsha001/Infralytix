/**
 * Infralytix — DAG Preview Component (React Flow).
 *
 * Automatically positions task nodes in topological levels left-to-right,
 * with animated curved bezier edges representing dependency relationships.
 *
 * Visual upgrades vs v1:
 * - Darker dot-grid background (neutral-950 bg matches page)
 * - Framer Motion fade-in wrapper for smooth entrance
 * - fitView on mount with a small animation delay so the viewport settles
 * - Cleaner Controls panel styling
 */

import React, { useMemo, useCallback } from 'react'
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  MarkerType,
  Node,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { motion } from 'framer-motion'

import { WorkflowTaskInput } from '../types'
import { TaskNode } from './TaskNode'

const nodeTypes = { workflowTask: TaskNode }

interface DagPreviewProps {
  tasks: WorkflowTaskInput[]
}

// ─── Inner graph (needs ReactFlowProvider context for useReactFlow) ───────────

const DagGraph: React.FC<{ nodes: Node<WorkflowTaskInput>[]; edges: Edge[] }> = ({
  nodes,
  edges,
}) => {
  const { fitView } = useReactFlow()

  // Fit view 120ms after mount so React Flow has rendered the nodes
  const onInit = useCallback(() => {
    setTimeout(() => fitView({ padding: 0.22, duration: 500 }), 120)
  }, [fitView])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.22 }}
      minZoom={0.15}
      maxZoom={1.6}
      proOptions={{ hideAttribution: true }}
      onInit={onInit}
    >
      <Background
        color="rgba(180, 149, 164, 0.2)"
        gap={22}
        size={1.2}
        variant={BackgroundVariant.Dots}
        style={{ backgroundColor: 'var(--color-bg-base)' }}
      />
      <Controls
        className="!bg-[var(--color-bg-elevated)]/90 !border-white/10 !rounded-xl !shadow-xl [&>button]:!bg-transparent [&>button]:!border-white/10 [&>button]:!text-white hover:[&>button]:!bg-white/10 [&>button]:transition-colors"
      />
    </ReactFlow>
  )
}

// ─── Public component ─────────────────────────────────────────────────────────

export const DagPreview: React.FC<DagPreviewProps> = ({ tasks }) => {
  // Compute topological layers
  const { nodes, edges } = useMemo(() => {
    if (!tasks || tasks.length === 0) return { nodes: [], edges: [] }

    const taskMap = new Map<string, WorkflowTaskInput>()
    tasks.forEach((t) => taskMap.set(t.id, t))

    const depthMemo = new Map<string, number>()
    const getDepth = (id: string, visited = new Set<string>()): number => {
      if (depthMemo.has(id)) return depthMemo.get(id)!
      if (visited.has(id)) return 0
      visited.add(id)
      const task = taskMap.get(id)
      if (!task || task.depends_on.length === 0) {
        depthMemo.set(id, 0)
        return 0
      }
      let max = 0
      for (const parentId of task.depends_on) {
        max = Math.max(max, getDepth(parentId, new Set(visited)) + 1)
      }
      depthMemo.set(id, max)
      return max
    }

    tasks.forEach((t) => getDepth(t.id))

    const layers = new Map<number, WorkflowTaskInput[]>()
    tasks.forEach((t) => {
      const d = depthMemo.get(t.id) || 0
      if (!layers.has(d)) layers.set(d, [])
      layers.get(d)!.push(t)
    })

    const layoutNodes: Node<WorkflowTaskInput>[] = []
    const layoutEdges: Edge[] = []

    layers.forEach((layerTasks, layerIndex) => {
      layerTasks.forEach((task, taskIndex) => {
        layoutNodes.push({
          id: task.id,
          type: 'workflowTask',
          position: {
            x: layerIndex * 290 + 40,
            y: taskIndex * 155 + 40,
          },
          data: task,
        })
      })
    })

    tasks.forEach((task) => {
      task.depends_on.forEach((parent) => {
        layoutEdges.push({
          id: `e-${parent}-${task.id}`,
          source: parent,
          target: task.id,
          type: 'smoothstep',
          animated: true,
          style: { stroke: '#882ECA', strokeWidth: 1.8 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#882ECA',
            width: 14,
            height: 14,
          },
        })
      })
    })

    return { nodes: layoutNodes, edges: layoutEdges }
  }, [tasks])

  if (tasks.length === 0) {
    return (
      <div className="h-80 glass-card flex items-center justify-center text-neutral-400 text-sm rounded-2xl">
        No valid tasks to preview. Paste or upload workflow JSON above.
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.985 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
      className="w-full h-96 rounded-2xl overflow-hidden border border-[color-mix(in_srgb,var(--color-bg-elevated)_65%,rgba(255,255,255,0.12))] relative"
      style={{ background: 'var(--color-bg-base)' }}
    >
      {/* Overlay label */}
      <div className="absolute top-3 left-4 z-10 flex items-center gap-2 pointer-events-none">
        <span className="badge-neutral text-xs">
          Interactive DAG ({tasks.length} {tasks.length === 1 ? 'task' : 'tasks'})
        </span>
        <span className="text-[11px] text-neutral-500">Scroll to zoom · Drag to pan</span>
      </div>

      <ReactFlowProvider>
        <DagGraph nodes={nodes} edges={edges} />
      </ReactFlowProvider>
    </motion.div>
  )
}
