"""
Infralytix — Custom Exceptions and Exception Handlers.

Defines a hierarchy of application exceptions and registers FastAPI
exception handlers that convert them to consistent JSON error responses.

Error Response Schema (all errors):
    {
        "error": {
            "code": "RESOURCE_NOT_FOUND",
            "message": "User with id 42 was not found.",
            "details": null,
            "request_id": "abc123"
        }
    }

Design Decisions:
    - All app exceptions inherit from InfralytixBaseException
    - HTTP status codes are attached to the exception class, not the handler
    - Error codes are SCREAMING_SNAKE_CASE strings (not HTTP status integers)
    - This makes frontend error handling deterministic and refactorable
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


# =============================================================================
# Exception Hierarchy
# =============================================================================

class InfralytixBaseException(Exception):
    """
    Root exception for all Infralytix-specific errors.

    All custom exceptions MUST inherit from this class.
    The exception handler maps HTTP status code from the exception class.
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundException(InfralytixBaseException):
    """Resource does not exist."""
    http_status = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"


class ConflictException(InfralytixBaseException):
    """Resource already exists or violates a uniqueness constraint."""
    http_status = status.HTTP_409_CONFLICT
    error_code = "RESOURCE_CONFLICT"


class UnauthorizedException(InfralytixBaseException):
    """Authentication credentials are missing or invalid."""
    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class ForbiddenException(InfralytixBaseException):
    """Authenticated user lacks permission for this action."""
    http_status = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class BadRequestException(InfralytixBaseException):
    """Client sent a malformed or logically invalid request."""
    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"


class UnprocessableEntityException(InfralytixBaseException):
    """Request is syntactically valid but semantically incorrect."""
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "UNPROCESSABLE_ENTITY"


class ServiceUnavailableException(InfralytixBaseException):
    """A downstream service (database, AI API) is unavailable."""
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "SERVICE_UNAVAILABLE"


class RateLimitExceededException(InfralytixBaseException):
    """Client has exceeded the configured rate limit."""
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"


class AgentExecutionException(InfralytixBaseException):
    """An AI agent failed during execution."""
    http_status = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "AGENT_EXECUTION_FAILED"


# =============================================================================
# Response Builder
# =============================================================================

def _build_error_response(
    request: Request,
    status_code: int,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build a standardised JSON error response."""
    request_id: str = getattr(request.state, "request_id", "unknown")

    body: dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "request_id": request_id,
        }
    }

    return JSONResponse(status_code=status_code, content=body)


# =============================================================================
# Exception Handlers
# =============================================================================

async def infralytix_exception_handler(
    request: Request,
    exc: InfralytixBaseException,
) -> JSONResponse:
    """Handle all InfralytixBaseException subclasses."""
    # Log at WARNING for client errors, ERROR for server errors
    log_fn = logger.error if exc.http_status >= 500 else logger.warning
    log_fn(
        "Application exception",
        extra={
            "error_code": exc.error_code,
            "message": exc.message,
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=exc.http_status >= 500,
    )

    return _build_error_response(
        request=request,
        status_code=exc.http_status,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors (422 Unprocessable Entity).

    Transforms Pydantic's verbose error format into our standardised schema.
    """
    logger.warning(
        "Request validation failed",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": exc.errors(),
        },
    )

    # Simplify the Pydantic error list for client consumption
    simplified_errors = [
        {
            "field": " → ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]

    return _build_error_response(
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message="Request validation failed. Check the 'details' field for field-level errors.",
        details={"errors": simplified_errors},
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catch-all handler for any unhandled exception.

    Logs the full traceback but returns a generic message to the client
    to avoid leaking internal implementation details.
    """
    logger.error(
        "Unhandled exception",
        extra={
            "path": request.url.path,
            "method": request.method,
        },
        exc_info=exc,
    )

    return _build_error_response(
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. Our team has been notified.",
    )


# =============================================================================
# Registration
# =============================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers on the FastAPI application.

    Called once during app factory creation in main.py.

    Args:
        app: The FastAPI application instance.
    """
    app.add_exception_handler(
        InfralytixBaseException,
        infralytix_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,  # type: ignore[arg-type]
    )
    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,  # type: ignore[arg-type]
    )
