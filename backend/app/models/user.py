"""
Infralytix — User ORM Model.

Defines the User entity representing registered accounts and their roles.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.refresh_token import RefreshToken


class UserRole(str, enum.Enum):
    """
    Role-Based Access Control (RBAC) user roles.

    USER: Standard developer account, can run workflows and view own data.
    ADMINISTRATOR: Full administrative access across the platform.
    EVALUATOR: Read-only access across all workflows, runs, and dashboards.
    """

    USER = "user"
    ADMINISTRATOR = "administrator"
    EVALUATOR = "evaluator"


class User(BaseModel):
    """
    User entity representing an authenticated account.

    Note on relationships:
        Every relationship on this model and future models MUST use lazy="selectin".
        Default lazy loading (lazy="select") issues synchronous SQL queries when an
        attribute is accessed, which triggers Greenlet / MissingGreenlet exceptions
        in SQLAlchemy's AsyncSession. Eager loading via selectin ensures related
        objects are loaded safely within the active async transaction.
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role"),
        default=UserRole.USER,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Note: Using lazy="selectin" for AsyncSession safety as detailed above
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="user",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="Project.created_at.desc()",
    )

    def __repr__(self) -> str:
        """String representation of User."""
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"
