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

from pydantic import Field, computed_field, field_validator
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
    PORT: int = Field(default=8000, ge=1, le=65535, description="Bind port")

    # ─── Database — MySQL 8.4 (with SQLite sandbox fallback) ─────────────────
    DB_ENGINE: Literal["mysql", "sqlite"] = Field(
        default="mysql",
        description="Database engine ('mysql' or 'sqlite' for local sandboxes)",
    )
    DB_HOST: str = Field(default="localhost", description="MySQL host")
    DB_PORT: int = Field(default=3306, ge=1, le=65535, description="MySQL port")
    DB_USER: str = Field(default="", description="MySQL username")
    DB_PASSWORD: str = Field(default="", description="MySQL password")
    DB_NAME: str = Field(default="infralytix_db", description="MySQL database name")
    DATABASE_URL_ENV: str | None = Field(
        default=None,
        alias="DATABASE_URL",
        description="Direct database URL override from environment (e.g. Render, Railway)",
    )

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

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if v_str.startswith("[") and v_str.endswith("]"):
                import json

                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed]
                except (ValueError, TypeError):
                    return [i.strip() for i in v_str.strip("[]").split(",") if i.strip()]
            return [i.strip() for i in v_str.split(",") if i.strip()]
        if isinstance(v, list):
            return [str(i).strip() for i in v]
        return [str(v)]

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

    # ─── Storage / File Uploads ───────────────────────────────────────────────
    UPLOAD_DIR: str = Field(
        default="uploads",
        description="Directory for storing uploaded repository archives",
    )

    # ─── AI Agents (Sprint 4+) ────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    GEMINI_MODEL: str = Field(default="gemini-1.5-pro", description="Gemini model identifier")
    GCP_API_KEY: str = Field(default="", description="Google Cloud Billing Catalog API key")

    # ─── Computed Properties ──────────────────────────────────────────────────

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Async database URL for SQLAlchemy (aiomysql or aiosqlite driver)."""
        if self.DATABASE_URL_ENV:
            url = self.DATABASE_URL_ENV.strip()
            if url.startswith("mysql://"):
                url = url.replace("mysql://", "mysql+aiomysql://", 1)
            elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
                url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            return url
        if self.DB_ENGINE == "sqlite":
            return f"sqlite+aiosqlite:///{self.DB_NAME}.db"
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync database URL for Alembic migrations (pymysql or sqlite driver)."""
        if self.DATABASE_URL_ENV:
            url = self.DATABASE_URL_ENV.strip()
            if url.startswith("mysql+aiomysql://"):
                url = url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)
            elif url.startswith("mysql://"):
                url = url.replace("mysql://", "mysql+pymysql://", 1)
            elif url.startswith("sqlite+aiosqlite://"):
                url = url.replace("sqlite+aiosqlite://", "sqlite://", 1)
            return url
        if self.DB_ENGINE == "sqlite":
            return f"sqlite:///{self.DB_NAME}.db"
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
