"""
Infralytix Backend — Application Entry Point.

This module uses the Application Factory pattern:
  - `create_application()` builds and configures the FastAPI app
  - `app` is the module-level ASGI application instance
  - Uvicorn runs: uvicorn app.main:app

Lifespan events (startup/shutdown) are handled via the @asynccontextmanager
pattern (FastAPI's recommended approach since 0.95+).

Middleware stack (applied in reverse order — last added = outermost):
  1. RequestIDMiddleware     — Assigns unique ID to every request
  2. CORSMiddleware          — Cross-origin resource sharing
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import get_logger, setup_logging
from app.api.v1.router import v1_router

logger = get_logger(__name__)


# =============================================================================
# Lifespan — Startup & Shutdown Events
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application startup and shutdown events.

    Startup:
        - Configure structured logging
        - Log environment info
        - (Sprint 2) Verify database connectivity
        - (Sprint 7) Initialize agent worker pool

    Shutdown:
        - Gracefully close database connections
        - Flush any pending log buffers
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_format=settings.LOG_FORMAT,
    )

    logger.info(
        "Infralytix backend starting",
        extra={
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "debug": settings.DEBUG,
        },
    )

    # Database connection pool will be initialized here in Sprint 2
    # AI agent registry will be initialized here in Sprint 7

    logger.info("Infralytix backend ready to accept requests")

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Infralytix backend shutting down gracefully")

    # Database pool disposal will be added here in Sprint 2


# =============================================================================
# Middleware
# =============================================================================

async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """
    Assign a unique request ID to every incoming request.

    The request ID is:
      - Stored on request.state.request_id
      - Included in all log lines (via exception handlers)
      - Returned in the X-Request-ID response header

    This makes distributed tracing and log correlation trivial.
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()
    response = await call_next(request)
    process_time_ms = (time.perf_counter() - start_time) * 1000

    # Attach tracing headers to every response
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = f"{process_time_ms:.2f}"

    # Log every request at DEBUG level (INFO would be too noisy in production)
    logger.debug(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(process_time_ms, 2),
        },
    )

    return response


# =============================================================================
# Application Factory
# =============================================================================

def create_application() -> FastAPI:
    """
    Build and configure the FastAPI application.

    This factory pattern keeps the module-level `app` clean and
    makes the application fully testable (tests can call create_application()
    with different settings injected).

    Returns:
        A fully configured FastAPI ASGI application.
    """
    application = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="AI-Powered Developer Infrastructure Operating System",
        # Only expose API docs in non-production environments
        openapi_url="/api/v1/openapi.json" if not settings.is_production else None,
        docs_url="/api/v1/docs" if not settings.is_production else None,
        redoc_url="/api/v1/redoc" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ── Register Exception Handlers ───────────────────────────────────────────
    register_exception_handlers(application)

    # ── Register Middleware ───────────────────────────────────────────────────
    # Order matters: last registered = outermost (first to process requests)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Process-Time-Ms"],
    )

    application.middleware("http")(request_id_middleware)

    # ── Register Routers ──────────────────────────────────────────────────────
    application.include_router(v1_router, prefix="/api/v1")

    return application


# =============================================================================
# ASGI Application Instance
# =============================================================================
# Uvicorn entry point: uvicorn app.main:app
app = create_application()
