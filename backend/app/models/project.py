"""
Infralytix — Project ORM Model.

Represents a user project / repository workspace.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.user import User


class Project(BaseModel):
    """
    User project representing a repository or infrastructure environment.

    All relationships use lazy="selectin" for AsyncSession safety.
    """

    __tablename__ = "projects"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    repo_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    archive_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(
        "User",
        back_populates="projects",
        lazy="selectin",
    )
    agent_runs: Mapped[list[AgentRun]] = relationship(
        "AgentRun",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="AgentRun.created_at.desc()",
    )

    def __repr__(self) -> str:
        """String representation of Project."""
        return f"<Project(id={self.id}, name='{self.name}', user_id={self.user_id})>"
