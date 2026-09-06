"""
Infralytix — Multi-Cloud Cost Comparison Endpoint.

Provides public (no authentication required) multi-cloud cost evaluation
across AWS, Azure, and GCP with AI-assisted workload recommendations.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.schemas.cost_comparison import (
    CloudComparisonResponse,
    CloudResourceRequest,
)
from app.services.cost_comparison_service import cost_comparison_service

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


__all__ = ["router", "compare_cloud_costs"]
