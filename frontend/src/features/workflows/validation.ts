/**
 * Infralytix — Workflow DAG Client-Side Schema Validation.
 *
 * Performs real-time static checking:
 * 1. JSON syntax validity.
 * 2. Field types and range constraints.
 * 3. Unique task IDs.
 * 4. Dangling dependency references.
 * 5. Cycle detection via Kahn's algorithm (topological sorting).
 */

import { ValidationFeedback, WorkflowTaskInput } from './types'

const VALID_CATEGORIES = new Set(['cpu_bound', 'io_bound', 'memory_bound', 'gpu_bound'])

export function validateWorkflowJson(rawJson: string): {
  parsed: WorkflowTaskInput[] | null
  feedback: ValidationFeedback
} {
  const errors: string[] = []

  if (!rawJson.trim()) {
    return {
      parsed: null,
      feedback: {
        isValid: false,
        errors: ['Please enter or upload a workflow JSON definition.'],
        taskCount: 0,
        peakVcpu: 0,
        peakRamGb: 0,
        totalBaselineSeconds: 0,
      },
    }
  }

  let data: unknown
  try {
    data = JSON.parse(rawJson)
  } catch (err) {
    return {
      parsed: null,
      feedback: {
        isValid: false,
        errors: [`Invalid JSON syntax: ${(err as Error).message}`],
        taskCount: 0,
        peakVcpu: 0,
        peakRamGb: 0,
        totalBaselineSeconds: 0,
      },
    }
  }

  if (typeof data !== 'object' || data === null) {
    errors.push('Root must be a JSON object containing a "tasks" array.')
    return {
      parsed: null,
      feedback: {
        isValid: false,
        errors,
        taskCount: 0,
        peakVcpu: 0,
        peakRamGb: 0,
        totalBaselineSeconds: 0,
      },
    }
  }

  const rawTasks = (data as Record<string, unknown>).tasks
  if (!Array.isArray(rawTasks)) {
    errors.push('The "tasks" field is required and must be an array of task objects.')
    return {
      parsed: null,
      feedback: {
        isValid: false,
        errors,
        taskCount: 0,
        peakVcpu: 0,
        peakRamGb: 0,
        totalBaselineSeconds: 0,
      },
    }
  }

  if (rawTasks.length === 0) {
    errors.push('The "tasks" array cannot be empty. At least one task is required.')
    return {
      parsed: null,
      feedback: {
        isValid: false,
        errors,
        taskCount: 0,
        peakVcpu: 0,
        peakRamGb: 0,
        totalBaselineSeconds: 0,
      },
    }
  }

  const taskMap = new Map<string, WorkflowTaskInput>()
  const parsedTasks: WorkflowTaskInput[] = []
  let peakVcpu = 0
  let peakRamGb = 0
  let totalBaselineSeconds = 0

  // ── Step 1: Validate individual task fields ──────────────────────────────
  rawTasks.forEach((raw, index) => {
    const taskPrefix = `Task #${index + 1}`

    if (typeof raw !== 'object' || raw === null) {
      errors.push(`${taskPrefix} is not a valid JSON object.`)
      return
    }

    const t = raw as Record<string, unknown>
    const id = typeof t.id === 'string' ? t.id.trim() : ''
    const name = typeof t.name === 'string' ? t.name.trim() : ''
    const category = typeof t.category === 'string' ? t.category.trim() : ''
    const baselineTime = typeof t.baseline_time_seconds === 'number' ? t.baseline_time_seconds : -1
    const baselineVcpu = typeof t.baseline_vcpu === 'number' ? t.baseline_vcpu : -1
    const baselineRam = typeof t.baseline_ram_gb === 'number' ? t.baseline_ram_gb : -1
    const dependsOn = Array.isArray(t.depends_on) ? t.depends_on : null

    if (!id) {
      errors.push(`${taskPrefix}: Missing or empty "id".`)
    } else if (taskMap.has(id)) {
      errors.push(`Duplicate task id "${id}" found at task #${index + 1}.`)
    }

    if (!name) {
      errors.push(`${taskPrefix} (${id || 'unknown'}): Missing or empty "name".`)
    }

    if (!VALID_CATEGORIES.has(category)) {
      errors.push(
        `${taskPrefix} (${id || 'unknown'}): Invalid category "${category}". Must be one of cpu_bound, io_bound, memory_bound, gpu_bound.`
      )
    }

    if (baselineTime <= 0) {
      errors.push(
        `${taskPrefix} (${id || 'unknown'}): "baseline_time_seconds" must be a positive number (> 0).`
      )
    }

    if (baselineVcpu < 1 || !Number.isInteger(baselineVcpu)) {
      errors.push(
        `${taskPrefix} (${id || 'unknown'}): "baseline_vcpu" must be an integer >= 1.`
      )
    }

    if (baselineRam <= 0) {
      errors.push(
        `${taskPrefix} (${id || 'unknown'}): "baseline_ram_gb" must be a positive number (> 0).`
      )
    }

    if (!dependsOn || !dependsOn.every((dep) => typeof dep === 'string')) {
      errors.push(
        `${taskPrefix} (${id || 'unknown'}): "depends_on" must be an array of string task IDs.`
      )
    }

    if (id && !taskMap.has(id)) {
      const taskObj: WorkflowTaskInput = {
        id,
        name: name || id,
        category: (category as WorkflowTaskInput['category']) || 'cpu_bound',
        baseline_time_seconds: baselineTime > 0 ? baselineTime : 1,
        baseline_vcpu: baselineVcpu >= 1 ? baselineVcpu : 1,
        baseline_ram_gb: baselineRam > 0 ? baselineRam : 1,
        depends_on: dependsOn ? dependsOn.map(String) : [],
      }
      taskMap.set(id, taskObj)
      parsedTasks.push(taskObj)

      peakVcpu = Math.max(peakVcpu, taskObj.baseline_vcpu)
      peakRamGb = Math.max(peakRamGb, taskObj.baseline_ram_gb)
      totalBaselineSeconds += taskObj.baseline_time_seconds
    }
  })

  // ── Step 2: Validate dependency references (dangling deps & self-deps) ────
  for (const task of parsedTasks) {
    for (const depId of task.depends_on) {
      if (depId === task.id) {
        errors.push(`Task "${task.id}" cannot depend on itself.`)
      } else if (!taskMap.has(depId)) {
        errors.push(`Task "${task.id}" references non-existent dependency "${depId}".`)
      }
    }
  }

  // ── Step 3: Cycle detection via Kahn's algorithm (Topological sort) ──────
  if (errors.length === 0 && parsedTasks.length > 0) {
    const inDegree = new Map<string, number>()
    const adj = new Map<string, string[]>()

    for (const task of parsedTasks) {
      inDegree.set(task.id, task.depends_on.length)
      for (const parentId of task.depends_on) {
        if (!adj.has(parentId)) {
          adj.set(parentId, [])
        }
        adj.get(parentId)!.push(task.id)
      }
    }

    const queue: string[] = []
    for (const [taskId, deg] of inDegree.entries()) {
      if (deg === 0) {
        queue.push(taskId)
      }
    }

    let visitedCount = 0
    while (queue.length > 0) {
      const current = queue.shift()!
      visitedCount++

      const neighbors = adj.get(current) || []
      for (const neighbor of neighbors) {
        const nextDeg = inDegree.get(neighbor)! - 1
        inDegree.set(neighbor, nextDeg)
        if (nextDeg === 0) {
          queue.push(neighbor)
        }
      }
    }

    if (visitedCount < parsedTasks.length) {
      errors.push(
        'Cycle detected in dependency graph. Workflows must be Directed Acyclic Graphs (DAGs).'
      )
    }
  }

  return {
    parsed: errors.length === 0 ? parsedTasks : null,
    feedback: {
      isValid: errors.length === 0,
      errors,
      taskCount: parsedTasks.length,
      peakVcpu,
      peakRamGb,
      totalBaselineSeconds,
    },
  }
}
