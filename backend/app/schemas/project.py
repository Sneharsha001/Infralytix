"""
Infralytix — Project & Repository Intelligence Schemas (Pydantic v2).

Defines separate Request and Response schemas for projects, uploads, and agent runs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent_run import AgentRunStatus


# ─── Request Schemas ─────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=120, description="Project name")
    description: str | None = Field(default=None, max_length=1000, description="Project description")
    repo_name: str | None = Field(default=None, max_length=120, description="Repository name")


class ProjectUpdate(BaseModel):
    """Schema for updating an existing project."""

    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    repo_name: str | None = Field(default=None, max_length=120)


# ─── Analysis Output Schemas ────────────────────────────────────────────────


class LanguageStat(BaseModel):
    """File extension / language statistic."""

    language: str = Field(..., description="Detected programming language")
    extension: str = Field(..., description="File extension")
    file_count: int = Field(..., ge=0, description="Number of source files")
    loc: int = Field(..., ge=0, description="Approximate lines of code")
    percentage: float = Field(..., ge=0.0, le=100.0, description="Percentage of total LOC")


class DependencyFile(BaseModel):
    """Detected dependency manifest file and parsed packages."""

    filename: str = Field(..., description="File path relative to repository root")
    package_manager: str = Field(..., description="Package manager ecosystem")
    dependencies: list[str] = Field(default_factory=list, description="Extracted dependency list")


class RepositoryAnalysisResult(BaseModel):
    """Structured deterministic repository intelligence analysis result."""

    total_files: int = Field(..., ge=0, description="Total source files analyzed")
    total_loc: int = Field(..., ge=0, description="Total source lines of code")
    primary_language: str | None = Field(default=None, description="Dominant language by LOC")
    languages: list[LanguageStat] = Field(default_factory=list, description="Language breakdown")
    dependency_files: list[DependencyFile] = Field(
        default_factory=list,
        description="Manifests detected",
    )
    detected_frameworks: list[str] = Field(
        default_factory=list,
        description="Key frameworks / libraries identified",
    )


# ─── Response Schemas ────────────────────────────────────────────────────────


class AgentRunResponse(BaseModel):
    """Schema for returning an agent execution run."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Agent run ID")
    project_id: uuid.UUID = Field(..., description="Associated project ID")
    agent_type: str = Field(..., description="Type of agent run")
    status: AgentRunStatus = Field(..., description="Run status")
    output_data: dict[str, Any] | None = Field(default=None, description="Output payload")
    error_message: str | None = Field(default=None, description="Error message if failed")
    created_at: datetime = Field(..., description="Run start timestamp")
    updated_at: datetime = Field(..., description="Run completion timestamp")


class ProjectResponse(BaseModel):
    """Schema for returning a project and its metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Project UUID")
    user_id: uuid.UUID = Field(..., description="Owner user UUID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(default=None, description="Project description")
    repo_name: str | None = Field(default=None, description="Repository name")
    archive_filename: str | None = Field(default=None, description="Uploaded archive filename")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    latest_run: AgentRunResponse | None = Field(default=None, description="Most recent agent run")
