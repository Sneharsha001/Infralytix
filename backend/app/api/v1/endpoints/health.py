"""
Infralytix — Health Check Endpoints.

Provides two endpoints:
  GET /api/v1/health         — Liveness check (is the process alive?)
  GET /api/v1/health/ready   — Readiness check (is it ready to serve traffic?)

These endpoints are consumed by:
  - Docker HEALTHCHECK instruction
  - Kubernetes liveness/readiness probes
  - Load balancer health checks
  - GitHub Actions CI verification

Design:
  - No authentication required (health checks must be publicly accessible)
  - Returns structured JSON matching the health check standard
  - The readiness check will verify database connectivity (Sprint 2)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Response Schemas
# =============================================================================

class ServiceInfo(BaseModel):
    """Information about the running service."""

    name: str = Field(description="Service name")
    version: str = Field(description="Service version")
    environment: str = Field(description="Deployment environment")


class HealthResponse(BaseModel):
    """Standard health check response body."""

    status: str = Field(description="Health status: healthy | degraded | unhealthy")
    timestamp: str = Field(description="ISO 8601 UTC timestamp of the check")
    service: ServiceInfo = Field(description="Service metadata")


class ReadinessResponse(BaseModel):
    """Readiness check response — includes dependency status."""

    status: str = Field(description="Readiness status: ready | not_ready")
    timestamp: str = Field(description="ISO 8601 UTC timestamp of the check")
    service: ServiceInfo = Field(description="Service metadata")
    checks: dict[str, str] = Field(description="Status of each dependency")


# =============================================================================
# Endpoints
# =============================================================================

@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness Check",
    description=(
        "Returns 200 if the application process is alive and has completed startup. "
        "Used by Docker and load balancers to decide whether to restart the container."
    ),
    responses={
        200: {"description": "Service is alive"},
    },
)
async def health_check() -> HealthResponse:
    """
    Liveness check — answers: 'Is the process running?'

    This endpoint should ALWAYS return 200 as long as the FastAPI
    process is running. If it fails, the container should be restarted.
    """
    logger.debug("Liveness check requested")

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(UTC).isoformat(),
        service=ServiceInfo(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.APP_ENV,
        ),
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness Check",
    description=(
        "Returns 200 if the service is ready to handle traffic. "
        "Checks all critical dependencies (database, etc.). "
        "Returns 503 if any critical dependency is unavailable."
    ),
    responses={
        200: {"description": "Service is ready"},
        503: {"description": "Service is not ready — a dependency is unavailable"},
    },
)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check — answers: 'Is the service ready to serve requests?'

    Unlike the liveness check, this verifies connectivity to critical
    dependencies. If the database is unreachable, this returns 503.

    Sprint 2 will add real database connectivity verification here.
    """
    logger.debug("Readiness check requested")

    # ── Dependency Checks ─────────────────────────────────────────────────────
    # TODO (Sprint 2): Add actual database ping
    checks: dict[str, str] = {
        "database": "ok (not yet verified — Sprint 2)",
        "application": "ok",
    }

    # Determine overall status
    all_ok = all(v.startswith("ok") for v in checks.values())
    overall_status = "ready" if all_ok else "not_ready"

    return ReadinessResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        service=ServiceInfo(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            environment=settings.APP_ENV,
        ),
        checks=checks,
    )
