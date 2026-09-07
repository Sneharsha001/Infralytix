/**
 * Infralytix — DAG Preview Component (React Flow).
 *
 * Automatically positions task nodes in topological levels from left to right,
 * with animated curved bezier edges representing dependency relationships.
 */

import React, { useMemo } from 'react'
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  MarkerType,
  Node,
} from 'reactflow'
import 'reactflow/dist/style.css'

import { WorkflowTaskInput } from '../types'
import { TaskNode } from './TaskNode'

const nodeTypes = {
  workflowTask: TaskNode,
}

interface DagPreviewProps {
  tasks: WorkflowTaskInput[]
}

export const DagPreview: React.FC<DagPreviewProps> = ({ tasks }) => {
  // Compute topological layers for clean left-to-right hierarchy
  const { nodes, edges } = useMemo(() => {
    if (!tasks || tasks.length === 0) {
      return { nodes: [], edges: [] }
    }

    const taskMap = new Map<string, WorkflowTaskInput>()
    tasks.forEach((t) => taskMap.set(t.id, t))

    // Compute layer depth for each node
    const depthMemo = new Map<string, number>()
    const getDepth = (id: string, visited = new Set<string>()): number => {
      if (depthMemo.has(id)) return depthMemo.get(id)!
      if (visited.has(id)) return 0 // cycle guard

      visited.add(id)
      const task = taskMap.get(id)
      if (!task || task.depends_on.length === 0) {
        depthMemo.set(id, 0)
        return 0
      }

      let maxParentDepth = 0
      for (const parentId of task.depends_on) {
        maxParentDepth = Math.max(maxParentDepth, getDepth(parentId, new Set(visited)) + 1)
      }
      depthMemo.set(id, maxParentDepth)
      return maxParentDepth
    }

    tasks.forEach((t) => getDepth(t.id))

    // Group tasks by layer
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
            x: layerIndex * 280 + 40,
            y: taskIndex * 145 + 40,
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
          style: { stroke: '#818cf8', strokeWidth: 2 },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: '#818cf8',
            width: 16,
            height: 16,
          },
        })
      })
    })

    return { nodes: layoutNodes, edges: layoutEdges }
  }, [tasks])

  if (tasks.length === 0) {
    return (
      <div className="h-80 glass-card flex items-center justify-center text-neutral-500 text-sm">
        No valid tasks to preview. Paste or upload workflow JSON above.
      </div>
    )
  }

  return (
    <div className="w-full h-96 glass-card rounded-2xl overflow-hidden border border-white/10 relative">
      <div className="absolute top-3 left-4 z-10 flex items-center gap-2">
        <span className="badge-neutral text-xs">
          Interactive DAG ({tasks.length} {tasks.length === 1 ? 'task' : 'tasks'})
        </span>
        <span className="text-[11px] text-neutral-400">
          Scroll to zoom • Drag to pan
        </span>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          color="#374151"
          gap={20}
          size={1}
          variant={BackgroundVariant.Dots}
          className="bg-neutral-950/70"
        />
        <Controls
          className="!bg-neutral-900/90 !border-white/10 !rounded-xl !shadow-lg [&>button]:!bg-transparent [&>button]:!border-white/10 [&>button]:!text-white hover:[&>button]:!bg-white/10"
        />
      </ReactFlow>
    </div>
  )
}
