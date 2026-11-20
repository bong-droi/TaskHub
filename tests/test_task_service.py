"""Unit test tầng service: chỉ dùng repository/access được inject, raise exception nghiệp vụ."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import PROJECT_NOT_FOUND, TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.models.enums import ProjectStatus
from app.schemas.task import TaskCreate
from app.services.task_service import TaskService

USER = MagicMock(id=7)


@pytest.fixture
def parts():
    tasks, projects, users, access, labels = (AsyncMock() for _ in range(5))
    return TaskService(tasks, projects, users, access, labels), tasks, projects, access


async def test_create_task_goes_through_injected_dependencies(parts):
    svc, tasks, projects, access = parts
    projects.get.return_value = MagicMock(workspace_id=5, status=ProjectStatus.ACTIVE)
    tasks.create.return_value = "created"
    assert await svc.create_task(TaskCreate(title="x", project_id=1), USER) == "created"
    projects.get.assert_awaited_once_with(1)
    access.require.assert_awaited_once()  # phải kiểm tra quyền trước khi tạo
    assert tasks.create.await_args.args[0]["created_by"] == 7


async def test_missing_task_raises_domain_exception_not_http(parts):
    svc, tasks, _, _ = parts
    tasks.get.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await svc.get_task(USER, 1)
    assert exc.value.message == TASK_NOT_FOUND


async def test_missing_project_raises_domain_exception(parts):
    svc, _, projects, _ = parts
    projects.get.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await svc.create_task(TaskCreate(title="x", project_id=1), USER)
    assert exc.value.message == PROJECT_NOT_FOUND
