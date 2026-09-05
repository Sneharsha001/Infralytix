# Sprint 1/2 Review — Authentication & Authorization (RBAC)

**Sprint Name**: Authentication & Role-Based Access Control (RBAC)  
**Sprint Number**: 1  
**Date Completed**: 2026-09-05  
**Sprint Duration**: 1 session  
**Status**: ✅ Complete

---

## Objective

Implement the complete, production-grade Authentication and Authorization layer for the Infralytix backend. This includes user registration, password hashing via bcrypt (passlib), JWT token issuance/verification (python-jose), refresh token rotation and revocation (HttpOnly cookies), layered architecture (API → Service → Repository → Models), and RBAC route gating.

---

## Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| `backend/app/models/base.py` | ✅ | `BaseModel` with UUID `id`, `created_at`, `updated_at` |
| `backend/app/models/user.py` | ✅ | `User` ORM entity with `UserRole` enum; documented `lazy="selectin"` |
| `backend/app/models/refresh_token.py` | ✅ | `RefreshToken` ORM entity storing SHA-256 token hashes |
| `backend/alembic/versions/20260905_2200_001_create_users_and_refresh_tokens_tables.py` | ✅ | Hand-crafted migration for `users` and `refresh_tokens` |
| `backend/alembic/env.py` | ✅ | Wired `target_metadata = Base.metadata` |
| `backend/app/schemas/auth.py` | ✅ | `UserRegister`, `UserLogin`, `TokenResponse`, `UserResponse` (never exposes `hashed_password`) |
| `backend/app/schemas/user.py` | ✅ | Separate Request (`UserCreate`, `UserUpdate`) and Response (`UserRead`) schemas |
| `backend/app/repositories/user_repository.py` | ✅ | Pure SQL queries: `get_by_email`, `get_by_id`, `create`, `update`, token persistence/revocation |
| `backend/app/services/auth_service.py` | ✅ | Business logic: `register_user`, `authenticate_user`, JWT access token, refresh token rotation/theft detection |
| `backend/app/middlewares/auth_middleware.py` | ✅ | `get_current_user` dependency (401 on expired/invalid) & `require_role(UserRole)` (403 on forbidden) |
| `backend/app/api/v1/endpoints/auth.py` | ✅ | Endpoints: `POST /register`, `POST /login`, `POST /refresh`, `POST /logout`, `GET /me`, `GET /admin-only` |
| `backend/app/api/v1/router.py` | ✅ | Mounted `auth_router` under prefix `/auth` |
| `backend/tests/test_auth.py` | ✅ | 17 test cases covering registration, login, refresh rotation/reuse, RBAC, logout |

---

## Architecture Added

- **Layered Architecture**: Strict separation of concerns:
  - `endpoints/auth.py` handles HTTP protocol, cookies, and status codes.
  - `services/auth_service.py` handles password verification, JWT generation, and token rotation rules.
  - `repositories/user_repository.py` executes isolated SQLAlchemy queries.
  - `models/user.py` & `models/refresh_token.py` inherit `models/base.py`'s `BaseModel`.
- **Security & Cryptography**:
  - Passwords hashed using bcrypt via `passlib`.
  - JWT access tokens signed with HMAC-SHA256 (`python-jose`) using `settings.SECRET_KEY` and `settings.ALGORITHM`.
  - Refresh tokens are cryptographically random strings (64 bytes URL-safe); only their SHA-256 hashes are stored in the database.
  - Refresh tokens delivered as secure `HttpOnly`, `SameSite=Lax` cookies scoped to `/api/v1/auth`.
  - **Token Reuse Detection**: If an already revoked refresh token is presented, all refresh tokens for that user are revoked immediately.
- **RBAC (Role-Based Access Control)**:
  - `UserRole`: `user`, `administrator`, `evaluator`.
  - Declarative dependency `require_role(*allowed_roles)` returns HTTP 403 `ForbiddenException` for unauthorized roles.

---

## Database Changes

- Created `users` table:
  - `id`: UUID Primary Key
  - `name`: VARCHAR(120) NOT NULL
  - `email`: VARCHAR(160) NOT NULL UNIQUE (indexed)
  - `hashed_password`: VARCHAR(255) NOT NULL
  - `role`: ENUM('user', 'administrator', 'evaluator') NOT NULL DEFAULT 'user'
  - `is_active`: BOOLEAN NOT NULL DEFAULT TRUE
  - `created_at`: DATETIME(timezone=True) NOT NULL
  - `updated_at`: DATETIME(timezone=True) NOT NULL
- Created `refresh_tokens` table:
  - `id`: UUID Primary Key
  - `user_id`: UUID NOT NULL, Foreign Key to `users(id)` ON DELETE CASCADE
  - `token_hash`: CHAR(64) NOT NULL UNIQUE (indexed)
  - `expires_at`: DATETIME(timezone=True) NOT NULL
  - `revoked_at`: DATETIME(timezone=True) NULL
  - `created_at`: DATETIME(timezone=True) NOT NULL
  - `updated_at`: DATETIME(timezone=True) NOT NULL

---

## APIs Created

| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/v1/auth/register` | POST | 201 Created | Registers new user account; returns `UserResponse` |
| `/api/v1/auth/login` | POST | 200 OK | Authenticates user; returns `TokenResponse` and sets `HttpOnly` refresh cookie |
| `/api/v1/auth/refresh` | POST | 200 OK | Rotates refresh token cookie and issues new access token |
| `/api/v1/auth/logout` | POST | 200 OK | Revokes active refresh token and clears `HttpOnly` cookie |
| `/api/v1/auth/me` | GET | 200 OK | Protected endpoint returning current user profile |
| `/api/v1/auth/admin-only` | GET | 200 OK | RBAC-gated route requiring `administrator` role (403 for other roles) |

---

## Tests Completed

All 32 tests across the backend test suite passed with 100% success rate:

```text
tests/test_auth.py::TestUserRegistration::test_register_success PASSED
tests/test_auth.py::TestUserRegistration::test_register_duplicate_email PASSED
tests/test_auth.py::TestUserRegistration::test_register_validation_short_password PASSED
tests/test_auth.py::TestUserRegistration::test_register_invalid_email PASSED
tests/test_auth.py::TestUserLogin::test_login_success PASSED
tests/test_auth.py::TestUserLogin::test_login_wrong_password PASSED
tests/test_auth.py::TestUserLogin::test_login_nonexistent_email PASSED
tests/test_auth.py::TestUserLogin::test_login_inactive_account PASSED
tests/test_auth.py::TestTokenRefresh::test_refresh_token_success PASSED
tests/test_auth.py::TestTokenRefresh::test_refresh_token_missing PASSED
tests/test_auth.py::TestTokenRefresh::test_refresh_token_reuse_detection PASSED
tests/test_auth.py::TestProtectedRoutesAndRBAC::test_get_me_unauthenticated PASSED
tests/test_auth.py::TestProtectedRoutesAndRBAC::test_get_me_invalid_token PASSED
tests/test_auth.py::TestProtectedRoutesAndRBAC::test_get_me_authenticated PASSED
tests/test_auth.py::TestProtectedRoutesAndRBAC::test_admin_route_as_regular_user_forbidden PASSED
tests/test_auth.py::TestProtectedRoutesAndRBAC::test_admin_route_as_admin_user_allowed PASSED
tests/test_auth.py::TestLogout::test_logout_clears_cookie PASSED
tests/test_health.py::TestLivenessCheck::test_health_returns_200 PASSED
tests/test_health.py::TestLivenessCheck::test_health_response_schema PASSED
tests/test_health.py::TestLivenessCheck::test_health_status_is_healthy PASSED
tests/test_health.py::TestLivenessCheck::test_health_service_metadata PASSED
tests/test_health.py::TestLivenessCheck::test_health_timestamp_is_present PASSED
tests/test_health.py::TestLivenessCheck::test_health_content_type_is_json PASSED
tests/test_health.py::TestLivenessCheck::test_health_includes_request_id_header PASSED
tests/test_health.py::TestLivenessCheck::test_health_includes_process_time_header PASSED
tests/test_health.py::TestLivenessCheck::test_health_request_ids_are_unique PASSED
tests/test_health.py::TestReadinessCheck::test_readiness_returns_200 PASSED
tests/test_health.py::TestReadinessCheck::test_readiness_response_schema PASSED
tests/test_health.py::TestReadinessCheck::test_readiness_checks_is_dict PASSED
tests/test_health.py::TestReadinessCheck::test_readiness_application_check_ok PASSED
tests/test_health.py::TestNotFoundBehavior::test_unknown_route_returns_404 PASSED
tests/test_health.py::TestNotFoundBehavior::test_root_path_returns_404 PASSED

======================= 32 passed in 6.44s =======================
```

- **Linter**: `ruff check app/ tests/` → 0 errors.
- **Type Checker**: `mypy app/ --ignore-missing-imports` → 0 errors across 26 source files.

---

## Next Sprint

- **Sprint 2 / Workflow Ingestion**:
  - Implement `app/models/workflow.py`, `tasks.py`, `task_dependencies.py`.
  - Workflow file upload endpoint (`POST /api/v1/workflows`) with format validation.
  - DAG cycle detection & task graph parsing (NetworkX).
