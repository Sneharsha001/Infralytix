"""
Infralytix — User Schemas (Pydantic v2).

Defines separate Request and Response schemas for user operations.
Request and response schemas are explicitly separate classes.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class UserCreate(BaseModel):
    """Schema for creating a new user (internal or admin user provisioning)."""

    name: str = Field(..., min_length=2, max_length=120, description="Full user name")
    email: EmailStr = Field(..., description="Unique user email address")
    password: str = Field(..., min_length=8, max_length=128, description="Initial password")
    role: UserRole = Field(default=UserRole.USER, description="User role")


class UserUpdate(BaseModel):
    """Schema for updating an existing user's attributes."""

    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = Field(default=None)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class UserRead(BaseModel):
    """Schema for reading user details (response)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="User unique UUID")
    name: str = Field(..., description="Full user name")
    email: str = Field(..., description="User email address")
    role: UserRole = Field(..., description="User role")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
