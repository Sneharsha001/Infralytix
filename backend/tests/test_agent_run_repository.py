"""
Tests for AgentRunRepository.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.agent_run import AgentRun, AgentRunStatus
from app.repositories.agent_run_repository import AgentRunRepository


@pytest.fixture
def repo(mock_db_session: AsyncMock) -> AgentRunRepository:
    return AgentRunRepository(session=mock_db_session)


@pytest.fixture
def sample_run() -> AgentRun:
    return AgentRun(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        agent_type="repository",
        status=AgentRunStatus.PENDING,
    )


class TestAgentRunRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_success(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock, sample_run: AgentRun
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_run
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_id(sample_run.id)
        assert result == sample_run
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: AgentRunRepository, mock_db_session: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_id(uuid.uuid4())
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_project_success(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock, sample_run: AgentRun
    ):
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [sample_run]
        mock_db_session.execute.return_value = mock_result

        result = await repo.list_by_project(sample_run.project_id)
        assert len(result) == 1
        assert result[0] == sample_run
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_project_empty(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock
    ):
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await repo.list_by_project(uuid.uuid4())
        assert len(result) == 0
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_by_type_success(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock, sample_run: AgentRun
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_run
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_latest_by_type(sample_run.project_id, "repository")
        assert result == sample_run
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_by_type_not_found(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock
    ):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_latest_by_type(uuid.uuid4(), "repository")
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(self, repo: AgentRunRepository, mock_db_session: AsyncMock):
        project_id = uuid.uuid4()
        result = await repo.create(
            project_id=project_id,
            agent_type="security",
            status=AgentRunStatus.COMPLETED,
            output_data={"key": "value"},
        )
        assert result.project_id == project_id
        assert result.agent_type == "security"
        assert result.status == AgentRunStatus.COMPLETED
        assert result.output_data == {"key": "value"}

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_defaults(self, repo: AgentRunRepository, mock_db_session: AsyncMock):
        # Edge case: Using defaults
        project_id = uuid.uuid4()
        result = await repo.create(project_id=project_id)
        assert result.agent_type == "repository"
        assert result.status == AgentRunStatus.PENDING
        assert result.output_data is None
        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_success(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock, sample_run: AgentRun
    ):
        result = await repo.update_status(
            sample_run,
            status=AgentRunStatus.COMPLETED,
            output_data={"done": True},
            error_message="none",
        )
        assert result.status == AgentRunStatus.COMPLETED
        assert result.output_data == {"done": True}
        assert result.error_message == "none"

        mock_db_session.add.assert_called_once_with(sample_run)
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_partial(
        self, repo: AgentRunRepository, mock_db_session: AsyncMock, sample_run: AgentRun
    ):
        # Edge case: updating status but keeping output_data/error_message as None
        # should not overwrite existing values
        sample_run.output_data = {"existing": True}
        sample_run.error_message = "existing err"

        result = await repo.update_status(sample_run, status=AgentRunStatus.FAILED)
        assert result.status == AgentRunStatus.FAILED
        assert result.output_data == {"existing": True}
        assert result.error_message == "existing err"

        mock_db_session.add.assert_called_once_with(sample_run)
