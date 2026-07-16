"""
Infralytix — Database Session Management and Dependency Injection.

This module provides the core SQLAlchemy async engine and session factory.
It implements the dependency injection pattern via `get_db()` which FastAPI
routes will use to acquire database sessions.

Design Decisions:
    - Uses AsyncEngine for non-blocking database I/O.
    - Yields `AsyncSession` to routes, automatically closing after the request.
    - Uses SQLAlchemy 2.0 style configuration.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.config import settings
from app.logging.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Engine and Session Factory Initialization
# =============================================================================

# The async engine manages the connection pool to MySQL
engine: AsyncEngine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # Verifies connection health before checkout
)

# The session factory generates new session objects bound to the engine
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=AsyncSession,
)


# =============================================================================
# Dependency Injection
# =============================================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency: Yields an AsyncSession for database operations.

    Usage in routes:
        @router.get("/")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...

    The session is automatically closed when the request lifecycle ends,
    ensuring connections are returned to the pool even if exceptions occur.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
