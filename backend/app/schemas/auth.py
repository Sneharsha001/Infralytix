"""
Infralytix — Authentication Schemas (Pydantic v2).

Defines request and response schemas for registration, login, and tokens.
Design rule: UserResponse strictly NEVER exposes hashed_password or password fields.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserRegister(BaseModel):
    """Payload for user registration."""

    name: str = Field(..., min_length=2, max_length=120, description="Full user name")
    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (minimum 8 characters)",
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="Account role (user, administrator, or evaluator)",
    )


class UserLogin(BaseModel):
    """Payload for user authentication."""

    email: EmailStr = Field(..., description="User account email")
    password: str = Field(..., description="Account password")


class TokenResponse(BaseModel):
    """Response returned upon successful login or token refresh."""

    access_token: str = Field(..., description="JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Token type header prefix")
    expires_in: int = Field(..., description="Access token expiration window in seconds")


class UserResponse(BaseModel):
    """
    Public representation of a User.

    Notice: hashed_password is strictly excluded to prevent credential leakage.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Unique user identifier")
    name: str = Field(..., description="User full name")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(..., description="Assigned role")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Account last update timestamp")


class TokenPayload(BaseModel):
    """Decoded JWT payload data structure."""

    sub: str = Field(..., description="Subject claim (user id string)")
    role: str = Field(..., description="User role claim")
    exp: int = Field(..., description="Expiration timestamp (unix epoch)")
    token_type: str = Field(default="access", description="Token type ('access' or 'refresh')")
