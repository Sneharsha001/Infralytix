# =============================================================================
# Infralytix Backend — Multi-Stage Dockerfile
# =============================================================================
# Stages:
#   builder     — Install Python dependencies
#   development — Hot reload server (bind mount source)
#   production  — Minimal, non-root, hardened image
# =============================================================================

# ── Base: Shared Python version ───────────────────────────────────────────────
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# ── Builder: Install all dependencies ────────────────────────────────────────
FROM base AS builder

WORKDIR /build

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency spec first (Docker layer cache optimization)
COPY pyproject.toml .

# Install production dependencies only
# --system: install into system Python (not venv) for cleaner COPY in next stage
RUN uv pip install --system --no-cache \
    fastapi \
    "uvicorn[standard]" \
    "pydantic>=2.9.0,<3.0" \
    "pydantic-settings>=2.6.0,<3.0" \
    "sqlalchemy>=2.0.36,<3.0" \
    "alembic>=1.14.0,<2.0" \
    "aiomysql>=0.2.0,<0.3" \
    "pymysql>=1.1.0,<2.0" \
    "cryptography>=43.0.0" \
    "python-jose[cryptography]>=3.3.0,<4.0" \
    "passlib[bcrypt]>=1.7.4,<2.0" \
    "python-multipart>=0.0.12,<0.1" \
    "httpx>=0.28.0,<0.29"

# ── Development: Hot reload with mounted source ───────────────────────────────
FROM base AS development

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml and install all deps including dev
COPY pyproject.toml .
RUN uv pip install --system --no-cache -e ".[dev]"

# Note: Source code is mounted via docker-compose volume in dev mode
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Production: Minimal, hardened, non-root ───────────────────────────────────
FROM base AS production

# Install curl for HEALTHCHECK instruction
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd --gid 1001 infralytix && \
    useradd \
        --uid 1001 \
        --gid infralytix \
        --no-create-home \
        --shell /bin/false \
        infralytix

WORKDIR /app

# Copy only what is needed from builder
# Python standard library is already in the base image
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages

# Copy CLI tools installed by packages (uvicorn, alembic)
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn
COPY --from=builder /usr/local/bin/alembic /usr/local/bin/alembic

# Copy application source with correct ownership
COPY --chown=infralytix:infralytix app/ ./app/
COPY --chown=infralytix:infralytix alembic/ ./alembic/
COPY --chown=infralytix:infralytix alembic.ini ./alembic.ini

# Switch to non-root user
USER infralytix

EXPOSE 8000

# Docker health check — polls the health endpoint every 30s
HEALTHCHECK \
    --interval=30s \
    --timeout=10s \
    --start-period=15s \
    --retries=3 \
    CMD curl --fail --silent http://localhost:8000/api/v1/health || exit 1

# Use exec form (not shell form) for proper signal handling (SIGTERM on shutdown)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--no-access-log", \
     "--workers", "1"]
