"""Unit test tầng service: service chỉ dùng repository được inject, raise exception nghiệp vụ."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import PROJECT_NOT_FOUND, TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService


@pytest.fixture
def parts():
    tasks, projects, users = AsyncMock(), AsyncMock(), AsyncMock()
    return TaskService(tasks, projects, users), tasks, projects


async def test_create_task_goes_through_injected_repositories(parts):
    svc, tasks, projects = parts
    projects.get.return_value = MagicMock()
    tasks.create.return_value = "created"
    assert await svc.create_task(TaskCreate(title="x", project_id=1), created_by=7) == "created"
    projects.get.assert_awaited_once_with(1)
    tasks.create.assert_awaited_once()
    assert tasks.create.await_args.args[0]["created_by"] == 7


async def test_missing_task_raises_domain_exception_not_http(parts):
    svc, tasks, _ = parts
    tasks.get.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await svc.get_task(1)
    assert exc.value.message == TASK_NOT_FOUND


async def test_missing_project_raises_domain_exception(parts):
    svc, _, projects = parts
    projects.get.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await svc.create_task(TaskCreate(title="x", project_id=1), created_by=7)
    assert exc.value.message == PROJECT_NOT_FOUND
