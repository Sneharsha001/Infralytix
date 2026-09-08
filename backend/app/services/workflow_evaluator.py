"""
Infralytix — Workflow Evaluator.

Pure, I/O-free module that estimates how a validated workflow DAG performs on a
single candidate cloud instance type.

Public API
----------
    scale_task_time(task, instance) -> float | None
    compute_makespan(tasks, scaled_times) -> float
    evaluate_workflow(workflow, instance) -> WorkflowEvaluation

Scaling Model
-------------
Each task's baseline_time_seconds was measured on a reference instance with
baseline_vcpu cores and baseline_ram_gb RAM.  The candidate instance may have
different resources, so we scale the time accordingly:

    cpu_bound:
        The task parallelises well across vCPUs.  Scaled time shrinks inversely
        with the vCPU ratio, but real-world super-linear speed-up is rare, so we
        cap the speedup at MAX_CPU_SPEEDUP (default 16×).

        speedup = min(candidate_vcpu / baseline_vcpu, MAX_CPU_SPEEDUP)
        scaled  = baseline / speedup

    io_bound:
        Throughput increases weakly with more vCPUs (Amdahl's law – mostly serial
        I/O waits dominate).  We use a sub-linear power law with exponent
        IO_VCPU_EXPONENT (default 0.3) and cap at IO_MAX_SPEEDUP (default 2×).

        speedup = min((candidate_vcpu / baseline_vcpu) ** IO_VCPU_EXPONENT,
                      IO_MAX_SPEEDUP)
        scaled  = baseline / speedup

    memory_bound:
        The bottleneck is data movement through RAM, not compute.  Scaling is
        proportional to the RAM ratio, capped at MAX_RAM_SPEEDUP (default 8×).

        speedup = min(candidate_ram_gb / baseline_ram_gb, MAX_RAM_SPEEDUP)
        scaled  = baseline / speedup

    gpu_bound:
        Requires a GPU-enabled instance.  Returns None ("incompatible") if the
        candidate instance does not have a GPU.  When the instance does have a GPU
        the baseline_time_seconds is returned unchanged (no further scaling without
        GPU-specific spec data).

Critical Path (Makespan)
------------------------
Given the dependency edges, tasks can execute in parallel once all predecessors
finish.  The workflow completes at the end of its *critical path* — the longest
weighted path through the DAG — NOT the sum of all task times.

Implementation: we build a networkx DiGraph where every node carries a
``duration`` attribute equal to its scaled time.  We then use
``nx.dag_longest_path_length`` with a weight function that accumulates durations
along the path.

    Technically we model edge weight as the duration of the *source* node, so
    the longest-path length equals the sum of durations along the critical path.
    The final node's duration is added explicitly after the longest-path call.

Cost Model
----------
Each task occupies the instance for its scaled duration (no bin-packing or
packing efficiency: we assume one task runs at a time on the cores it needs,
which is conservative).  Parallel tasks both incur cost because they each
use instance resources.

    task_cost = (scaled_time_seconds / 3600) * instance.hourly_price_usd
    total_cost = sum(task_cost for all compatible tasks)
"""

from __future__ import annotations

from typing import Final

import networkx as nx

from app.schemas.workflow import TaskCategory, WorkflowResponse, WorkflowTaskResponse
from app.schemas.workflow_evaluation import (
    InstanceSpec,
    TaskEvaluation,
    WorkflowEvaluation,
)

# ─── Scaling Constants ────────────────────────────────────────────────────────

#: Maximum CPU speedup multiplier for cpu_bound tasks.
#: Enforces diminishing returns beyond 16× parallelism.
MAX_CPU_SPEEDUP: Final[float] = 16.0

#: Sub-linear vCPU exponent for io_bound tasks (Amdahl fraction ≈ 0.3).
IO_VCPU_EXPONENT: Final[float] = 0.3

#: Maximum speedup for io_bound tasks (near-flat; mostly serial I/O waits).
IO_MAX_SPEEDUP: Final[float] = 2.0

#: Maximum speedup multiplier for memory_bound tasks.
MAX_RAM_SPEEDUP: Final[float] = 8.0


# ─── WorkflowEvaluationError ─────────────────────────────────────────────────


class WorkflowEvaluationError(ValueError):
    """
    Raised when the workflow cannot be evaluated on the given instance.

    Current trigger: every task in the workflow is gpu_bound but the candidate
    instance has no GPU — makespan and cost would both be undefined.
    """


# ─── Step 1: Scale a single task's time ──────────────────────────────────────


def scale_task_time(
    task: WorkflowTaskResponse,
    instance: InstanceSpec,
) -> float | None:
    """
    Compute the expected wall-clock time for *task* running on *instance*.

    Args:
        task:     A validated workflow task (from WorkflowResponse.tasks).
        instance: The candidate cloud instance specification.

    Returns:
        Estimated wall-clock time in seconds (> 0) for compatible tasks, or
        ``None`` for gpu_bound tasks on a non-GPU instance.

    Scaling behaviour:
        - cpu_bound:    inversely proportional to vCPU ratio, capped at MAX_CPU_SPEEDUP.
        - io_bound:     sub-linear with vCPUs (exponent IO_VCPU_EXPONENT), capped at IO_MAX_SPEEDUP.
        - memory_bound: inversely proportional to RAM ratio, capped at MAX_RAM_SPEEDUP.
        - gpu_bound:    None if instance.has_gpu is False; baseline unchanged otherwise.
    """
    category = task.category
    baseline = task.baseline_time_seconds

    if category == TaskCategory.gpu_bound:
        if not instance.has_gpu:
            return None
        # No further scaling without GPU-specific throughput data
        return baseline

    if category == TaskCategory.cpu_bound:
        vcpu_ratio: float = instance.vcpu / task.baseline_vcpu
        speedup = min(vcpu_ratio, MAX_CPU_SPEEDUP)
        return baseline / speedup

    if category == TaskCategory.io_bound:
        vcpu_ratio = instance.vcpu / task.baseline_vcpu
        speedup = min(float(vcpu_ratio**IO_VCPU_EXPONENT), IO_MAX_SPEEDUP)
        return baseline / speedup

    # memory_bound
    ram_ratio: float = instance.ram_gb / task.baseline_ram_gb
    speedup = min(ram_ratio, MAX_RAM_SPEEDUP)
    return baseline / speedup


# ─── Step 2: Critical-path makespan ──────────────────────────────────────────


def compute_makespan(
    tasks: list[WorkflowTaskResponse],
    scaled_times: dict[str, float],
) -> float:
    """
    Compute workflow makespan as the longest weighted path through the DAG.

    Only tasks present in *scaled_times* (compatible tasks) are included.
    Incompatible gpu_bound tasks on non-GPU instances are excluded; their
    dependents are still evaluated with 0-duration predecessors, which is a
    conservative approximation.

    Args:
        tasks:        All workflow tasks (for reconstructing dependency edges).
        scaled_times: Mapping of task_id -> scaled wall-clock seconds for
                      compatible tasks.  Incompatible task_ids are absent.

    Returns:
        Total critical-path duration in seconds.  Returns 0.0 when there are no
        compatible tasks.

    Algorithm — CPM (Critical Path Method) in topological order:
        For each node visited in topological order, compute its *earliest finish time*:

            EF[node] = max(EF[pred] for pred in predecessors, default=0)
                       + duration[node]

        This is the standard CPM forward-pass.
        Makespan = max(EF) over all nodes.

        This approach is correct regardless of fan-out/fan-in topology and avoids
        the ambiguity of edge-weight ties that occur when source-only edge weights
        are used with ``nx.dag_longest_path_length``.
    """
    if not scaled_times:
        return 0.0

    dag: nx.DiGraph = nx.DiGraph()

    # Nodes: only compatible tasks
    for task_id in scaled_times:
        dag.add_node(task_id)

    # Edges: dep_id -> task_id means dep must finish before task starts
    task_by_id: dict[str, WorkflowTaskResponse] = {t.id: t for t in tasks}
    for task_id in scaled_times:
        task = task_by_id[task_id]
        for dep_id in task.depends_on:
            if dep_id in scaled_times:
                dag.add_edge(dep_id, task_id)

    # CPM forward pass in topological order
    earliest_finish: dict[str, float] = {}
    for _node in nx.topological_sort(dag):
        node: str = str(_node)
        duration: float = scaled_times[node]
        pred_max: float = max(
            (earliest_finish[str(p)] for p in dag.predecessors(_node)),
            default=0.0,
        )
        earliest_finish[node] = pred_max + duration

    return max(earliest_finish.values())


# ─── Step 3: Top-level evaluator ─────────────────────────────────────────────


def evaluate_workflow(
    workflow: WorkflowResponse,
    instance: InstanceSpec,
) -> WorkflowEvaluation:
    """
    Estimate workflow performance on a single candidate instance type.

    This function is **pure** — no I/O, no database access, no external calls.
    It can be called from tests, API endpoints, or CLI scripts equally.

    Args:
        workflow: A validated WorkflowResponse (output of WorkflowService).
        instance: The candidate instance to evaluate against.

    Returns:
        WorkflowEvaluation containing:
            - makespan_seconds:   Critical-path length (not sum of all task times).
            - total_cost_usd:     Sum of per-task costs (parallel tasks both count).
            - task_evaluations:   Per-task breakdown.
            - incompatible_tasks: task_ids that cannot run on this instance.

    Raises:
        WorkflowEvaluationError: If *every* task is incompatible with the instance,
            making both makespan and cost undefined.
    """
    tasks = workflow.tasks

    # ── 1. Scale each task's time ────────────────────────────────────────────
    task_evals: list[TaskEvaluation] = []
    scaled_times: dict[str, float] = {}
    incompatible: list[str] = []

    for task in tasks:
        scaled = scale_task_time(task, instance)

        if scaled is None:
            incompatible.append(task.id)
            task_evals.append(
                TaskEvaluation(task_id=task.id, scaled_time_seconds=None, cost_usd=0.0)
            )
        else:
            scaled_times[task.id] = scaled
            task_cost = (scaled / 3600.0) * instance.hourly_price_usd
            task_evals.append(
                TaskEvaluation(
                    task_id=task.id,
                    scaled_time_seconds=scaled,
                    cost_usd=round(task_cost, 6),
                )
            )

    # ── 2. Guard: nothing runnable ────────────────────────────────────────────
    if not scaled_times:
        raise WorkflowEvaluationError(
            "All tasks in this workflow are gpu_bound but the candidate instance "
            f"has no GPU (instance: {instance.vcpu} vCPU, {instance.ram_gb} GB RAM). "
            "Select a GPU-enabled instance type to evaluate this workflow."
        )

    # ── 3. Critical-path makespan ─────────────────────────────────────────────
    makespan = compute_makespan(tasks, scaled_times)

    # ── 4. Total cost: sum individual task costs ──────────────────────────────
    total_cost = round(sum(e.cost_usd for e in task_evals), 6)

    return WorkflowEvaluation(
        makespan_seconds=round(makespan, 4),
        total_cost_usd=total_cost,
        task_evaluations=task_evals,
        incompatible_tasks=incompatible,
    )


__all__ = [
    "MAX_CPU_SPEEDUP",
    "IO_VCPU_EXPONENT",
    "IO_MAX_SPEEDUP",
    "MAX_RAM_SPEEDUP",
    "WorkflowEvaluationError",
    "scale_task_time",
    "compute_makespan",
    "evaluate_workflow",
]
