"""
Infralytix — AgentRun Repository.

Encapsulates database operations for AgentRun entities.
"""

from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun, AgentRunStatus


class AgentRunRepository:
    """Repository handling SQL persistence for AgentRun entities."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        project_id: uuid.UUID,
        agent_type: str = "repository",
        status: AgentRunStatus = AgentRunStatus.PENDING,
        output_data: dict[str, Any] | None = None,
    ) -> AgentRun:
        """Create and persist a new agent run."""
        run = AgentRun(
            project_id=project_id,
            agent_type=agent_type,
            status=status,
            output_data=output_data,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_by_id(self, run_id: uuid.UUID) -> AgentRun | None:
        """Fetch a single run by ID."""
        stmt = select(AgentRun).where(AgentRun.id == run_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_project(self, project_id: uuid.UUID) -> list[AgentRun]:
        """Fetch all agent runs for a project, newest first."""
        stmt = (
            select(AgentRun)
            .where(AgentRun.project_id == project_id)
            .order_by(AgentRun.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        run: AgentRun,
        status: AgentRunStatus,
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
    ) -> AgentRun:
        """Update run status, results payload, and error message."""
        run.status = status
        if output_data is not None:
            run.output_data = output_data
        if error_message is not None:
            run.error_message = error_message
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run
