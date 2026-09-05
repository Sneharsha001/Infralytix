"""
Infralytix — Authentication Endpoints.

Implements:
  - POST /register: User registration
  - POST /login: User authentication, returns access token + sets HttpOnly refresh cookie
  - POST /refresh: Token refresh with automatic rotation and cookie update
  - POST /logout: Revokes refresh token and clears HttpOnly cookie
  - GET /me: Retrieves current authenticated user profile
  - GET /admin-only: RBAC-gated route for verifying administrator permissions
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.database.session import get_db
from app.exceptions.exceptions import UnauthorizedException
from app.middlewares.auth_middleware import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.auth import (
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)
from app.services.auth_service import auth_service

router = APIRouter()


class RefreshFallbackPayload(BaseModel):
    """Optional payload for clients unable to use cookies (e.g. CLI tools)."""

    refresh_token: str | None = Field(default=None, description="Raw refresh token fallback")


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account with hashed password and default role.",
)
async def register(
    user_in: UserRegister,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Register a new user account."""
    user = await auth_service.register_user(db, user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user",
    description=(
        "Authenticates credentials, returns access token in body, "
        "sets HttpOnly refresh cookie."
    ),
)
async def login(
    login_in: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate user, set HttpOnly refresh cookie, and return access token."""
    user, access_token, raw_refresh_token = await auth_service.authenticate_user(db, login_in)

    # Set secure HttpOnly cookie for refresh token
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",  # noqa: S106
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="Validates and rotates the refresh token from HttpOnly cookie or payload.",
)
async def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshFallbackPayload | None = None,
    cookie_token: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate refresh token and issue a fresh access token."""
    raw_token = (
        request.cookies.get("refresh_token")
        or cookie_token
        or (payload.refresh_token if payload else None)
    )

    if not raw_token:
        raise UnauthorizedException(message="Refresh token not found in cookie or request body")

    new_access_token, new_raw_refresh = await auth_service.refresh_access_token(db, raw_token)

    # Update HttpOnly cookie with rotated refresh token
    response.set_cookie(
        key="refresh_token",
        value=new_raw_refresh,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth",
    )

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",  # noqa: S106
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout user",
    description="Revokes the active refresh token and clears the HttpOnly cookie.",
)
async def logout(
    request: Request,
    response: Response,
    cookie_token: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    payload: RefreshFallbackPayload | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Revoke refresh token and remove cookie."""
    raw_token = (
        request.cookies.get("refresh_token")
        or cookie_token
        or (payload.refresh_token if payload else None)
    )
    if raw_token:
        await auth_service.revoke_refresh_token(db, raw_token)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
    )
    return {"message": "Successfully logged out"}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user",
    description="Protected route retrieving the authenticated user's profile.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.get(
    "/admin-only",
    status_code=status.HTTP_200_OK,
    summary="Admin only endpoint",
    description="RBAC-gated route requiring the administrator role.",
)
async def admin_only_route(
    current_admin: User = Depends(require_role(UserRole.ADMINISTRATOR)),
) -> dict[str, Any]:
    """Test endpoint demonstrating RBAC role restriction."""
    return {
        "message": f"Welcome, Administrator {current_admin.name}!",
        "role": current_admin.role.value,
    }
