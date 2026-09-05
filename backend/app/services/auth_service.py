"""
Infralytix — Authentication Service.

Encapsulates password hashing (bcrypt via passlib), JWT issuance/decoding
(python-jose), refresh token management, and authentication workflows.
All business logic lives here; endpoints delegate directly to this service.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.config import settings
from app.exceptions.exceptions import ConflictException, UnauthorizedException
from app.logging.logging import get_logger
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserLogin, UserRegister

logger = get_logger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service class handling authentication business logic."""

    def __init__(self) -> None:
        self.secret_key: str = settings.SECRET_KEY
        self.algorithm: str = settings.ALGORITHM
        self.access_token_expire_minutes: int = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days: int = settings.REFRESH_TOKEN_EXPIRE_DAYS

    # ─── Password Cryptography ───────────────────────────────────────────────

    def hash_password(self, plain_password: str) -> str:
        """Hash plaintext password using bcrypt."""
        return pwd_context.hash(plain_password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against stored bcrypt hash."""
        return pwd_context.verify(plain_password, hashed_password)

    # ─── JWT Operations ───────────────────────────────────────────────────────

    def create_access_token(
        self,
        user_id: uuid.UUID,
        role: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """
        Generate a signed JWT access token.

        Claims:
            - sub: string UUID of user
            - role: user role string
            - type: "access"
            - exp: unix timestamp
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=self.access_token_expire_minutes,
            )

        payload: dict[str, Any] = {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "exp": int(expire.timestamp()),
            "iat": int(datetime.now(UTC).timestamp()),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def generate_refresh_token(self) -> tuple[str, str, datetime]:
        """
        Generate an opaque refresh token and its SHA-256 hash.

        Returns:
            (raw_token, token_hash, expires_at)
        """
        raw_token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(days=self.refresh_token_expire_days)
        return raw_token, token_hash, expires_at

    def create_refresh_token(self, user_id: uuid.UUID) -> tuple[str, str, datetime]:
        """Convenience method returning raw token, hash, and expiration."""
        return self.generate_refresh_token()

    def decode_token(self, token: str, expected_type: str = "access") -> dict[str, Any]:
        """
        Decode and validate signature and expiry of a JWT.

        Raises:
            UnauthorizedException if token is expired, malformed, or has incorrect type.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            token_type = payload.get("type")
            if token_type != expected_type:
                raise UnauthorizedException(
                    message=f"Invalid token type: expected '{expected_type}', got '{token_type}'",
                )
            if not payload.get("sub"):
                raise UnauthorizedException(message="Token payload missing subject identifier")
            return payload
        except ExpiredSignatureError as e:
            logger.warning("Token expired", extra={"error": str(e)})
            raise UnauthorizedException(message="Token has expired") from e
        except JWTError as e:
            logger.warning("JWT verification failed", extra={"error": str(e)})
            raise UnauthorizedException(message="Could not validate credentials") from e

    # ─── Auth Workflows ───────────────────────────────────────────────────────

    async def register_user(
        self,
        session: AsyncSession,
        register_data: UserRegister,
    ) -> User:
        """
        Register a new user account.

        Raises:
            ConflictException if email is already taken.
        """
        repo = UserRepository(session)
        existing_user = await repo.get_by_email(register_data.email)
        if existing_user:
            logger.warning(
                "Registration conflict: email already exists",
                extra={"email": register_data.email},
            )
            raise ConflictException(
                message=f"User with email '{register_data.email}' already exists",
            )

        hashed_pw = self.hash_password(register_data.password)
        user = await repo.create(
            name=register_data.name,
            email=register_data.email,
            hashed_password=hashed_pw,
            role=register_data.role,
        )
        await session.commit()
        logger.info(
            "User registered successfully",
            extra={"user_id": str(user.id), "email": user.email},
        )
        return user

    async def authenticate_user(
        self,
        session: AsyncSession,
        login_data: UserLogin,
    ) -> tuple[User, str, str]:
        """
        Verify credentials, issue access token and refresh token.

        Returns:
            (User, access_token, raw_refresh_token)

        Raises:
            UnauthorizedException on invalid credentials or inactive account.
        """
        repo = UserRepository(session)
        user = await repo.get_by_email(login_data.email)

        if not user or not self.verify_password(login_data.password, user.hashed_password):
            logger.warning("Failed login attempt", extra={"email": login_data.email})
            raise UnauthorizedException(message="Incorrect email or password")

        if not user.is_active:
            logger.warning("Inactive account login attempt", extra={"user_id": str(user.id)})
            raise UnauthorizedException(message="User account is deactivated")

        access_token = self.create_access_token(user.id, user.role.value)
        raw_refresh, token_hash, expires_at = self.generate_refresh_token()

        await repo.create_refresh_token(user.id, token_hash, expires_at)
        await session.commit()

        logger.info("User authenticated successfully", extra={"user_id": str(user.id)})
        return user, access_token, raw_refresh

    async def refresh_access_token(
        self,
        session: AsyncSession,
        raw_refresh_token: str,
    ) -> tuple[str, str]:
        """
        Validate refresh token, rotate refresh token, and return new tokens.

        Security:
            Detects token reuse. If a revoked token is presented, all refresh tokens
            for that user are revoked immediately (SDD §5.1 reuse detection).

        Returns:
            (new_access_token, new_raw_refresh_token)
        """
        if not raw_refresh_token:
            raise UnauthorizedException(message="Missing refresh token")

        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        repo = UserRepository(session)
        token_record = await repo.get_refresh_token_by_hash(token_hash)

        if not token_record:
            logger.warning("Unknown refresh token presented")
            raise UnauthorizedException(message="Invalid refresh token")

        # Security check: Token Reuse Detection
        if token_record.revoked_at is not None:
            logger.error(
                "Refresh token reuse detected! Revoking all sessions for user",
                extra={"user_id": str(token_record.user_id)},
            )
            await repo.revoke_all_user_refresh_tokens(token_record.user_id)
            await session.commit()
            raise UnauthorizedException(
                message="Refresh token reuse detected. All sessions revoked. Please log in again.",
            )

        # Check expiration
        now = datetime.now(UTC)
        token_expires = (
            token_record.expires_at
            if token_record.expires_at.tzinfo
            else token_record.expires_at.replace(tzinfo=UTC)
        )
        if token_expires < now:
            logger.warning(
                "Expired refresh token presented",
                extra={"user_id": str(token_record.user_id)},
            )
            raise UnauthorizedException(message="Refresh token has expired. Please log in again.")

        user = await repo.get_by_id(token_record.user_id)
        if not user or not user.is_active:
            raise UnauthorizedException(message="User account not found or inactive")

        # Rotate token: revoke existing, issue new
        await repo.revoke_refresh_token(token_record)
        new_raw, new_hash, new_expires = self.generate_refresh_token()
        await repo.create_refresh_token(user.id, new_hash, new_expires)

        new_access_token = self.create_access_token(user.id, user.role.value)
        await session.commit()

        logger.info("Token refreshed and rotated", extra={"user_id": str(user.id)})
        return new_access_token, new_raw

    async def revoke_refresh_token(
        self,
        session: AsyncSession,
        raw_refresh_token: str | None,
    ) -> None:
        """Revoke a refresh token on logout."""
        if not raw_refresh_token:
            return

        token_hash = hashlib.sha256(raw_refresh_token.encode("utf-8")).hexdigest()
        repo = UserRepository(session)
        token_record = await repo.get_refresh_token_by_hash(token_hash)
        if token_record and token_record.revoked_at is None:
            await repo.revoke_refresh_token(token_record)
            await session.commit()
            logger.info("Refresh token revoked", extra={"user_id": str(token_record.user_id)})


# Module-level singleton
auth_service = AuthService()
