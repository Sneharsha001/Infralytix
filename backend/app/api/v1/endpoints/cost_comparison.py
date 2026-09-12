"""
Infralytix — Multi-Cloud Cost Comparison Endpoint.

Provides public (no authentication required) multi-cloud cost evaluation
across AWS, Azure, and GCP with AI-assisted workload recommendations.
"""

from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, status

from app.schemas.cost_comparison import (
    CloudComparisonResponse,
    CloudResourceRequest,
)
from app.schemas.workload_inference import WorkloadInferenceResult
from app.services.cost_comparison_service import cost_comparison_service
from app.services.workload_inference_service import process_archive_for_workload

router = APIRouter()


@router.post(
    "",
    response_model=CloudComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare cloud workload costs across AWS, Azure, and GCP",
    description=(
        "Evaluates real-time compute and storage pricing across AWS, Azure, and GCP "
        "concurrently without requiring authentication. Returns matched instance types, "
        "monthly cost estimates, and an AI-generated architectural recommendation."
    ),
)
async def compare_cloud_costs(
    request: CloudResourceRequest,
) -> CloudComparisonResponse:
    """
    Public multi-cloud cost comparison endpoint.
    """
    return await cost_comparison_service.compare_clouds(request)


@router.post(
    "/infer-workload",
    response_model=WorkloadInferenceResult,
    status_code=status.HTTP_200_OK,
    summary="Infer workload compute profile from repository archive (public)",
    description=(
        "Upload a repository zip archive (max 50 MB). Runs static analysis and calls "
        "Gemini (or deterministic heuristics when no API key is configured) to return "
        "estimated vCPU, RAM, storage, and a one-line justification. "
        "Public endpoint — no authentication or database project required."
    ),
    responses={
        200: {"description": "Workload profile inferred successfully."},
        400: {"description": "Invalid file — only .zip archives are accepted."},
        500: {"description": "Archive extraction or analysis failed."},
    },
)
async def infer_workload(
    file: UploadFile = File(..., description="Repository zip archive (.zip)"),
) -> WorkloadInferenceResult:
    """
    Public workload inference endpoint for pre-flight cost comparison.
    """
    return await process_archive_for_workload(file, log_extra={"endpoint": "cost_comparison"})


__all__ = ["router", "compare_cloud_costs", "infer_workload"]
