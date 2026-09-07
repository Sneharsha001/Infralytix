"""
Infralytix — Workflow Endpoint.

POST /api/v1/workflows
  - Accepts a WorkflowCreateRequest (list of tasks with dependency edges).
  - Validates the DAG (unique ids, no dangling references, no cycles).
  - Returns a WorkflowResponse with a server-assigned workflow_id on success.
  - Returns HTTP 422 with a clear error message on any validation failure.

No authentication is required for this phase (stateless validation only).
No database persistence occurs — the validated result is returned directly.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.logging.logging import get_logger
from app.schemas.workflow import WorkflowCreateRequest, WorkflowResponse
from app.schemas.workflow_optimizer import (
    WorkflowOptimizeRequest,
    WorkflowOptimizeResult,
)
from app.services.workflow_optimizer_service import workflow_optimizer_service
from app.services.workflow_service import WorkflowValidationError, workflow_service

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=WorkflowResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit and validate a workflow DAG",
    description=(
        "Accepts a workflow definition as an ordered list of tasks with dependency edges. "
        "Validates that task ids are unique, all depends_on references exist, and the "
        "dependency graph is acyclic. Returns the validated workflow with a server-assigned "
        "workflow_id on success, or HTTP 422 with a clear error message on validation failure."
    ),
    responses={
        201: {"description": "Workflow validated successfully."},
        422: {
            "description": (
                "Workflow failed DAG validation (cycle, dangling ref, or empty list)."
            )
        },
    },
)
async def submit_workflow(
    request: WorkflowCreateRequest,
) -> WorkflowResponse | JSONResponse:
    """
    Validate and accept a workflow DAG submission.

    Business rules enforced by WorkflowService:
    - Non-empty task list (Pydantic min_length=1 on ``tasks`` field).
    - All task ids are unique within the workflow.
    - All depends_on entries reference existing task ids.
    - The dependency graph contains no cycles.
    """
    try:
        return workflow_service.validate_and_build(request)
    except WorkflowValidationError as exc:
        logger.warning(f"workflow_validation_failed reason={exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "WORKFLOW_VALIDATION_ERROR",
                    "message": str(exc),
                    "details": None,
                }
            },
        )


@router.post(
    "/optimize",
    response_model=WorkflowOptimizeResult,
    status_code=status.HTTP_200_OK,
    summary="Optimize workflow across multi-cloud instance catalog",
    description=(
        "Validates the workflow DAG and sweeps AWS, Azure, and GCP candidate instances "
        "concurrently. Returns the Pareto-optimal frontier labelled with Fastest, Cheapest, "
        "and Best balance."
    ),
    responses={
        200: {"description": "Pareto optimization completed successfully."},
        422: {"description": "Workflow DAG validation failed."},
    },
)
async def optimize_workflow(
    request: WorkflowOptimizeRequest,
) -> WorkflowOptimizeResult | JSONResponse:
    """
    Validate workflow and compute Pareto-optimal cloud instance recommendations.
    """
    try:
        validated_workflow = workflow_service.validate_and_build(request.workflow)
    except WorkflowValidationError as exc:
        logger.warning(f"workflow_optimization_validation_failed reason={exc}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "code": "WORKFLOW_VALIDATION_ERROR",
                    "message": str(exc),
                    "details": None,
                }
            },
        )

    return await workflow_optimizer_service.optimize(
        validated_workflow,
        region=request.region,
    )


__all__ = ["optimize_workflow", "router", "submit_workflow"]
