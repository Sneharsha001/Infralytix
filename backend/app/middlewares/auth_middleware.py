"""
Infralytix — Authentication and RBAC Middlewares / Dependencies.

Provides:
  - `get_current_user`: FastAPI dependency that validates the Bearer token,
    loads the User via UserRepository, and rejects unauthenticated/expired requests (401).
  - `require_role`: Higher-order dependency for Role-Based Access Control (RBAC),
    verifying the user has an authorized role (403).
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.exceptions.exceptions import ForbiddenException, UnauthorizedException
from app.logging.logging import get_logger
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.services.auth_service import auth_service

logger = get_logger(__name__)

# HTTPBearer with auto_error=False allows custom exception raising
security_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    FastAPI dependency to extract and authenticate the current user.

    Steps:
      1. Verify Authorization Bearer header is present.
      2. Decode and validate JWT access token signature & expiration.
      3. Retrieve User from database via UserRepository.
      4. Ensure user exists and is active.

    Raises:
      UnauthorizedException (401) on any authentication failure.
    """
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(message="Authentication credentials were not provided")

    token = credentials.credentials
    payload = auth_service.decode_token(token, expected_type="access")

    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedException(message="Token subject identifier missing")

    try:
        user_id = uuid.UUID(sub)
    except ValueError as e:
        raise UnauthorizedException(message="Invalid user identifier format") from e

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)

    if not user:
        logger.warning("Token subject does not match any user", extra={"user_id": sub})
        raise UnauthorizedException(message="User not found")

    if not user.is_active:
        logger.warning("Authenticated user account is deactivated", extra={"user_id": sub})
        raise UnauthorizedException(message="User account is deactivated")

    return user


def require_role(*allowed_roles: UserRole) -> Callable[..., Any]:
    """
    Generate an RBAC dependency that permits only specified roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMINISTRATOR))])
        async def admin_dashboard(): ...

    Raises:
        ForbiddenException (403) if authenticated user's role is not in allowed_roles.
    """

    async def role_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_roles:
            logger.warning(
                "RBAC access denied",
                extra={
                    "user_id": str(current_user.id),
                    "user_role": current_user.role.value,
                    "allowed_roles": [r.value for r in allowed_roles],
                },
            )
            raise ForbiddenException(
                message="You do not have permission to access this resource",
                details={
                    "current_role": current_user.role.value,
                    "required_roles": [r.value for r in allowed_roles],
                },
            )
        return current_user

    return role_checker
