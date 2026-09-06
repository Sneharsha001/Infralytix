"""
Tests — Authentication & RBAC (Sprint 2/3).

Verifies:
  - User Registration (success, duplicate email, validation errors)
  - User Authentication / Login (success, incorrect password, inactive user)
  - Token Refresh (successful rotation, missing cookie, reuse detection)
  - Protected route access (with and without valid Bearer token)
  - Role-Based Access Control (RBAC 403 vs 200)
  - Logout (cookie invalidation)
All database interactions are mocked so tests run without live MySQL.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.services.auth_service import auth_service

# Test Fixtures & In-Memory State
# Note: client and mock_db_session are provided by conftest.py
# =============================================================================


@pytest.fixture
def sample_user() -> User:
    """Standard user fixture."""
    return User(
        id=uuid.uuid4(),
        name="John Doe",
        email="john@example.com",
        hashed_password=auth_service.hash_password("SuperSecret123!"),
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def admin_user() -> User:
    """Administrator user fixture."""
    return User(
        id=uuid.uuid4(),
        name="Admin User",
        email="admin@example.com",
        hashed_password=auth_service.hash_password("AdminSecret123!"),
        role=UserRole.ADMINISTRATOR,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


# =============================================================================
# 1. Registration Tests
# =============================================================================

class TestUserRegistration:
    """Tests for POST /api/v1/auth/register."""

    def test_register_success(self, client: TestClient) -> None:
        """New user can register successfully; password hash is never returned."""
        with (
            patch("app.services.auth_service.UserRepository") as mock_repo_cls,
        ):
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_email = AsyncMock(return_value=None)

            created_id = uuid.uuid4()
            created_user = User(
                id=created_id,
                name="Alice Wonder",
                email="alice@example.com",
                hashed_password=auth_service.hash_password("SecurePassword99!"),
                role=UserRole.USER,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            mock_repo.create = AsyncMock(return_value=created_user)

            response = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Alice Wonder",
                    "email": "alice@example.com",
                    "password": "SecurePassword99!",
                },
            )

            assert response.status_code == 201
            body = response.json()
            assert body["email"] == "alice@example.com"
            assert body["name"] == "Alice Wonder"
            assert body["role"] == "user"
            assert "hashed_password" not in body
            assert "password" not in body

    def test_register_duplicate_email(self, client: TestClient, sample_user: User) -> None:
        """Registering with an already existing email returns 409 Conflict."""
        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_email = AsyncMock(return_value=sample_user)

            response = client.post(
                "/api/v1/auth/register",
                json={
                    "name": "Another Name",
                    "email": sample_user.email,
                    "password": "Password1234!",
                },
            )

            assert response.status_code == 409
            body = response.json()
            assert "already exists" in body["error"]["message"].lower()

    def test_register_validation_short_password(self, client: TestClient) -> None:
        """Passwords shorter than 8 characters fail validation with 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Short Pass",
                "email": "short@example.com",
                "password": "short",
            },
        )
        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient) -> None:
        """Invalid email addresses fail validation with 422."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "name": "Bad Email",
                "email": "not-an-email",
                "password": "ValidPassword123!",
            },
        )
        assert response.status_code == 422


# =============================================================================
# 2. Login Tests
# =============================================================================

class TestUserLogin:
    """Tests for POST /api/v1/auth/login."""

    def test_login_success(self, client: TestClient, sample_user: User) -> None:
        """Valid credentials return JWT access token and set HttpOnly refresh cookie."""
        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_email = AsyncMock(return_value=sample_user)
            mock_repo.create_refresh_token = AsyncMock()

            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": sample_user.email,
                    "password": "SuperSecret123!",
                },
            )

            assert response.status_code == 200
            body = response.json()
            assert "access_token" in body
            assert body["token_type"] == "bearer"
            assert body["expires_in"] > 0

            # Verify HttpOnly cookie
            assert "refresh_token" in response.cookies
            set_cookie_header = response.headers.get("set-cookie", "")
            assert "HttpOnly" in set_cookie_header

    def test_login_wrong_password(self, client: TestClient, sample_user: User) -> None:
        """Incorrect password returns 401 Unauthorized."""
        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_email = AsyncMock(return_value=sample_user)

            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": sample_user.email,
                    "password": "WrongPassword!",
                },
            )

            assert response.status_code == 401
            assert "incorrect email or password" in response.json()["error"]["message"].lower()

    def test_login_nonexistent_email(self, client: TestClient) -> None:
        """Unknown email returns 401 Unauthorized."""
        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_email = AsyncMock(return_value=None)

            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": "ghost@example.com",
                    "password": "AnyPassword123!",
                },
            )

            assert response.status_code == 401

    def test_login_inactive_account(self, client: TestClient, sample_user: User) -> None:
        """Deactivated account cannot log in and returns 401 Unauthorized."""
        sample_user.is_active = False
        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_email = AsyncMock(return_value=sample_user)

            response = client.post(
                "/api/v1/auth/login",
                json={
                    "email": sample_user.email,
                    "password": "SuperSecret123!",
                },
            )

            assert response.status_code == 401
            assert "deactivated" in response.json()["error"]["message"].lower()


# =============================================================================
# 3. Token Refresh Tests
# =============================================================================

class TestTokenRefresh:
    """Tests for POST /api/v1/auth/refresh."""

    def test_refresh_token_success(self, client: TestClient, sample_user: User) -> None:
        """Valid refresh cookie rotates token and issues new access token."""
        raw_token, token_hash, expires_at = auth_service.generate_refresh_token()
        existing_record = RefreshToken(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )

        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_refresh_token_by_hash = AsyncMock(return_value=existing_record)
            mock_repo.get_by_id = AsyncMock(return_value=sample_user)
            mock_repo.revoke_refresh_token = AsyncMock()
            mock_repo.create_refresh_token = AsyncMock()

            response = client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": raw_token},
            )

            assert response.status_code == 200
            body = response.json()
            assert "access_token" in body
            assert "refresh_token" in response.cookies
            # Assert that old token was marked revoked
            mock_repo.revoke_refresh_token.assert_called_once_with(existing_record)

    def test_refresh_token_missing(self, client: TestClient) -> None:
        """Calling /refresh without cookie or body returns 401."""
        response = client.post("/api/v1/auth/refresh")
        assert response.status_code == 401

    def test_refresh_token_reuse_detection(self, client: TestClient, sample_user: User) -> None:
        """Presenting an already-revoked refresh token triggers session revocation (401)."""
        raw_token, token_hash, expires_at = auth_service.generate_refresh_token()
        already_revoked = RefreshToken(
            id=uuid.uuid4(),
            user_id=sample_user.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=datetime.now(UTC) - timedelta(hours=1),
        )

        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_refresh_token_by_hash = AsyncMock(return_value=already_revoked)
            mock_repo.revoke_all_user_refresh_tokens = AsyncMock()

            response = client.post(
                "/api/v1/auth/refresh",
                cookies={"refresh_token": raw_token},
            )

            assert response.status_code == 401
            assert "reuse detected" in response.json()["error"]["message"].lower()
            mock_repo.revoke_all_user_refresh_tokens.assert_called_once_with(sample_user.id)


# =============================================================================
# 4. Protected Route & RBAC Tests
# =============================================================================

class TestProtectedRoutesAndRBAC:
    """Tests for protected routes and Role-Based Access Control."""

    def test_get_me_unauthenticated(self, client: TestClient) -> None:
        """Accessing /me without Authorization header returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient) -> None:
        """Accessing /me with bogus token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.payload"},
        )
        assert response.status_code == 401

    def test_get_me_authenticated(self, client: TestClient, sample_user: User) -> None:
        """Accessing /me with valid token returns user profile."""
        token = auth_service.create_access_token(sample_user.id, sample_user.role.value)

        with patch("app.middlewares.auth_middleware.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=sample_user)

            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            body = response.json()
            assert body["email"] == sample_user.email
            assert body["name"] == sample_user.name
            assert "hashed_password" not in body

    def test_admin_route_as_regular_user_forbidden(
        self, client: TestClient, sample_user: User
    ) -> None:
        """Regular user accessing admin route receives 403 Forbidden."""
        token = auth_service.create_access_token(sample_user.id, sample_user.role.value)

        with patch("app.middlewares.auth_middleware.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=sample_user)

            response = client.get(
                "/api/v1/auth/admin-only",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 403
            assert response.json()["error"]["code"] == "FORBIDDEN"

    def test_admin_route_as_admin_user_allowed(
        self, client: TestClient, admin_user: User
    ) -> None:
        """Administrator accessing admin route receives 200 OK."""
        token = auth_service.create_access_token(admin_user.id, admin_user.role.value)

        with patch("app.middlewares.auth_middleware.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_by_id = AsyncMock(return_value=admin_user)

            response = client.get(
                "/api/v1/auth/admin-only",
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            assert "Welcome, Administrator" in response.json()["message"]


# =============================================================================
# 5. Logout Tests
# =============================================================================

class TestLogout:
    """Tests for POST /api/v1/auth/logout."""

    def test_logout_clears_cookie(self, client: TestClient) -> None:
        """Logout endpoint revokes token and clears the HttpOnly cookie."""
        client.cookies.set("refresh_token", "sample_token_value", domain="testserver")

        with patch("app.services.auth_service.UserRepository") as mock_repo_cls:
            mock_repo = mock_repo_cls.return_value
            mock_repo.get_refresh_token_by_hash = AsyncMock(return_value=None)

            response = client.post("/api/v1/auth/logout")

            assert response.status_code == 200
            assert response.json()["message"] == "Successfully logged out"
            cookie_val = response.cookies.get("refresh_token")
            assert cookie_val is None or cookie_val == ""
