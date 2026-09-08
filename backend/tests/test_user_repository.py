"""
Tests for UserRepository.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.refresh_token import RefreshToken
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository


@pytest.fixture
def repo(mock_db_session: AsyncMock) -> UserRepository:
    return UserRepository(session=mock_db_session)


@pytest.fixture
def sample_user() -> User:
    return User(
        id=uuid.uuid4(),
        name="Test User",
        email="test@example.com",
        hashed_password="hash",
        role=UserRole.USER,
        is_active=True,
    )


class TestUserRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, repo: UserRepository, mock_db_session: AsyncMock, sample_user: User
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_id(sample_user.id)
        assert result == sample_user
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: UserRepository, mock_db_session: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_id(uuid.uuid4())
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_success(
        self, repo: UserRepository, mock_db_session: AsyncMock, sample_user: User
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_user
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_email(" TEST@EXAMPLE.com ")
        assert result == sample_user
        # Verify case-insensitive handling isn't explicitly tested on the mock, but the method runs.
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, repo: UserRepository, mock_db_session: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_email("missing@example.com")
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(self, repo: UserRepository, mock_db_session: AsyncMock):
        result = await repo.create("New User ", " NEW@example.com", "hash")
        assert result.name == "New User"
        assert result.email == "new@example.com"
        assert result.hashed_password == "hash"

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_duplicate_email(self, repo: UserRepository, mock_db_session: AsyncMock):
        # Simulate IntegrityError on flush
        mock_db_session.flush.side_effect = IntegrityError(None, None, Exception("Duplicate key"))
        with pytest.raises(IntegrityError):
            await repo.create("Dup", "dup@example.com", "hash")

    @pytest.mark.asyncio
    async def test_update_success(
        self, repo: UserRepository, mock_db_session: AsyncMock, sample_user: User
    ):
        result = await repo.update(sample_user, name="Updated Name", invalid_field="ignore_this")
        assert result.name == "Updated Name"

        mock_db_session.add.assert_called_once_with(sample_user)
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_no_kwargs(
        self, repo: UserRepository, mock_db_session: AsyncMock, sample_user: User
    ):
        result = await repo.update(sample_user)
        assert result == sample_user
        mock_db_session.add.assert_called_once_with(sample_user)
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()


class TestRefreshTokenRepository:
    @pytest.mark.asyncio
    async def test_create_refresh_token_success(
        self, repo: UserRepository, mock_db_session: AsyncMock
    ):
        user_id = uuid.uuid4()
        expires = datetime.now(UTC)
        result = await repo.create_refresh_token(user_id, "token_hash_abc", expires)

        assert result.user_id == user_id
        assert result.token_hash == "token_hash_abc"
        assert result.expires_at == expires

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_refresh_token_by_hash_success(
        self, repo: UserRepository, mock_db_session: AsyncMock
    ):
        mock_token = RefreshToken(
            user_id=uuid.uuid4(), token_hash="abc", expires_at=datetime.now(UTC)
        )
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_token
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_refresh_token_by_hash("abc")
        assert result == mock_token
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_refresh_token_by_hash_not_found(
        self, repo: UserRepository, mock_db_session: AsyncMock
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_refresh_token_by_hash("missing")
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_refresh_token_success(
        self, repo: UserRepository, mock_db_session: AsyncMock
    ):
        mock_token = RefreshToken(
            user_id=uuid.uuid4(), token_hash="abc", expires_at=datetime.now(UTC)
        )
        assert mock_token.revoked_at is None

        await repo.revoke_refresh_token(mock_token)

        assert mock_token.revoked_at is not None
        mock_db_session.add.assert_called_once_with(mock_token)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_refresh_token_already_revoked(
        self, repo: UserRepository, mock_db_session: AsyncMock
    ):
        # Edge case: revoking an already revoked token updates the timestamp
        import datetime as dt

        old_time = dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
        mock_token = RefreshToken(
            user_id=uuid.uuid4(),
            token_hash="abc",
            expires_at=dt.datetime.now(dt.UTC),
            revoked_at=old_time,
        )

        # Prevent RuntimeWarning for unawaited coroutine by making add a synchronous MagicMock
        mock_db_session.add = MagicMock()

        await repo.revoke_refresh_token(mock_token)

        assert mock_token.revoked_at is not None
        assert mock_token.revoked_at != old_time
        mock_db_session.add.assert_called_once_with(mock_token)
        mock_db_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_all_user_refresh_tokens(
        self, repo: UserRepository, mock_db_session: AsyncMock
    ):
        user_id = uuid.uuid4()
        await repo.revoke_all_user_refresh_tokens(user_id)

        mock_db_session.execute.assert_called_once()
        mock_db_session.flush.assert_called_once()
