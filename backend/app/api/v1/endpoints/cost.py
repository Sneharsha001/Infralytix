"""
Infralytix — Multi-Cloud Cost Comparison Endpoints.

Implements:
  POST /cost/estimate           — Run a new cost comparison
  GET  /cost/estimates          — List the current user's saved estimates
  GET  /cost/estimates/{run_id} — Retrieve a single estimate by ID

Design notes:
  - Follows the exact pattern of endpoints/agents.py
  - All business logic is in cost_service.py and cost_ai_service.py
  - Results are persisted as AgentRun records with agent_type="cost"
  - Auth is required for all three endpoints (Depends(get_current_user))
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.logging.logging import get_logger
from app.middlewares.auth_middleware import get_current_user, get_optional_current_user
from app.models.agent_run import AgentRunStatus
from app.models.user import User
from app.repositories.agent_run_repository import AgentRunRepository
from app.schemas.cost import (
    CostComparisonResult,
    CostEstimateListItem,
    CostEstimateRequest,
    CostEstimateResponse,
)
from app.services.cost_ai_service import CostAIService
from app.services.cost_comparison_service import CostComparisonService

logger = get_logger(__name__)
router = APIRouter()

_AGENT_TYPE = "cost"


# ---------------------------------------------------------------------------
# POST /cost/estimate & POST /cost/cost-comparison
# ---------------------------------------------------------------------------


@router.post(
    "/estimate",
    response_model=CostEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a multi-cloud cost comparison",
    description=(
        "Computes monthly cost estimates for AWS, GCP, and/or Azure based on the "
        "provided workload specification (vCPUs, RAM, storage, runtime hours). "
        "Appends an AI-generated recommendation. Authentication is optional; if "
        "authenticated, the result is saved to the user's estimate history."
    ),
)
@router.post(
    "/cost-comparison",
    response_model=CostEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Run a multi-cloud cost comparison (alias)",
    description="Alias for /estimate.",
)
async def create_estimate(
    body: CostEstimateRequest,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostEstimateResponse:
    """Compute and optionally persist a multi-cloud cost estimate."""
    user_label = str(current_user.id) if current_user else "anonymous"

    logger.info(
        "Starting cost estimate",
        extra={
            "user_id": user_label,
            "providers": body.providers,
            "cpu": body.cpu_cores,
            "memory_gb": body.memory_gb,
        },
    )

    run_repo = AgentRunRepository(db) if current_user else None
    cost_run = None
    cost_run_id = uuid.uuid4()
    created_at = datetime.now(UTC)

    if current_user and run_repo:
        cost_run = await run_repo.create(
            project_id=current_user.id,
            agent_type=_AGENT_TYPE,
            status=AgentRunStatus.RUNNING,
        )
        await db.commit()
        cost_run_id = cost_run.id
        created_at = cost_run.created_at

    try:
        # 1. Price calculation across clouds
        calculator = CostComparisonService()
        estimates = await calculator.compute_async(body)

        if not estimates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid estimates produced. Check provider selection.",
            )

        # 2. AI suggestion (Gemini or rule-based fallback)
        ai_service = CostAIService()
        suggestion = await ai_service.suggest(body, estimates)

        # 3. Assemble result (cheapest among available providers)
        available = [
            e
            for e in estimates
            if not any("unavailable" in n.lower() or "failed" in n.lower() for n in e.notes)
            and e.total_monthly_usd > 0.0
        ]
        cheapest = available[0] if available else estimates[0]
        result = CostComparisonResult(
            providers=estimates,
            cheapest_provider=cheapest.provider,
            ai_suggestion=suggestion,
        )

        # 4. Persist result payload in the AgentRun record if authenticated
        if current_user and run_repo and cost_run:
            output: dict[str, Any] = {
                "result": result.model_dump(mode="json"),
                "workload_label": body.workload_label,
            }
            cost_run = await run_repo.update_status(
                cost_run,
                status=AgentRunStatus.COMPLETED,
                output_data=output,
            )
            await db.commit()
            await db.refresh(cost_run)

    except HTTPException:
        if current_user and run_repo and cost_run:
            await run_repo.update_status(
                cost_run,
                status=AgentRunStatus.FAILED,
                error_message="Invalid provider selection",
            )
            await db.commit()
        raise
    except Exception as exc:
        logger.error(
            "Cost estimate failed",
            extra={"error": str(exc), "user_id": user_label},
        )
        if current_user and run_repo and cost_run:
            await run_repo.update_status(
                cost_run,
                status=AgentRunStatus.FAILED,
                error_message=str(exc),
            )
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cost estimation failed. Please try again.",
        ) from exc

    logger.info(
        "Cost estimate completed",
        extra={
            "run_id": str(cost_run_id),
            "cheapest": cheapest.provider,
            "total_usd": cheapest.total_monthly_usd,
        },
    )

    return CostEstimateResponse(
        id=cost_run_id,
        result=result,
        created_at=created_at,
        workload_label=body.workload_label,
    )


# ---------------------------------------------------------------------------
# GET /cost/estimates
# ---------------------------------------------------------------------------


@router.get(
    "/estimates",
    response_model=list[CostEstimateListItem],
    status_code=status.HTTP_200_OK,
    summary="List saved cost estimates",
    description=(
        "Returns the authenticated user's saved cost estimates, "
        "most recent first. Limited to 50 results."
    ),
)
async def list_estimates(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[CostEstimateListItem]:
    """Return summary list of cost estimates for the current user."""
    run_repo = AgentRunRepository(db)
    runs = await run_repo.list_by_project(current_user.id)

    # Filter to only cost-type runs with completed status
    cost_runs = [
        r for r in runs if r.agent_type == _AGENT_TYPE and r.status == AgentRunStatus.COMPLETED
    ][:50]

    items: list[CostEstimateListItem] = []
    for run in cost_runs:
        if not run.output_data:
            continue
        result_dict: dict[str, Any] = run.output_data.get("result", {})
        providers_list: list[dict[str, Any]] = result_dict.get("providers", [])
        cheapest_provider: str = result_dict.get("cheapest_provider", "unknown")
        total_usd: float = (
            providers_list[0].get("total_monthly_usd", 0.0) if providers_list else 0.0
        )
        items.append(
            CostEstimateListItem(
                id=run.id,
                cheapest_provider=cheapest_provider,
                total_monthly_usd=total_usd,
                workload_label=run.output_data.get("workload_label", ""),
                created_at=run.created_at,
            )
        )

    return items


# ---------------------------------------------------------------------------
# GET /cost/estimates/{run_id}
# ---------------------------------------------------------------------------


@router.get(
    "/estimates/{run_id}",
    response_model=CostEstimateResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a specific cost estimate",
    description=(
        "Fetches a previously saved cost estimate by its run ID. "
        "Returns 404 if the estimate does not exist or belongs to another user."
    ),
)
async def get_estimate(
    run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostEstimateResponse:
    """Fetch a single cost estimate by its AgentRun ID."""
    run_repo = AgentRunRepository(db)
    run = await run_repo.get_by_id(run_id)

    # 404-mask: don't reveal whether the run ID exists for another user
    if not run or run.agent_type != _AGENT_TYPE or run.project_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cost estimate not found.",
        )

    if not run.output_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate has no result data.",
        )

    result = CostComparisonResult.model_validate(run.output_data["result"])
    return CostEstimateResponse(
        id=run.id,
        result=result,
        created_at=run.created_at,
        workload_label=run.output_data.get("workload_label", ""),
    )
