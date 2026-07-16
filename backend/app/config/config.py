"""
Infralytix — Application Configuration.

Uses Pydantic Settings v2 for type-safe, environment-driven configuration.
All settings are loaded from environment variables or a .env file.

Design Decisions:
    - Pydantic BaseSettings validates all config at startup (fail-fast)
    - Computed properties (DATABASE_URL) are derived, never stored in env
    - Settings is a singleton (module-level `settings` instance)
    - No magic strings — every config value is typed and documented
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for the Infralytix backend.

    All fields are loaded from environment variables.
    Field names map directly to env var names (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Extra fields in .env are silently ignored (safe for future additions)
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────────
    APP_NAME: str = Field(default="Infralytix", description="Application name")
    APP_VERSION: str = Field(default="0.1.0", description="Semantic version")
    APP_ENV: Literal["development", "testing", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    DEBUG: bool = Field(default=False, description="Enable debug mode (never True in prod)")

    # ─── Server ───────────────────────────────────────────────────────────────
    HOST: str = Field(default="0.0.0.0", description="Bind address")
    PORT: int = Field(default=8000, ge=1024, le=65535, description="Bind port")

    # ─── Database — MySQL 8.4 ────────────────────────────────────────────────
    DB_HOST: str = Field(default="localhost", description="MySQL host")
    DB_PORT: int = Field(default=3306, ge=1, le=65535, description="MySQL port")
    DB_USER: str = Field(description="MySQL username")
    DB_PASSWORD: str = Field(description="MySQL password")
    DB_NAME: str = Field(default="infralytix_db", description="MySQL database name")

    # Pool settings (tunable per environment)
    DB_POOL_SIZE: int = Field(default=10, ge=1, description="SQLAlchemy connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, description="Max connections above pool size")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=5, description="Pool checkout timeout (seconds)")
    DB_ECHO: bool = Field(default=False, description="Log all SQL queries (dev only)")

    # ─── Security — JWT ───────────────────────────────────────────────────────
    SECRET_KEY: str = Field(
        description="HMAC secret key for JWT signing. Min 64 hex chars.",
        min_length=32,
    )
    ALGORITHM: Literal["HS256", "HS384", "HS512"] = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        ge=5,
        le=1440,
        description="Access token lifetime in minutes",
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7,
        ge=1,
        le=90,
        description="Refresh token lifetime in days",
    )

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        description="Allowed CORS origins",
    )

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60,
        ge=1,
        description="Max requests per IP per minute",
    )

    # ─── Logging ─────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Minimum log level",
    )
    LOG_FORMAT: Literal["json", "text"] = Field(
        default="json",
        description="Log output format (json for production, text for dev)",
    )

    # ─── AI Agents (Sprint 4+) ────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro", description="Gemini model identifier")

    # ─── Computed Properties ──────────────────────────────────────────────────

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Async database URL for SQLAlchemy (aiomysql driver)."""
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync database URL for Alembic migrations (pymysql driver)."""
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """True when running in a production environment."""
        return self.APP_ENV == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_development(self) -> bool:
        """True when running in a development environment."""
        return self.APP_ENV == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached Settings singleton.

    Uses lru_cache to ensure the .env file is only read once.
    Call get_settings.cache_clear() in tests to reset between test runs.
    """
    return Settings()  # type: ignore[call-arg]


# Module-level singleton — use this throughout the application
settings: Settings = get_settings()
