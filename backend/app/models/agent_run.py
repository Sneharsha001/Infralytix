"""
Infralytix — AgentRun ORM Model.

Defines an execution run of an AI agent or deterministic analyzer on a project.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING, Any
import uuid

from sqlalchemy import ForeignKey, JSON, String, Text, Uuid
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.project import Project


class AgentRunStatus(str, enum.Enum):
    """Execution status for an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentRun(BaseModel):
    """
    Records an execution of an agent pipeline or static analyzer.

    All relationships use lazy="selectin" for AsyncSession safety.
    """

    __tablename__ = "agent_runs"

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_type: Mapped[str] = mapped_column(
        String(50),
        default="repository",
        nullable=False,
    )
    status: Mapped[AgentRunStatus] = mapped_column(
        SQLEnum(AgentRunStatus, name="agent_run_status"),
        default=AgentRunStatus.PENDING,
        nullable=False,
    )
    output_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    project: Mapped[Project] = relationship(
        "Project",
        back_populates="agent_runs",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of AgentRun."""
        return f"<AgentRun(id={self.id}, type={self.agent_type}, status={self.status.value})>"
