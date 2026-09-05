"""
Infralytix — Refresh Token ORM Model.

Stores hashed refresh tokens for session rotation and revocation.
Matches IEEE 1016 SDD §5.1 / §6.4 specification: only the SHA-256 hash of
the refresh token is persisted to prevent token exposure in database breaches.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(BaseModel):
    """
    Persisted refresh token record.

    Only SHA-256 hash of the token is saved.
    Rotated tokens have revoked_at populated.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Note: Using lazy="selectin" for AsyncSession safety
    user: Mapped[User] = relationship(
        "User",
        back_populates="refresh_tokens",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        """String representation of RefreshToken."""
        is_revoked = self.revoked_at is not None
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, revoked={is_revoked})>"
