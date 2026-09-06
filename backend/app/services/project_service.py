"""
Infralytix — Project Management Service.

Coordinates project creation, ownership enforcement, file uploads,
and deterministic repository intelligence analysis pipelines.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.logging.logging import get_logger
from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.project import Project
from app.repositories.agent_run_repository import AgentRunRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.analysis_service import RepositoryAnalysisService

logger = get_logger(__name__)


class ProjectService:
    """Business logic for project workspaces, archive uploads, and agent analysis."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.project_repo = ProjectRepository(session)
        self.agent_run_repo = AgentRunRepository(session)

    async def get_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> Project:
        """
        Fetch project by ID, strictly enforcing user ownership.

        Raises:
            HTTPException: 404 if project does not exist OR belongs to another user.
                           (Masks existence to prevent enumeration attacks).
        """
        project = await self.project_repo.get_by_id(project_id)
        if not project or project.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    async def list_projects(self, user_id: uuid.UUID) -> list[Project]:
        """Fetch all projects owned by the user."""
        return await self.project_repo.list_by_user(user_id)

    async def create_project(self, user_id: uuid.UUID, data: ProjectCreate) -> Project:
        """Create a new project workspace for the user."""
        project = await self.project_repo.create(
            user_id=user_id,
            name=data.name,
            description=data.description,
            repo_name=data.repo_name,
        )
        logger.info(
            "Created new project",
            extra={"project_id": str(project.id), "user_id": str(user_id)},
        )
        return project

    async def update_project(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        data: ProjectUpdate,
    ) -> Project:
        """Update an existing project after validating ownership."""
        project = await self.get_project(user_id, project_id)
        update_data = data.model_dump(exclude_unset=True)
        return await self.project_repo.update(project, **update_data)

    async def delete_project(self, user_id: uuid.UUID, project_id: uuid.UUID) -> None:
        """Delete a project and any associated uploaded archive files."""
        project = await self.get_project(user_id, project_id)

        # Clean up storage folder if exists
        project_storage = Path(settings.UPLOAD_DIR) / str(user_id) / str(project_id)
        if project_storage.exists():
            shutil.rmtree(project_storage, ignore_errors=True)

        await self.project_repo.delete(project)
        logger.info(
            "Deleted project",
            extra={"project_id": str(project_id), "user_id": str(user_id)},
        )

    async def handle_upload(
        self,
        user_id: uuid.UUID,
        project_id: uuid.UUID,
        file: UploadFile,
    ) -> AgentRun:
        """
        Store uploaded repository zip archive and execute deterministic static analysis.

        Creates an AgentRun in PENDING -> RUNNING -> COMPLETED/FAILED state.
        """
        project = await self.get_project(user_id, project_id)

        if not file.filename or not file.filename.lower().endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .zip archives are supported for repository analysis",
            )

        # Prepare upload destination
        upload_dir = Path(settings.UPLOAD_DIR) / str(user_id) / str(project_id)
        upload_dir.mkdir(parents=True, exist_ok=True)
        archive_path = upload_dir / "repository.zip"

        try:
            with open(archive_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.error(
                "Failed to save uploaded archive",
                extra={"project_id": str(project_id), "error_message": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded archive",
            ) from e

        # Update project record
        await self.project_repo.update(
            project,
            archive_filename=file.filename,
            repo_name=project.repo_name or Path(file.filename).stem,
        )

        # Initialize AgentRun record
        run = await self.agent_run_repo.create(
            project_id=project.id,
            agent_type="repository",
            status=AgentRunStatus.PENDING,
        )

        # Run analysis pipeline
        run = await self.agent_run_repo.update_status(run, status=AgentRunStatus.RUNNING)
        try:
            analysis_result = RepositoryAnalysisService.analyze_archive(
                archive_path=archive_path,
                work_dir=upload_dir,
            )
            run = await self.agent_run_repo.update_status(
                run=run,
                status=AgentRunStatus.COMPLETED,
                output_data=analysis_result.model_dump(),
            )
            logger.info(
                "Completed repository intelligence analysis",
                extra={
                    "project_id": str(project_id),
                    "run_id": str(run.id),
                    "total_loc": analysis_result.total_loc,
                    "primary_language": analysis_result.primary_language,
                },
            )
        except Exception as e:
            error_text = str(e)
            logger.error(
                "Repository analysis run failed",
                extra={
                    "project_id": str(project_id),
                    "run_id": str(run.id),
                    "error_message": error_text,
                },
            )
            run = await self.agent_run_repo.update_status(
                run=run,
                status=AgentRunStatus.FAILED,
                error_message=error_text,
            )

        return run

    async def list_agent_runs(self, user_id: uuid.UUID, project_id: uuid.UUID) -> list[AgentRun]:
        """Fetch all agent run history for a project, enforcing user ownership."""
        await self.get_project(user_id, project_id)
        return await self.agent_run_repo.list_by_project(project_id)
