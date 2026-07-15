"""
Tests — Health Check Endpoints.

Sprint 0: Verify that the health and readiness endpoints work correctly.

Test Categories:
  - Response status codes
  - Response body schema validation
  - Service metadata accuracy
  - Response headers (X-Request-ID, X-Process-Time-Ms)
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_application
from app.core.config import get_settings


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def client() -> TestClient:
    """
    Create a synchronous test client for the FastAPI application.

    Using scope="module" so the app is only created once per test file,
    which is faster and reflects real startup behavior.
    """
    app = create_application()
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


# =============================================================================
# Liveness Check Tests — GET /api/v1/health
# =============================================================================

class TestLivenessCheck:
    """Tests for the liveness/health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint must always return HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_response_schema(self, client: TestClient) -> None:
        """Health response must contain all required fields."""
        response = client.get("/api/v1/health")
        body = response.json()

        assert "status" in body
        assert "timestamp" in body
        assert "service" in body

    def test_health_status_is_healthy(self, client: TestClient) -> None:
        """Health status must be 'healthy'."""
        response = client.get("/api/v1/health")
        assert response.json()["status"] == "healthy"

    def test_health_service_metadata(self, client: TestClient) -> None:
        """Service metadata must match application config."""
        settings = get_settings()
        response = client.get("/api/v1/health")
        service = response.json()["service"]

        assert service["name"] == settings.APP_NAME
        assert service["version"] == settings.APP_VERSION
        assert service["environment"] == settings.APP_ENV

    def test_health_timestamp_is_present(self, client: TestClient) -> None:
        """Timestamp must be a non-empty ISO 8601 string."""
        response = client.get("/api/v1/health")
        timestamp = response.json()["timestamp"]

        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
        # ISO 8601 timestamps contain 'T'
        assert "T" in timestamp

    def test_health_content_type_is_json(self, client: TestClient) -> None:
        """Response Content-Type must be application/json."""
        response = client.get("/api/v1/health")
        assert "application/json" in response.headers["content-type"]

    def test_health_includes_request_id_header(self, client: TestClient) -> None:
        """Every response must include an X-Request-ID header."""
        response = client.get("/api/v1/health")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    def test_health_includes_process_time_header(self, client: TestClient) -> None:
        """Every response must include an X-Process-Time-Ms header."""
        response = client.get("/api/v1/health")
        assert "x-process-time-ms" in response.headers

    def test_health_request_ids_are_unique(self, client: TestClient) -> None:
        """Each request must receive a unique request ID."""
        response1 = client.get("/api/v1/health")
        response2 = client.get("/api/v1/health")

        id1 = response1.headers["x-request-id"]
        id2 = response2.headers["x-request-id"]

        assert id1 != id2


# =============================================================================
# Readiness Check Tests — GET /api/v1/health/ready
# =============================================================================

class TestReadinessCheck:
    """Tests for the readiness endpoint."""

    def test_readiness_returns_200(self, client: TestClient) -> None:
        """Readiness endpoint must return HTTP 200 when all checks pass."""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200

    def test_readiness_response_schema(self, client: TestClient) -> None:
        """Readiness response must include status, timestamp, service, and checks."""
        response = client.get("/api/v1/health/ready")
        body = response.json()

        assert "status" in body
        assert "timestamp" in body
        assert "service" in body
        assert "checks" in body

    def test_readiness_checks_is_dict(self, client: TestClient) -> None:
        """The 'checks' field must be a dictionary."""
        response = client.get("/api/v1/health/ready")
        checks = response.json()["checks"]

        assert isinstance(checks, dict)

    def test_readiness_application_check_ok(self, client: TestClient) -> None:
        """Application check must always be 'ok'."""
        response = client.get("/api/v1/health/ready")
        checks = response.json()["checks"]

        assert "application" in checks
        assert checks["application"].startswith("ok")


# =============================================================================
# 404 Behavior Tests
# =============================================================================

class TestNotFoundBehavior:
    """Tests for non-existent routes."""

    def test_unknown_route_returns_404(self, client: TestClient) -> None:
        """Non-existent routes must return HTTP 404."""
        response = client.get("/api/v1/nonexistent")
        assert response.status_code == 404

    def test_root_path_returns_404(self, client: TestClient) -> None:
        """The bare root path returns 404 (API has no root handler)."""
        response = client.get("/")
        assert response.status_code == 404
