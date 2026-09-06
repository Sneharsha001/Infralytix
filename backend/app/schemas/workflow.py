"""
Infralytix — Workflow Schemas (Pydantic v2).

Defines Request and Response schemas for the workflow submission endpoint.
Each workflow is a list of tasks forming a Directed Acyclic Graph (DAG).
"""

from __future__ import annotations

import uuid
from enum import Enum

from pydantic import BaseModel, Field

# ─── Enums ───────────────────────────────────────────────────────────────────


class TaskCategory(str, Enum):
    """Classification of a task's primary resource bottleneck."""

    cpu_bound = "cpu_bound"
    io_bound = "io_bound"
    memory_bound = "memory_bound"
    gpu_bound = "gpu_bound"


# ─── Request Schemas ─────────────────────────────────────────────────────────


class WorkflowTaskRequest(BaseModel):
    """
    A single task within a workflow submission.

    The ``depends_on`` list encodes directed edges in the DAG: each entry must
    reference the ``id`` of another task in the same workflow request.
    """

    id: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Caller-assigned unique identifier for this task within the workflow.",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Human-readable task name.",
    )
    category: TaskCategory = Field(
        ...,
        description="Resource category: cpu_bound | io_bound | memory_bound | gpu_bound.",
    )
    baseline_time_seconds: float = Field(
        ...,
        gt=0,
        description="Estimated baseline wall-clock time in seconds (must be > 0).",
    )
    baseline_vcpu: int = Field(
        ...,
        ge=1,
        description="Minimum vCPU cores required by this task.",
    )
    baseline_ram_gb: float = Field(
        ...,
        gt=0,
        description="Minimum RAM in GB required by this task (must be > 0).",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="IDs of tasks that must complete before this task starts.",
    )


class WorkflowCreateRequest(BaseModel):
    """
    Request body for POST /api/v1/workflows.

    The ``tasks`` list must be non-empty, each task id must be unique within
    the workflow, all ``depends_on`` references must point to existing task ids,
    and the dependency graph must be acyclic.
    """

    tasks: list[WorkflowTaskRequest] = Field(
        ...,
        min_length=1,
        description="Ordered list of tasks forming the workflow DAG.",
    )


# ─── Response Schemas ────────────────────────────────────────────────────────


class WorkflowTaskResponse(BaseModel):
    """A validated task as returned in the workflow response."""

    id: str = Field(..., description="Caller-assigned task identifier.")
    name: str = Field(..., description="Human-readable task name.")
    category: TaskCategory = Field(..., description="Resource category.")
    baseline_time_seconds: float = Field(..., description="Baseline wall-clock time in seconds.")
    baseline_vcpu: int = Field(..., description="Minimum vCPU cores required.")
    baseline_ram_gb: float = Field(..., description="Minimum RAM in GB required.")
    depends_on: list[str] = Field(default_factory=list, description="Upstream task IDs.")


class WorkflowResponse(BaseModel):
    """
    Response returned by POST /api/v1/workflows on successful DAG validation.

    ``workflow_id`` is a server-assigned UUID for the validated workflow.
    ``task_count`` mirrors ``len(tasks)`` for quick consumer use.
    """

    workflow_id: uuid.UUID = Field(
        ...,
        description="Server-assigned UUID for this validated workflow.",
    )
    task_count: int = Field(
        ...,
        ge=1,
        description="Number of tasks in the validated workflow.",
    )
    tasks: list[WorkflowTaskResponse] = Field(
        ...,
        description="Validated task list (same order as submitted).",
    )


__all__ = [
    "TaskCategory",
    "WorkflowCreateRequest",
    "WorkflowResponse",
    "WorkflowTaskRequest",
    "WorkflowTaskResponse",
]
