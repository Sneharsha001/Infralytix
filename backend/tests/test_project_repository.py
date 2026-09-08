"""
Tests for ProjectRepository.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.project import Project
from app.repositories.project_repository import ProjectRepository


@pytest.fixture
def repo(mock_db_session: AsyncMock) -> ProjectRepository:
    return ProjectRepository(session=mock_db_session)


@pytest.fixture
def sample_project() -> Project:
    return Project(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Project",
    )


class TestProjectRepository:
    @pytest.mark.asyncio
    async def test_get_by_id_success(self, repo: ProjectRepository, mock_db_session: AsyncMock, sample_project: Project):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_project
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_id(sample_project.id)
        assert result == sample_project
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo: ProjectRepository, mock_db_session: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        result = await repo.get_by_id(uuid.uuid4())
        assert result is None
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_user_success(self, repo: ProjectRepository, mock_db_session: AsyncMock, sample_project: Project):
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = [sample_project]
        mock_db_session.execute.return_value = mock_result

        result = await repo.list_by_user(sample_project.user_id)
        assert len(result) == 1
        assert result[0] == sample_project
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_by_user_empty(self, repo: ProjectRepository, mock_db_session: AsyncMock):
        mock_result = MagicMock()
        mock_result.scalars().all.return_value = []
        mock_db_session.execute.return_value = mock_result

        result = await repo.list_by_user(uuid.uuid4())
        assert len(result) == 0
        mock_db_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(self, repo: ProjectRepository, mock_db_session: AsyncMock):
        user_id = uuid.uuid4()
        result = await repo.create(
            user_id=user_id,
            name=" My Project ",
            description=" Desc ",
            repo_name=" my-repo "
        )
        assert result.user_id == user_id
        assert result.name == "My Project"
        assert result.description == "Desc"
        assert result.repo_name == "my-repo"

        mock_db_session.add.assert_called_once()
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_empty_optional_fields(self, repo: ProjectRepository, mock_db_session: AsyncMock):
        # Edge case: description and repo_name are None or empty strings
        user_id = uuid.uuid4()
        result = await repo.create(
            user_id=user_id,
            name="Project",
            description="",
            repo_name=None
        )
        assert result.description is None
        assert result.repo_name is None
        mock_db_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(self, repo: ProjectRepository, mock_db_session: AsyncMock, sample_project: Project):
        result = await repo.update(sample_project, name="Updated")
        assert result.name == "Updated"
        mock_db_session.add.assert_called_once_with(sample_project)
        mock_db_session.flush.assert_called_once()
        mock_db_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_invalid_field(self, repo: ProjectRepository, mock_db_session: AsyncMock, sample_project: Project):
        # Edge case: updating with an invalid field should ignore it
        result = await repo.update(sample_project, invalid_field="ignore")
        assert not hasattr(result, "invalid_field")
        mock_db_session.add.assert_called_once_with(sample_project)

    @pytest.mark.asyncio
    async def test_delete_success(self, repo: ProjectRepository, mock_db_session: AsyncMock, sample_project: Project):
        await repo.delete(sample_project)
        mock_db_session.delete.assert_called_once_with(sample_project)
        mock_db_session.flush.assert_called_once()
