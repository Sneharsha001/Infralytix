"""
Infralytix — Project & Repository Intelligence Endpoints.

Implements:
  - POST /projects: Create a new project workspace
  - GET /projects: List projects owned by current user
  - GET /projects/{id}: Retrieve project details and latest analysis run
  - DELETE /projects/{id}: Delete project workspace and associated files
  - POST /projects/{id}/upload: Upload repository zip and execute deterministic analysis
  - GET /projects/{id}/agent-runs: List execution run history for a project

Ownership note:
  Access or deletion of a project not owned by current user responds with 404 (not 403)
  to mask project existence and prevent enumeration.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.middlewares.auth_middleware import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    AgentRunResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter()


def _to_project_response(project: Project) -> ProjectResponse:
    """Helper to convert Project ORM entity to ProjectResponse schema with latest_run."""
    latest = project.agent_runs[0] if project.agent_runs else None
    return ProjectResponse(
        id=project.id,
        user_id=project.user_id,
        name=project.name,
        description=project.description,
        repo_name=project.repo_name,
        archive_filename=project.archive_filename,
        created_at=project.created_at,
        updated_at=project.updated_at,
        latest_run=AgentRunResponse.model_validate(latest) if latest else None,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Creates a new project workspace owned by the authenticated user.",
)
async def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project workspace."""
    service = ProjectService(db)
    project = await service.create_project(current_user.id, project_in)
    return _to_project_response(project)


@router.get(
    "",
    response_model=list[ProjectResponse],
    status_code=status.HTTP_200_OK,
    summary="List current user's projects",
    description="Returns all projects owned by the authenticated user.",
)
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectResponse]:
    """List all projects belonging to the authenticated user."""
    service = ProjectService(db)
    projects = await service.list_projects(current_user.id)
    return [_to_project_response(p) for p in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project by ID",
    description="Retrieve project details. Returns 404 if not found or not owned by user.",
)
async def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Fetch project details for the authenticated user."""
    service = ProjectService(db)
    project = await service.get_project(current_user.id, project_id)
    return _to_project_response(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project",
    description="Update project details. Returns 404 if not found or not owned by user.",
)
async def update_project(
    project_id: uuid.UUID,
    project_in: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Update project details for the authenticated user."""
    service = ProjectService(db)
    project = await service.update_project(current_user.id, project_id, project_in)
    return _to_project_response(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete project",
    description="Delete project and clean up storage. Returns 404 if not found or not owned.",
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a project workspace and associated files."""
    service = ProjectService(db)
    await service.delete_project(current_user.id, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/upload",
    response_model=AgentRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload repository zip and analyze",
    description="Uploads a repository zip archive, stores it, and triggers static analysis.",
)
async def upload_repository(
    project_id: uuid.UUID,
    file: UploadFile = File(..., description="Repository zip archive"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AgentRunResponse:
    """Upload repository archive and execute deterministic static analysis."""
    service = ProjectService(db)
    run = await service.handle_upload(current_user.id, project_id, file)
    return AgentRunResponse.model_validate(run)


@router.get(
    "/{project_id}/agent-runs",
    response_model=list[AgentRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List project agent runs",
    description="Returns the history of agent and static analysis runs for a project.",
)
async def list_agent_runs(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AgentRunResponse]:
    """Retrieve run history for a project."""
    service = ProjectService(db)
    runs = await service.list_agent_runs(current_user.id, project_id)
    return [AgentRunResponse.model_validate(r) for r in runs]
