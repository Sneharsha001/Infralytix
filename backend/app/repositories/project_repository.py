"""
Infralytix — Project Repository.

Encapsulates all database queries and mutations for Project entities.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


class ProjectRepository:
    """Repository handling SQL persistence for Project entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, project_id: uuid.UUID) -> Project | None:
        """Fetch a single project by primary key ID."""
        stmt = select(Project).where(Project.id == project_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[Project]:
        """Fetch all projects owned by the specified user, ordered by creation desc."""
        stmt = (
            select(Project)
            .where(Project.user_id == user_id)
            .order_by(Project.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        description: str | None = None,
        repo_name: str | None = None,
    ) -> Project:
        """Create and persist a new project."""
        project = Project(
            user_id=user_id,
            name=name.strip(),
            description=description.strip() if description else None,
            repo_name=repo_name.strip() if repo_name else None,
        )
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def update(self, project: Project, **kwargs: object) -> Project:
        """Update fields on an existing project."""
        for key, value in kwargs.items():
            if hasattr(project, key) and value is not None:
                setattr(project, key, value)
        self.session.add(project)
        await self.session.flush()
        await self.session.refresh(project)
        return project

    async def delete(self, project: Project) -> None:
        """Delete a project and cascade-delete its agent runs."""
        await self.session.delete(project)
        await self.session.flush()
