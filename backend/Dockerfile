# =============================================================================
# Infralytix Backend — Multi-Stage Dockerfile
# =============================================================================
# Stages:
#   base        — Shared Python runtime with uv and venv PATH
#   builder     — Install production Python dependencies into virtualenv
#   development — Hot reload server with dev dependencies
#   production  — Minimal, non-root, hardened production image
# =============================================================================

# ── Base: Shared Python version ───────────────────────────────────────────────
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim AS base

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/app/.venv/bin:$PATH"

# ── Builder: Install all dependencies ────────────────────────────────────────
FROM base AS builder

WORKDIR /app

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency spec first (Docker layer cache optimization)
COPY pyproject.toml uv.lock* ./

# Install production dependencies into virtual environment (/app/.venv)
# --no-install-project avoids requiring source code during dependency caching layer
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

# ── Development: Hot reload with mounted source ───────────────────────────────
FROM base AS development

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency specs and install all dependencies including dev tools
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --extra dev --no-install-project || uv sync --extra dev --no-install-project

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

# Set ownership of /app
RUN chown -R infralytix:infralytix /app

# Copy complete virtual environment from builder stage
COPY --from=builder --chown=infralytix:infralytix /app/.venv /app/.venv

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
