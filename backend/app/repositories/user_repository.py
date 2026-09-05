"""
Infralytix — User Repository.

Encapsulates all database interactions for User and RefreshToken entities.
No business logic or endpoint dependencies live here.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole


class UserRepository:
    """Repository handling SQL persistence for users and refresh tokens."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch a single user by their UUID primary key."""
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a single user by their email address (case-insensitive search)."""
        stmt = select(User).where(User.email == email.lower().strip())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        email: str,
        hashed_password: str,
        role: UserRole = UserRole.USER,
    ) -> User:
        """Create and persist a new user record."""
        user = User(
            name=name.strip(),
            email=email.lower().strip(),
            hashed_password=hashed_password,
            role=role,
            is_active=True,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update(self, user: User, **kwargs: object) -> User:
        """Update fields on an existing user entity."""
        for key, value in kwargs.items():
            if value is not None and hasattr(user, key):
                setattr(user, key, value)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    # ─── Refresh Token Persistence ───────────────────────────────────────────

    async def create_refresh_token(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        """Save a new hashed refresh token."""
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_refresh_token_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Fetch an active or revoked refresh token by its SHA-256 hash."""
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_refresh_token(self, token: RefreshToken) -> None:
        """Mark a specific refresh token as revoked."""
        token.revoked_at = datetime.now(UTC)
        self.session.add(token)
        await self.session.flush()

    async def revoke_all_user_refresh_tokens(self, user_id: uuid.UUID) -> None:
        """Revoke all refresh tokens for a user (security defense against token reuse/theft)."""
        now = datetime.now(UTC)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.session.execute(stmt)
        await self.session.flush()
