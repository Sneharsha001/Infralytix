"""
Infralytix — Base ORM Model.

Every SQLAlchemy model in the application inherits from BaseModel.
Provides:
    - UUID primary key (id)
    - UTC timestamp on creation (created_at)
    - UTC timestamp on update (updated_at)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy entities."""
    pass


class BaseModel(Base):
    """
    Abstract base model providing id, created_at, and updated_at.

    All entity models inherit from this class to maintain consistent
    primary keys and audit timestamps.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """String representation showing class name and id."""
        return f"<{self.__class__.__name__}(id={self.id})>"
