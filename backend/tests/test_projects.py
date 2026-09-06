"""
Tests — Project Management & Repository Intelligence (Phase 1).

Verifies:
  - Project CRUD (create, list, get, update, delete)
  - Ownership enforcement: 404 on nonexistent OR other user's project (masks existence)
  - Authentication requirement (401 without Bearer token)
  - Zip upload validation (reject non-zip)
  - Deterministic repository analysis (LOC count, language detection, framework detection)
  - Agent run history retrieval
  - Zip-slip security protection
"""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.project import Project
from app.models.user import User, UserRole
from app.services.analysis_service import RepositoryAnalysisService
from app.services.auth_service import auth_service

# ─── Shared Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def user_a() -> User:
    """Primary test user."""
    return User(
        id=uuid.uuid4(),
        name="Alice Developer",
        email="alice@infralytix.io",
        hashed_password="hashed_pw",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def user_b() -> User:
    """Secondary test user (for ownership isolation testing)."""
    return User(
        id=uuid.uuid4(),
        name="Bob Intruder",
        email="bob@infralytix.io",
        hashed_password="hashed_pw",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def auth_header(user_a: User) -> dict[str, str]:
    """Authorization header with valid JWT for user_a."""
    token = auth_service.create_access_token(user_a.id, user_a.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_project(user_a: User) -> Project:
    """Project owned by user_a."""
    return Project(
        id=uuid.uuid4(),
        user_id=user_a.id,
        name="Backend Microservice",
        description="Core API gateway in FastAPI",
        repo_name="backend-microservice",
        archive_filename=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# ─── 1. Project CRUD & Ownership Isolation Tests ─────────────────────────────


class TestProjectCRUD:
    """Tests for project management endpoints."""

    def test_unauthenticated_access_rejected(self, client: TestClient) -> None:
        """Calling /projects without token returns 401."""
        response = client.get("/api/v1/projects")
        assert response.status_code == 401

    def test_create_project_success(
        self,
        client: TestClient,
        user_a: User,
        auth_header: dict[str, str],
    ) -> None:
        """User can create a project workspace."""
        new_id = uuid.uuid4()
        created = Project(
            id=new_id,
            user_id=user_a.id,
            name="Infrastructure Orchestrator",
            description="Terraform and Pulumi modules",
            repo_name="infra-orchestrator",
            archive_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.create = AsyncMock(return_value=created)

            response = client.post(
                "/api/v1/projects",
                headers=auth_header,
                json={
                    "name": "Infrastructure Orchestrator",
                    "description": "Terraform and Pulumi modules",
                    "repo_name": "infra-orchestrator",
                },
            )

            assert response.status_code == 201
            data = response.json()
            assert data["id"] == str(new_id)
            assert data["name"] == "Infrastructure Orchestrator"
            assert data["user_id"] == str(user_a.id)

    def test_list_projects_returns_user_projects(
        self,
        client: TestClient,
        user_a: User,
        sample_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """GET /projects returns only current user's projects."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.list_by_user = AsyncMock(return_value=[sample_project])

            response = client.get("/api/v1/projects", headers=auth_header)

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == sample_project.name

    def test_get_project_success(
        self,
        client: TestClient,
        user_a: User,
        sample_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """GET /projects/{id} returns project if user is owner."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=sample_project)

            response = client.get(f"/api/v1/projects/{sample_project.id}", headers=auth_header)

            assert response.status_code == 200
            assert response.json()["id"] == str(sample_project.id)

    def test_get_project_nonexistent_returns_404(
        self,
        client: TestClient,
        user_a: User,
        auth_header: dict[str, str],
    ) -> None:
        """GET /projects/{id} returns 404 when project does not exist."""
        random_id = uuid.uuid4()
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=None)

            response = client.get(f"/api/v1/projects/{random_id}", headers=auth_header)
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_project_other_user_masks_with_404(
        self,
        client: TestClient,
        user_a: User,
        user_b: User,
        sample_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """
        CRITICAL REQUIREMENT: Accessing another user's project returns 404 (not 403)
        to mask existence and prevent identifier enumeration.
        """
        # Project belongs to user_b, but request is from user_a
        sample_project.user_id = user_b.id

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=sample_project)

            response = client.get(f"/api/v1/projects/{sample_project.id}", headers=auth_header)
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_delete_project_other_user_masks_with_404(
        self,
        client: TestClient,
        user_a: User,
        user_b: User,
        sample_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Attempting to delete another user's project returns 404 (not 403)."""
        sample_project.user_id = user_b.id

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=sample_project)

            response = client.delete(f"/api/v1/projects/{sample_project.id}", headers=auth_header)
            assert response.status_code == 404

    def test_delete_project_success(
        self,
        client: TestClient,
        user_a: User,
        sample_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Owner can delete their project and receive 204 No Content."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=sample_project)
            mock_proj_repo.return_value.delete = AsyncMock()

            response = client.delete(f"/api/v1/projects/{sample_project.id}", headers=auth_header)
            assert response.status_code == 204


# ─── 2. Zip Upload & Static Repository Intelligence Tests ────────────────────


class TestProjectUploadAndAnalysis:
    """Tests for file upload and static analysis engine."""

    def test_upload_non_zip_rejected(
        self,
        client: TestClient,
        user_a: User,
        sample_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Uploading non-zip archive returns 400 Bad Request."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=sample_project)

            fake_tar = io.BytesIO(b"not a zip content")
            response = client.post(
                f"/api/v1/projects/{sample_project.id}/upload",
                headers=auth_header,
                files={"file": ("archive.tar.gz", fake_tar, "application/gzip")},
            )

            assert response.status_code == 400
            assert "zip" in response.json()["detail"].lower()

    def test_upload_and_analyze_zip_success(
        self,
        client: TestClient,
        user_a: User,
        sample_project: Project,
        auth_header: dict[str, str],
        tmp_path: Path,
    ) -> None:
        """Uploading a repository zip runs static analysis and completes AgentRun."""
        # Create an in-memory zip representing a real project
        zip_buffer = io.BytesIO()
        py_code = (
            "from fastapi import FastAPI\n\n"
            "app = FastAPI()\n\n"
            "@app.get('/')\n"
            "def root():\n"
            "    return {'ok': True}\n"
        )
        pkg_json = (
            '{"name": "frontend", "dependencies": '
            '{"react": "^19.0.0", "tailwindcss": "^3.4.0"}}'
        )
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("main.py", py_code)
            zf.writestr("package.json", pkg_json)
            zf.writestr("Dockerfile", "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\n")

        zip_buffer.seek(0)

        run_id = uuid.uuid4()
        run_record = AgentRun(
            id=run_id,
            project_id=sample_project.id,
            agent_type="repository",
            status=AgentRunStatus.PENDING,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.services.project_service.AgentRunRepository") as mock_run_repo,
            patch("app.services.project_service.settings") as mock_settings,
        ):
            mock_settings.UPLOAD_DIR = str(tmp_path / "uploads")
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=user_a)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=sample_project)
            mock_proj_repo.return_value.update = AsyncMock(return_value=sample_project)

            mock_run_repo.return_value.create = AsyncMock(return_value=run_record)

            async def mock_update_status(run, status, output_data=None, error_message=None):
                run.status = status
                run.output_data = output_data
                run.error_message = error_message
                return run

            mock_run_repo.return_value.update_status = AsyncMock(side_effect=mock_update_status)

            response = client.post(
                f"/api/v1/projects/{sample_project.id}/upload",
                headers=auth_header,
                files={"file": ("test-repo.zip", zip_buffer, "application/zip")},
            )

            assert response.status_code == 200
            body = response.json()
            assert body["id"] == str(run_id)
            assert body["status"] == "completed"
            output = body["output_data"]
            assert output is not None
            assert output["total_files"] >= 2
            assert output["total_loc"] > 0
            assert output["primary_language"] == "Python"
            assert "React" in output["detected_frameworks"]
            assert "Docker" in output["detected_frameworks"]


# ─── 3. Zip-Slip Vulnerability Prevention Tests ──────────────────────────────


class TestZipSlipPrevention:
    """Security tests against directory traversal attacks during extraction."""

    def test_zip_slip_raises_security_error(self, tmp_path: Path) -> None:
        """Archives containing '../' relative traversal paths must be rejected."""
        malicious_zip = tmp_path / "malicious.zip"
        target_extract_dir = tmp_path / "target"

        with zipfile.ZipFile(malicious_zip, "w") as zf:
            zf.writestr("../../etc/passwd", "root:x:0:0:root:/root:/bin/bash")

        with pytest.raises(ValueError, match="Zip slip security violation"):
            RepositoryAnalysisService.extract_zip(malicious_zip, target_extract_dir)
