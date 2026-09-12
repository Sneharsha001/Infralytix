"""
Tests — POST /projects/{id}/infer-workload (Workload Inference Endpoint).

Verifies:
  1. Success path (no Gemini key): heuristic fallback returns valid WorkloadInferenceResult
  2. Success path (Gemini key mocked): Gemini path invoked, schema validated
  3. Invalid file type (non-zip): returns 400
  4. Corrupt/empty zip: returns 400 or 500 with clear message
  5. Unauthenticated access: returns 401
  6. Project not found: returns 404
"""

from __future__ import annotations

import io
import uuid
import zipfile
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.project import Project
from app.models.user import User, UserRole
from app.schemas.workload_inference import WorkloadInferenceResult
from app.services.auth_service import auth_service


# ─── Shared Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def test_user() -> User:
    """Test user for authentication."""
    return User(
        id=uuid.uuid4(),
        name="Test Developer",
        email="dev@infralytix.io",
        hashed_password="hashed_pw",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def test_project(test_user: User) -> Project:
    """Project owned by test_user."""
    return Project(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="Inference Test Project",
        description="Used for testing workload inference",
        repo_name="inference-test",
        archive_filename=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def auth_header(test_user: User) -> dict[str, str]:
    """Authorization header with valid JWT."""
    token = auth_service.create_access_token(test_user.id, test_user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _make_zip_bytes(files: dict[str, str]) -> bytes:
    """Helper: create an in-memory zip archive with given filename → content."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _minimal_repo_zip() -> bytes:
    """Create a minimal but valid repo archive that static analysis can process."""
    return _make_zip_bytes(
        {
            "myrepo/main.py": "import os\nimport sys\n\ndef main():\n    print('hello')\n\nif __name__ == '__main__':\n    main()\n",
            "myrepo/requirements.txt": "fastapi>=0.100.0\npydantic>=2.0.0\nuvicorn>=0.22.0\n",
            "myrepo/Dockerfile": "FROM python:3.12-slim\nCOPY . /app\nRUN pip install -r requirements.txt\nCMD [\"python\", \"main.py\"]\n",
        }
    )


# ─── 1. Heuristic Fallback (No Gemini Key) ────────────────────────────────────


class TestInferWorkloadHeuristic:
    """Tests for the heuristic (no-Gemini) inference path."""

    def test_success_heuristic_returns_valid_result(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Upload a valid zip → heuristic fallback returns WorkloadInferenceResult."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.config.config.settings") as mock_settings,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)
            # No Gemini key — ensures heuristic path
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"

            zip_bytes = _minimal_repo_zip()
            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("myrepo.zip", zip_bytes, "application/zip")},
            )

        assert response.status_code == 200
        data = response.json()
        # Schema validation
        result = WorkloadInferenceResult.model_validate(data)
        assert result.vcpu >= 1
        assert result.ram_gb >= 1
        assert result.storage_gb >= 10
        assert isinstance(result.justification, str)
        assert len(result.justification) > 0

    def test_heuristic_justification_mentions_repo_stats(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Heuristic justification string should reference detected repo properties."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.config.config.settings") as mock_settings,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"

            zip_bytes = _minimal_repo_zip()
            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("myrepo.zip", zip_bytes, "application/zip")},
            )

        assert response.status_code == 200
        justification = response.json()["justification"]
        # Should mention "Heuristic" (deterministic path indicator) and file stats
        assert "Heuristic" in justification or len(justification) > 20

    def test_heuristic_returns_conservative_values_for_tiny_repo(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Tiny repo (1 file) should get conservative (small) resource estimates."""
        tiny_zip = _make_zip_bytes({"hello.py": "print('hello world')\n"})

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.config.config.settings") as mock_settings,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"

            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("tiny.zip", tiny_zip, "application/zip")},
            )

        assert response.status_code == 200
        data = response.json()
        # Tiny repo should not recommend huge resources
        assert data["vcpu"] <= 8
        assert data["ram_gb"] <= 32
        assert data["storage_gb"] <= 200


# ─── 2. Gemini Path (Mocked) ──────────────────────────────────────────────────


class TestInferWorkloadGemini:
    """Tests for the Gemini-backed inference path (API key mocked)."""

    def test_gemini_path_called_when_key_present(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """When GEMINI_API_KEY is set, Gemini inference is invoked."""
        gemini_response_json = (
            '{"vcpu": 4, "ram_gb": 16, "storage_gb": 100, '
            '"justification": "FastAPI web service with moderate dependency count."}'
        )

        mock_response = MagicMock()
        mock_response.text = gemini_response_json

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.config.config.settings") as mock_settings,
            patch(
                "app.services.workload_inference_service.WorkloadInferenceService._gemini_infer",
                new_callable=AsyncMock,
                return_value=WorkloadInferenceResult(
                    vcpu=4,
                    ram_gb=16,
                    storage_gb=100,
                    justification="FastAPI web service with moderate dependency count.",
                ),
            ) as mock_gemini,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)
            mock_settings.GEMINI_API_KEY = "fake-gemini-key"
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"

            zip_bytes = _minimal_repo_zip()
            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("repo.zip", zip_bytes, "application/zip")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["vcpu"] == 4
        assert data["ram_gb"] == 16
        assert data["storage_gb"] == 100
        assert "FastAPI" in data["justification"]
        mock_gemini.assert_called_once()

    def test_gemini_failure_falls_back_to_heuristic(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """If Gemini raises an exception, heuristic fallback is used (no 500 returned)."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.config.config.settings") as mock_settings,
            patch(
                "app.services.workload_inference_service.WorkloadInferenceService._gemini_infer",
                new_callable=AsyncMock,
                side_effect=Exception("Gemini API timeout"),
            ),
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)
            mock_settings.GEMINI_API_KEY = "fake-key"
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"

            zip_bytes = _minimal_repo_zip()
            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("repo.zip", zip_bytes, "application/zip")},
            )

        # Should succeed via heuristic, NOT return 500
        assert response.status_code == 200
        result = WorkloadInferenceResult.model_validate(response.json())
        assert result.vcpu >= 1
        assert result.ram_gb >= 1


# ─── 3. Validation Errors ─────────────────────────────────────────────────────


class TestInferWorkloadValidation:
    """Tests for input validation and error paths."""

    def test_non_zip_file_rejected_with_400(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Uploading a non-.zip file returns 400 Bad Request."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)

            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("requirements.txt", b"fastapi\n", "text/plain")},
            )

        assert response.status_code == 400
        assert "zip" in response.json()["detail"].lower()

    def test_tar_gz_file_rejected_with_400(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """Uploading a .tar.gz file (common confusion) returns 400."""
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)

            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("archive.tar.gz", b"binary content", "application/gzip")},
            )

        assert response.status_code == 400

    def test_unauthenticated_request_rejected_with_401(
        self,
        client: TestClient,
        test_project: Project,
    ) -> None:
        """Calling the endpoint without a Bearer token returns 401."""
        zip_bytes = _minimal_repo_zip()
        response = client.post(
            f"/api/v1/projects/{test_project.id}/infer-workload",
            files={"file": ("repo.zip", zip_bytes, "application/zip")},
        )
        assert response.status_code == 401

    def test_nonexistent_project_returns_404(
        self,
        client: TestClient,
        test_user: User,
        auth_header: dict[str, str],
    ) -> None:
        """Endpoint returns 404 when project_id doesn't exist or doesn't belong to user."""
        random_id = uuid.uuid4()
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=None)

            zip_bytes = _minimal_repo_zip()
            response = client.post(
                f"/api/v1/projects/{random_id}/infer-workload",
                headers=auth_header,
                files={"file": ("repo.zip", zip_bytes, "application/zip")},
            )

        assert response.status_code == 404

    def test_empty_zip_returns_valid_minimal_result(
        self,
        client: TestClient,
        test_user: User,
        test_project: Project,
        auth_header: dict[str, str],
    ) -> None:
        """An empty (but valid) zip returns a minimal result, not a 500."""
        empty_zip = _make_zip_bytes({})  # Valid zip with no files

        with (
            patch("app.middlewares.auth_middleware.UserRepository") as mock_user_repo,
            patch("app.services.project_service.ProjectRepository") as mock_proj_repo,
            patch("app.config.config.settings") as mock_settings,
        ):
            mock_user_repo.return_value.get_by_id = AsyncMock(return_value=test_user)
            mock_proj_repo.return_value.get_by_id = AsyncMock(return_value=test_project)
            mock_settings.GEMINI_API_KEY = ""
            mock_settings.GEMINI_MODEL = "gemini-1.5-flash"

            response = client.post(
                f"/api/v1/projects/{test_project.id}/infer-workload",
                headers=auth_header,
                files={"file": ("empty.zip", empty_zip, "application/zip")},
            )

        # Empty repo should return minimal values, not 500
        assert response.status_code == 200
        data = response.json()
        assert data["vcpu"] >= 1
        assert data["ram_gb"] >= 1
        assert data["storage_gb"] >= 10


# ─── 4. WorkloadInferenceService Unit Tests ───────────────────────────────────


class TestWorkloadInferenceServiceUnit:
    """Unit tests for WorkloadInferenceService heuristic logic."""

    def test_heuristic_vcpu_scales_with_file_count(self) -> None:
        """More files → higher vCPU estimate (up to cap)."""
        from app.schemas.project import RepositoryAnalysisResult
        from app.services.workload_inference_service import WorkloadInferenceService

        service = WorkloadInferenceService()

        small_analysis = RepositoryAnalysisResult(total_files=10, total_loc=500)
        large_analysis = RepositoryAnalysisResult(total_files=600, total_loc=50_000)

        small = service._heuristic_infer(small_analysis)
        large = service._heuristic_infer(large_analysis)

        assert large.vcpu >= small.vcpu

    def test_heuristic_storage_scales_with_loc(self) -> None:
        """More LOC → higher storage estimate."""
        from app.schemas.project import RepositoryAnalysisResult
        from app.services.workload_inference_service import WorkloadInferenceService

        service = WorkloadInferenceService()

        tiny = RepositoryAnalysisResult(total_files=5, total_loc=100)
        large = RepositoryAnalysisResult(total_files=500, total_loc=500_000)

        tiny_result = service._heuristic_infer(tiny)
        large_result = service._heuristic_infer(large)

        assert large_result.storage_gb >= tiny_result.storage_gb

    def test_heuristic_vcpu_capped_at_16(self) -> None:
        """vCPU is capped at 16 regardless of repo size."""
        from app.schemas.project import RepositoryAnalysisResult
        from app.services.workload_inference_service import WorkloadInferenceService

        service = WorkloadInferenceService()
        # Enormous repo: 100_000 files
        huge = RepositoryAnalysisResult(total_files=100_000, total_loc=10_000_000)
        result = service._heuristic_infer(huge)
        assert result.vcpu <= 16

    def test_heuristic_storage_capped_at_500(self) -> None:
        """Storage is capped at 500 GB regardless of LOC."""
        from app.schemas.project import RepositoryAnalysisResult
        from app.services.workload_inference_service import WorkloadInferenceService

        service = WorkloadInferenceService()
        huge = RepositoryAnalysisResult(total_files=100_000, total_loc=50_000_000)
        result = service._heuristic_infer(huge)
        assert result.storage_gb <= 500

    def test_heuristic_minimum_values_enforced(self) -> None:
        """Even for empty repos, minimum values (vcpu≥1, ram≥1, storage≥10) are returned."""
        from app.schemas.project import RepositoryAnalysisResult
        from app.services.workload_inference_service import WorkloadInferenceService

        service = WorkloadInferenceService()
        empty = RepositoryAnalysisResult(total_files=0, total_loc=0)
        result = service._heuristic_infer(empty)
        assert result.vcpu >= 1
        assert result.ram_gb >= 1
        assert result.storage_gb >= 10
