"""
Infralytix Backend — Pytest Configuration and Fixtures.

This conftest.py is the root configuration for the entire test suite.

Responsibilities:
  1. Set required environment variables BEFORE any app module imports
     (Pydantic Settings validates at import time, so env vars must be set first)
  2. Clear the Settings lru_cache between tests to ensure isolation
  3. Provide shared fixtures available to all test modules

Design:
  - Environment is set via os.environ, NOT a .env file
  - This makes CI configuration explicit and portable
  - The Settings cache is cleared after each test session
"""

from __future__ import annotations

import os

import pytest

# =============================================================================
# Set required environment variables BEFORE any app imports
# =============================================================================
# These must be set at module level (before collect phase) because
# Pydantic Settings.model_config reads env at class instantiation time.
#
# In CI, these are set via the GitHub Actions workflow env: block.
# Locally, these override the absence of a .env file in the test environment.

os.environ.setdefault("APP_ENV", "testing")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DB_HOST", "127.0.0.1")
os.environ.setdefault("DB_PORT", "3306")
os.environ.setdefault("DB_NAME", "infralytix_test")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "testpassword")
os.environ.setdefault("MYSQL_ROOT_PASSWORD", "testroot")
os.environ.setdefault(
    "SECRET_KEY",
    "test-secret-key-64-chars-minimum-not-for-production-use-only-abc123def",
)
os.environ.setdefault("LOG_FORMAT", "text")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(autouse=True, scope="session")
def clear_settings_cache() -> None:
    """
    Clear the Settings lru_cache after the entire test session.

    This ensures that if tests modify environment variables,
    subsequent test runs start fresh.
    """
    yield
    # Import here (after env vars are set) to avoid circular import
    from app.core.config import get_settings
    get_settings.cache_clear()
