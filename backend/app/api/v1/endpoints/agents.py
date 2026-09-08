"""
Infralytix — AI Agent Orchestration Endpoints.

Implements:
  - POST /projects/{id}/analyze: Trigger Gemini AI analysis of a repository
  - GET  /projects/{id}/analysis: Fetch the latest AI insight result

Ownership note:
  Both endpoints return 404 for projects not owned by the current user,
  masking project existence to prevent enumeration.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.logging.logging import get_logger
from app.middlewares.auth_middleware import get_current_user
from app.models.agent_run import AgentRunStatus
from app.models.user import User
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import AgentRunResponse
from app.services.ai_agent_service import GeminiAgentService

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/{project_id}/analyze",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger AI analysis",
    description=(
        "Runs Gemini-powered architectural analysis on the latest repository upload. "
        "Returns 422 if no repository has been uploaded yet for this project. "
        "Returns 404 if project does not exist or is not owned by the current user."
    ),
)
async def trigger_analysis(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """Trigger the AI agent pipeline against the latest Phase 1 static analysis."""
    project_repo = ProjectRepository(db)
    run_repo = AgentRunRepository(db)

    # Ownership guard (404-masks existence)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Require a completed Phase 1 analysis as input context
    repo_run = await run_repo.get_latest_by_type(project_id, "repository")
    if not repo_run or repo_run.status != AgentRunStatus.COMPLETED or not repo_run.output_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "No completed repository analysis found. "
                "Upload a repository zip first via POST /projects/{id}/upload."
            ),
        )

    logger.info(
        "Starting AI analysis",
        extra={"project_id": str(project_id), "user_id": str(current_user.id)},
    )

    # Create a new AgentRun record in RUNNING state
    ai_run = await run_repo.create(
        project_id=project_id,
        agent_type="gemini",
        status=AgentRunStatus.RUNNING,
    )
    await db.commit()

    # Run analysis (real Gemini or heuristic fallback)
    service = GeminiAgentService()
    try:
        insight = await service.analyze(project, repo_run.output_data)
        ai_run = await run_repo.update_status(
            ai_run,
            status=AgentRunStatus.COMPLETED,
            output_data=insight.model_dump(),
        )
        await db.commit()
        await db.refresh(ai_run)
    except Exception as exc:
        logger.error(
            "AI analysis failed",
            extra={"error": str(exc), "project_id": str(project_id)},
        )
        ai_run = await run_repo.update_status(
            ai_run,
            status=AgentRunStatus.FAILED,
            error_message=str(exc),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI analysis failed. Please try again.",
        ) from exc

    logger.info(
        "AI analysis completed",
        extra={"project_id": str(project_id), "run_id": str(ai_run.id)},
    )
    return AgentRunResponse.model_validate(ai_run)


@router.get(
    "/{project_id}/analysis",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest AI analysis result",
    description=(
        "Retrieves the most recent Gemini agent run result for a project. "
        "Returns 404 if no AI analysis has been run yet, or if project is not owned."
    ),
)
async def get_analysis(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """Fetch the most recent AI insight result for a project."""
    project_repo = ProjectRepository(db)
    run_repo = AgentRunRepository(db)

    # Ownership guard (404-masks existence)
    project = await project_repo.get_by_id(project_id)
    if not project or project.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    ai_run = await run_repo.get_latest_by_type(project_id, "gemini")
    if not ai_run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI analysis found. Run POST /projects/{id}/analyze first.",
        )

    return AgentRunResponse.model_validate(ai_run)
