"""
Alembic Migration Environment — Infralytix.

This env.py is the bridge between Alembic and SQLAlchemy.
It reads the database URL from the application's Settings class
(instead of alembic.ini) so there is a single source of truth.

Two run modes:
  - offline: generates SQL scripts without a DB connection
  - online:  connects to MySQL and applies migrations directly
"""

from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import the Settings singleton to get the database URL
from app.core.config import settings

# =============================================================================
# Alembic Config Object
# =============================================================================
config = context.config

# Configure Python logging from the alembic.ini [logging] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# =============================================================================
# Override sqlalchemy.url from environment variables
# =============================================================================
# This ensures migrations always use the same DB URL as the application.
# The synchronous URL (pymysql) is used here because Alembic is synchronous.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# =============================================================================
# Target Metadata
# =============================================================================
# Import all models here so that Alembic can detect schema changes.
# Models will be imported in Sprint 2 when we define them.
# Example: from app.models.user import User  # noqa: F401

# For autogenerate support, target_metadata must be set to your Base.metadata.
# This will be wired up in Sprint 2.
try:
    from app.db.base import Base  # noqa: F401
    target_metadata = Base.metadata
except ImportError:
    # Sprint 0: DB models not yet created
    logger.warning("Database models not yet available — running without autogenerate support")
    target_metadata = None

# =============================================================================
# Offline Migration
# =============================================================================

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generates SQL without connecting to DB).

    Useful for:
    - Previewing what migrations will do: alembic upgrade head --sql
    - Generating SQL to run on a managed database (RDS, Cloud SQL)
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # MySQL-specific: use ALTER TABLE for column changes
        render_as_batch=False,
    )

    with context.begin_transaction():
        context.run_migrations()


# =============================================================================
# Online Migration
# =============================================================================

def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connects to MySQL and applies changes).

    This is the default mode used by: alembic upgrade head
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Use NullPool — we don't need connection pooling for migrations
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare column types for stricter change detection
            compare_type=True,
            # Compare server defaults (e.g., DEFAULT NOW())
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# =============================================================================
# Entry Point
# =============================================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
