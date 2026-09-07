"""
Infralytix — Workflow Service.

Validates an incoming workflow DAG and returns a WorkflowResponse.

Validation rules (in order):
  1. Task list must not be empty (enforced by Pydantic min_length=1 on the request).
  2. Every task id must be unique within the workflow.
  3. Every depends_on entry must reference an existing task id in the workflow.
  4. The dependency graph must be acyclic (no cycles allowed).

Business logic is deliberately free of HTTP concerns; the endpoint translates
WorkflowValidationError into HTTP 422.
"""

from __future__ import annotations

import uuid

import networkx as nx

from app.logging.logging import get_logger
from app.schemas.workflow import (
    WorkflowCreateRequest,
    WorkflowResponse,
    WorkflowTaskResponse,
)

logger = get_logger(__name__)


class WorkflowValidationError(ValueError):
    """
    Raised when a workflow request fails semantic validation.

    The message is human-readable and safe to surface directly in a 422 response.
    """


class WorkflowService:
    """
    Pure business-logic service for workflow DAG validation.

    No database access occurs in this phase — the validated workflow is returned
    directly to the caller. Persistence will be added in a future sprint.
    """

    def validate_and_build(self, request: WorkflowCreateRequest) -> WorkflowResponse:
        """
        Validate the submitted workflow DAG and return a WorkflowResponse.

        Args:
            request: Parsed and Pydantic-validated workflow submission.

        Returns:
            WorkflowResponse with a server-assigned ``workflow_id`` and the
            validated task list.

        Raises:
            WorkflowValidationError: If any semantic DAG constraint is violated.
                Possible messages include:
                - Duplicate task id
                - Dangling depends_on reference
                - Cycle detected
        """
        tasks = request.tasks

        # ── 1. Duplicate id check ────────────────────────────────────────────
        seen_ids: set[str] = set()
        for task in tasks:
            if task.id in seen_ids:
                raise WorkflowValidationError(
                    f"Duplicate task id '{task.id}': every task id must be unique "
                    "within the workflow."
                )
            seen_ids.add(task.id)

        logger.debug(f"workflow_unique_ids_ok total_tasks={len(tasks)}")

        # ── 2. Dangling dependency check ─────────────────────────────────────
        for task in tasks:
            for dep_id in task.depends_on:
                if dep_id not in seen_ids:
                    raise WorkflowValidationError(
                        f"Task '{task.id}' has a depends_on reference to '{dep_id}', "
                        "which does not exist in this workflow."
                    )

        logger.debug("workflow_dependency_references_ok")

        # ── 3. Cycle check via networkx ──────────────────────────────────────
        dag: nx.DiGraph = nx.DiGraph()
        dag.add_nodes_from(task.id for task in tasks)
        for task in tasks:
            for dep_id in task.depends_on:
                # Edge direction: dep_id → task.id (dep must run before task)
                dag.add_edge(dep_id, task.id)

        if not nx.is_directed_acyclic_graph(dag):
            # Find one cycle to report a descriptive error message
            cycle = nx.find_cycle(dag, orientation="original")
            cycle_path = " → ".join(u for u, *_ in cycle)
            raise WorkflowValidationError(
                f"Workflow contains a cycle: {cycle_path}. "
                "Circular dependencies are not permitted."
            )

        logger.debug("workflow_dag_acyclic_ok")

        # ── 4. Build response ────────────────────────────────────────────────
        workflow_id = uuid.uuid4()
        task_responses = [
            WorkflowTaskResponse(
                id=task.id,
                name=task.name,
                category=task.category,
                baseline_time_seconds=task.baseline_time_seconds,
                baseline_vcpu=task.baseline_vcpu,
                baseline_ram_gb=task.baseline_ram_gb,
                depends_on=task.depends_on,
            )
            for task in tasks
        ]

        logger.info(f"workflow_validated_ok workflow_id={workflow_id} task_count={len(tasks)}")

        return WorkflowResponse(
            workflow_id=workflow_id,
            task_count=len(task_responses),
            tasks=task_responses,
        )


# Module-level singleton — mirrors the pattern used by cost_comparison_service
workflow_service = WorkflowService()

__all__ = [
    "WorkflowService",
    "WorkflowValidationError",
    "workflow_service",
]
