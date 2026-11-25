"""ResourceAccess là chỗ DUY NHẤT lấy resource + kiểm quyền + kiểm archive: test kỹ một lần,
mọi service dùng lại."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import (
    COMMENT_NOT_FOUND,
    INSUFFICIENT_PERMISSION,
    LABEL_NOT_FOUND,
    PROJECT_ARCHIVED,
    PROJECT_NOT_FOUND,
    TASK_NOT_FOUND,
    WORKSPACE_NOT_FOUND,
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.permissions import MANAGE_ROLES, READ_ROLES, WRITE_ROLES
from app.models.enums import ProjectStatus, UserRole, WorkspaceRole
from app.services.access import AccessControl
from app.services.resource_access import ResourceAccess

USER = MagicMock(id=1, role=UserRole.MEMBER)


def build(role: WorkspaceRole | None):
    """ResourceAccess với repo giả. `role`: role của USER trong workspace 10, None = người ngoài."""
    members = AsyncMock()
    members.get_member.return_value = MagicMock(role=role) if role else None
    repos = {n: AsyncMock() for n in ("workspaces", "projects", "tasks", "labels", "comments")}
    workspace = MagicMock(id=10)
    project = MagicMock(id=20, workspace_id=10, status=ProjectStatus.ACTIVE)
    task = MagicMock(id=30, project_id=20)
    label = MagicMock(id=40, project_id=20)
    comment = MagicMock(id=50, task_id=30)
    repos["workspaces"].get.return_value = workspace
    repos["projects"].get.return_value = project
    repos["tasks"].get.return_value = task
    repos["labels"].get.return_value = label
    repos["comments"].get.return_value = comment
    resources = ResourceAccess(AccessControl(members), **repos)
    return resources, repos


LOADERS = [  # (tên loader, id, message khi không thấy, repo chứa resource)
    ("workspace", 10, WORKSPACE_NOT_FOUND, "workspaces"),
    ("project", 20, PROJECT_NOT_FOUND, "projects"),
    ("task", 30, TASK_NOT_FOUND, "tasks"),
    ("label", 40, LABEL_NOT_FOUND, "labels"),
    ("comment", 50, COMMENT_NOT_FOUND, "comments"),
]


@pytest.mark.parametrize(("loader", "rid", "message", "repo"), LOADERS)
async def test_missing_resource_is_404_with_its_own_message(loader, rid, message, repo):
    resources, repos = build(WorkspaceRole.OWNER)
    repos[repo].get.return_value = None
    with pytest.raises(NotFoundException) as exc:
        await getattr(resources, loader)(USER, rid, READ_ROLES)
    assert exc.value.message == message


@pytest.mark.parametrize(("loader", "rid", "message", "repo"), LOADERS)
async def test_outsider_gets_the_same_404_so_existence_is_not_leaked(loader, rid, message, repo):
    resources, _ = build(None)
    with pytest.raises(NotFoundException) as exc:
        await getattr(resources, loader)(USER, rid, READ_ROLES)
    assert exc.value.message == message


@pytest.mark.parametrize(("loader", "rid", "message", "repo"), LOADERS)
@pytest.mark.parametrize(
    ("role", "allowed", "ok"),
    [
        (WorkspaceRole.VIEWER, READ_ROLES, True),
        (WorkspaceRole.VIEWER, WRITE_ROLES, False),
        (WorkspaceRole.EDITOR, WRITE_ROLES, True),
        (WorkspaceRole.EDITOR, MANAGE_ROLES, False),
        (WorkspaceRole.OWNER, MANAGE_ROLES, True),
    ],
)
async def test_member_is_checked_against_allowed_roles(
    loader, rid, message, repo, role, allowed, ok
):
    resources, _ = build(role)
    call = getattr(resources, loader)(USER, rid, allowed)
    if ok:
        assert await call is not None
    else:
        with pytest.raises(ForbiddenException) as exc:
            await call
        assert exc.value.message == INSUFFICIENT_PERMISSION


async def test_contexts_carry_everything_the_services_need():
    resources, repos = build(WorkspaceRole.EDITOR)
    task_ctx = await resources.task(USER, 30, READ_ROLES)
    assert (task_ctx.task.id, task_ctx.project.id, task_ctx.role) == (30, 20, WorkspaceRole.EDITOR)
    label_ctx = await resources.label(USER, 40, READ_ROLES)
    assert (label_ctx.label.id, label_ctx.project.id) == (40, 20)
    comment_ctx = await resources.comment(USER, 50, READ_ROLES)
    assert (comment_ctx.comment.id, comment_ctx.task.id, comment_ctx.project.id) == (50, 30, 20)
    repos["tasks"].get.assert_any_await(30)  # comment tìm task qua comment.task_id


async def test_system_admin_bypasses_membership():
    admin = MagicMock(id=9, role=UserRole.ADMIN)
    resources, _ = build(None)  # admin không phải thành viên
    assert (await resources.project(admin, 20, MANAGE_ROLES)).id == 20


def test_ensure_active_is_the_single_archive_rule():
    resources, _ = build(WorkspaceRole.OWNER)
    resources.ensure_active(MagicMock(status=ProjectStatus.ACTIVE))  # không ném gì
    with pytest.raises(ConflictException) as exc:
        resources.ensure_active(MagicMock(status=ProjectStatus.ARCHIVED))
    assert exc.value.message == PROJECT_ARCHIVED
