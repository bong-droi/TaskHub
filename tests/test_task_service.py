"""Unit test tầng service: chỉ dùng các thành phần được inject, raise exception nghiệp vụ."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import PROJECT_NOT_FOUND, TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.core.permissions import WRITE_ROLES
from app.schemas.task import TaskCreate, TaskCreateInProject
from app.services.task_service import TaskService

USER = MagicMock(id=7)


@pytest.fixture
def parts():
    tasks, users, cache = AsyncMock(), AsyncMock(), AsyncMock()
    notifier = MagicMock()  # task_assigned là hàm thường (chỉ xếp lịch chạy nền)
    resources = MagicMock()  # ensure_active là hàm thường; các loader là async
    for name in ("project", "task", "label", "is_member"):
        setattr(resources, name, AsyncMock())
    return TaskService(tasks, users, resources, cache, notifier), tasks, resources


async def test_create_task_goes_through_injected_dependencies(parts):
    svc, tasks, resources = parts
    project = MagicMock(id=1, workspace_id=5)
    resources.project.return_value = project
    tasks.create.return_value = "created"
    assert await svc.create_task(USER, 1, TaskCreateInProject(title="x")) == "created"
    resources.project.assert_awaited_once_with(USER, 1, WRITE_ROLES)  # kiểm quyền trước khi tạo
    resources.ensure_active.assert_called_once_with(project)
    data = tasks.create.await_args.args[0]
    assert data["created_by"] == 7 and data["project_id"] == 1


async def test_project_id_argument_wins_over_the_body(parts):
    """Endpoint cũ (POST /tasks) gửi project_id trong body: tham số project_id của hàm là nguồn
    duy nhất, body không được ghi đè."""
    svc, tasks, resources = parts
    resources.project.return_value = MagicMock(id=3, workspace_id=5)
    await svc.create_task(USER, 3, TaskCreate(title="x", project_id=99))
    assert tasks.create.await_args.args[0]["project_id"] == 3
    resources.project.assert_awaited_once_with(USER, 3, WRITE_ROLES)


@pytest.mark.parametrize("project_id", [0, -3, 2**31, 10**20])
async def test_create_task_with_unknown_project_is_not_found_never_validation_error(
    parts, project_id
):
    """Review: trước đây service dựng lại TaskCreate(project_id=...) nên project_id=0 ném
    ValidationError ngay trong service (500). Giờ chỉ còn NotFoundException."""
    svc, tasks, resources = parts
    resources.project.side_effect = NotFoundException(PROJECT_NOT_FOUND)
    with pytest.raises(NotFoundException) as exc:
        await svc.create_task(USER, project_id, TaskCreateInProject(title="x"))
    assert exc.value.message == PROJECT_NOT_FOUND
    tasks.create.assert_not_awaited()


async def test_missing_task_raises_domain_exception_not_http(parts):
    svc, _, resources = parts
    resources.task.side_effect = NotFoundException(TASK_NOT_FOUND)
    with pytest.raises(NotFoundException) as exc:
        await svc.get_task(USER, 1)
    assert exc.value.message == TASK_NOT_FOUND
