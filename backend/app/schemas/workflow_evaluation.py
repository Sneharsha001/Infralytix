"""
Infralytix — Workflow Evaluation Schemas (Pydantic v2).

Defines the InstanceSpec input and WorkflowEvaluation output for
the workflow performance estimator.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

# ─── Input ────────────────────────────────────────────────────────────────────


class InstanceSpec(BaseModel):
    """
    A candidate cloud instance type to evaluate a workflow against.

    Attributes:
        vcpu:              Number of available vCPU cores.
        ram_gb:            Available RAM in gigabytes.
        hourly_price_usd:  On-demand hourly price in USD.
        has_gpu:           Whether the instance provides GPU capacity.
                           Required for gpu_bound tasks; such tasks are marked
                           incompatible on non-GPU instances.
    """

    vcpu: int = Field(..., ge=1, description="Available vCPU cores.")
    ram_gb: float = Field(..., gt=0, description="Available RAM in GB.")
    hourly_price_usd: float = Field(..., gt=0, description="On-demand price per hour (USD).")
    has_gpu: bool = Field(
        default=False,
        description="True if the instance provides GPU capacity.",
    )


# ─── Per-task result ─────────────────────────────────────────────────────────


class TaskEvaluation(BaseModel):
    """
    Evaluation result for a single workflow task on a given instance.

    Attributes:
        task_id:              The task's caller-assigned identifier.
        scaled_time_seconds:  Estimated wall-clock time after resource scaling.
                              None when the task is incompatible with the instance
                              (gpu_bound task on a non-GPU instance).
        cost_usd:             Compute cost for this task (0.0 if incompatible).
    """

    task_id: str = Field(..., description="Task identifier.")
    scaled_time_seconds: float | None = Field(
        ...,
        description="Scaled wall-clock time in seconds, or None if incompatible.",
    )
    cost_usd: float = Field(..., ge=0, description="Compute cost for this task in USD.")


# ─── Aggregate result ─────────────────────────────────────────────────────────


class WorkflowEvaluation(BaseModel):
    """
    Aggregated evaluation of an entire workflow on a single instance type.

    Attributes:
        makespan_seconds:   Critical-path length in seconds (longest path through the
                            dependency DAG, accounting for parallel execution).
        total_cost_usd:     Sum of per-task compute costs.  Parallel tasks both incur
                            their individual costs because they each occupy instance
                            resources simultaneously.
        task_evaluations:   Per-task breakdown of scaled time and individual cost.
        incompatible_tasks: Task IDs that cannot run on this instance (gpu_bound tasks
                            on non-GPU instances).  Non-empty means the workflow cannot
                            fully execute on the candidate instance.
    """

    makespan_seconds: float = Field(..., ge=0, description="Critical-path makespan in seconds.")
    total_cost_usd: float = Field(
        ..., ge=0, description="Total compute cost in USD across all tasks."
    )
    task_evaluations: list[TaskEvaluation] = Field(
        ..., description="Per-task scaled time and cost breakdown."
    )
    incompatible_tasks: list[str] = Field(
        default_factory=list,
        description="Task IDs incompatible with this instance (gpu_bound on non-GPU).",
    )


__all__ = [
    "InstanceSpec",
    "TaskEvaluation",
    "WorkflowEvaluation",
]
