"""Tests -- AI Agent Orchestration Endpoints (Phase 2)."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.agent_run import AgentRun, AgentRunStatus
from app.models.project import Project
from app.models.user import User, UserRole
from app.schemas.project import AIInsightResult
from app.services.ai_agent_service import GeminiAgentService
from app.services.auth_service import auth_service


@pytest.fixture
def user_a():
    return User(
        id=uuid.uuid4(),
        name="Alice",
        email="alice@test.io",
        hashed_password="x",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def user_b():
    return User(
        id=uuid.uuid4(),
        name="Bob",
        email="bob@test.io",
        hashed_password="x",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def auth_header(user_a):
    token = auth_service.create_access_token(user_a.id, user_a.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_project(user_a):
    return Project(
        id=uuid.uuid4(),
        user_id=user_a.id,
        name="AI Gateway",
        description="ML API",
        repo_name="ai-gw",
        archive_filename="repo.zip",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


SAMPLE_REPO_ANALYSIS = {
    "total_files": 42,
    "total_loc": 8500,
    "primary_language": "Python",
    "languages": [
        {
            "language": "Python",
            "extension": ".py",
            "file_count": 38,
            "loc": 8000,
            "percentage": 94.1,
        }
    ],
    "dependency_files": [
        {
            "filename": "requirements.txt",
            "package_manager": "pip",
            "dependencies": ["fastapi", "pytest"],
        }
    ],
    "detected_frameworks": ["FastAPI", "pytest"],
}
GEMINI_OUTPUT = {
    "summary": "Mock AI insight.",
    "health_score": {
        "overall": 72,
        "maintainability": 75,
        "complexity": 70,
        "test_coverage_estimate": 65,
        "documentation": 55,
    },
    "insights": [],
    "tech_debt_indicators": [],
    "recommended_next_steps": [],
}


def _repo_run(proj):
    r = AgentRun(
        id=uuid.uuid4(),
        project_id=proj.id,
        agent_type="repository",
        status=AgentRunStatus.COMPLETED,
        output_data=SAMPLE_REPO_ANALYSIS,
        error_message=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    r.project = proj
    return r


def _ai_run(proj):
    r = AgentRun(
        id=uuid.uuid4(),
        project_id=proj.id,
        agent_type="gemini",
        status=AgentRunStatus.COMPLETED,
        output_data=GEMINI_OUTPUT,
        error_message=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    r.project = proj
    return r


class TestAuthGuards:
    def test_analyze_401(self, client: TestClient):
        assert client.post(f"/api/v1/projects/{uuid.uuid4()}/analyze").status_code == 401

    def test_analysis_401(self, client: TestClient):
        assert client.get(f"/api/v1/projects/{uuid.uuid4()}/analysis").status_code == 401


class TestOwnership:
    def _fp(self, user_b):
        return Project(
            id=uuid.uuid4(),
            user_id=user_b.id,
            name="B",
            description=None,
            repo_name=None,
            archive_filename=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def test_analyze_wrong_owner_404(self, client, user_a, user_b, auth_header):
        fp = self._fp(user_b)
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as ur,
            patch("app.api.v1.endpoints.agents.ProjectRepository") as pr,
        ):
            ur.return_value.get_by_id = AsyncMock(return_value=user_a)
            pr.return_value.get_by_id = AsyncMock(return_value=fp)
            assert (
                client.post(f"/api/v1/projects/{fp.id}/analyze", headers=auth_header).status_code
                == 404
            )

    def test_analysis_wrong_owner_404(self, client, user_a, user_b, auth_header):
        fp = self._fp(user_b)
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as ur,
            patch("app.api.v1.endpoints.agents.ProjectRepository") as pr,
        ):
            ur.return_value.get_by_id = AsyncMock(return_value=user_a)
            pr.return_value.get_by_id = AsyncMock(return_value=fp)
            assert (
                client.get(f"/api/v1/projects/{fp.id}/analysis", headers=auth_header).status_code
                == 404
            )


class TestTriggerAnalysis:
    def test_422_when_no_phase1_run(self, client, user_a, sample_project, auth_header):
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as ur,
            patch("app.api.v1.endpoints.agents.ProjectRepository") as pr,
            patch("app.api.v1.endpoints.agents.AgentRunRepository") as rr,
        ):
            ur.return_value.get_by_id = AsyncMock(return_value=user_a)
            pr.return_value.get_by_id = AsyncMock(return_value=sample_project)
            rr.return_value.get_latest_by_type = AsyncMock(return_value=None)
            r = client.post(f"/api/v1/projects/{sample_project.id}/analyze", headers=auth_header)
        assert r.status_code == 422
        assert "upload" in r.json()["detail"].lower()

    def test_success_returns_completed_run(self, client, user_a, sample_project, auth_header):
        ai = _ai_run(sample_project)
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as ur,
            patch("app.api.v1.endpoints.agents.ProjectRepository") as pr,
            patch("app.api.v1.endpoints.agents.AgentRunRepository") as rr,
            patch("app.api.v1.endpoints.agents.GeminiAgentService") as sc,
        ):
            ur.return_value.get_by_id = AsyncMock(return_value=user_a)
            pr.return_value.get_by_id = AsyncMock(return_value=sample_project)
            rr.return_value.get_latest_by_type = AsyncMock(return_value=_repo_run(sample_project))
            rr.return_value.create = AsyncMock(return_value=ai)
            rr.return_value.update_status = AsyncMock(return_value=ai)
            svc = MagicMock()
            svc.analyze = AsyncMock(return_value=AIInsightResult.model_validate(GEMINI_OUTPUT))
            sc.return_value = svc
            r = client.post(f"/api/v1/projects/{sample_project.id}/analyze", headers=auth_header)
        assert r.status_code == 200
        d = r.json()
        assert d["agent_type"] == "gemini"
        assert d["status"] == "completed"
        assert "health_score" in d["output_data"]


class TestGetAnalysis:
    def test_404_when_no_run(self, client, user_a, sample_project, auth_header):
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as ur,
            patch("app.api.v1.endpoints.agents.ProjectRepository") as pr,
            patch("app.api.v1.endpoints.agents.AgentRunRepository") as rr,
        ):
            ur.return_value.get_by_id = AsyncMock(return_value=user_a)
            pr.return_value.get_by_id = AsyncMock(return_value=sample_project)
            rr.return_value.get_latest_by_type = AsyncMock(return_value=None)
            assert (
                client.get(
                    f"/api/v1/projects/{sample_project.id}/analysis", headers=auth_header
                ).status_code
                == 404
            )

    def test_returns_latest_run(self, client, user_a, sample_project, auth_header):
        ai = _ai_run(sample_project)
        with (
            patch("app.middlewares.auth_middleware.UserRepository") as ur,
            patch("app.api.v1.endpoints.agents.ProjectRepository") as pr,
            patch("app.api.v1.endpoints.agents.AgentRunRepository") as rr,
        ):
            ur.return_value.get_by_id = AsyncMock(return_value=user_a)
            pr.return_value.get_by_id = AsyncMock(return_value=sample_project)
            rr.return_value.get_latest_by_type = AsyncMock(return_value=ai)
            r = client.get(f"/api/v1/projects/{sample_project.id}/analysis", headers=auth_header)
        assert r.status_code == 200
        d = r.json()
        assert d["agent_type"] == "gemini"
        assert d["output_data"]["health_score"]["overall"] == 72


class TestGeminiServiceMock:
    def test_valid_result(self, sample_project):
        r = asyncio.run(GeminiAgentService().analyze(sample_project, SAMPLE_REPO_ANALYSIS))
        assert isinstance(r, AIInsightResult)
        assert 0 <= r.health_score.overall <= 100
        assert len(r.insights) >= 2

    def test_detects_test_framework(self, sample_project):
        r = asyncio.run(GeminiAgentService().analyze(sample_project, SAMPLE_REPO_ANALYSIS))
        assert r.health_score.test_coverage_estimate == 65

    def test_penalises_missing_tests(self, sample_project):
        no_tests = {**SAMPLE_REPO_ANALYSIS, "detected_frameworks": ["Django"]}
        r = asyncio.run(GeminiAgentService().analyze(sample_project, no_tests))
        assert r.health_score.test_coverage_estimate == 20
        assert any(i.severity == "critical" for i in r.insights)

    def test_handles_empty_analysis(self, sample_project):
        r = asyncio.run(
            GeminiAgentService().analyze(sample_project, {"total_files": 0, "total_loc": 0})
        )
        assert isinstance(r, AIInsightResult)

    def test_all_scores_in_range(self, sample_project):
        r = asyncio.run(GeminiAgentService().analyze(sample_project, SAMPLE_REPO_ANALYSIS))
        s = r.health_score
        for f in (
            "overall",
            "maintainability",
            "complexity",
            "test_coverage_estimate",
            "documentation",
        ):
            v = getattr(s, f)
            assert 0 <= v <= 100, f"{f}={v}"
