"""Ma trận quyền: kiểm tra trực tiếp AccessControl với từng role."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.constants import INSUFFICIENT_PERMISSION
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.permissions import (
    MANAGE_ROLES,
    READ_ROLES,
    WRITE_ROLES,
    can_delete_task,
)
from app.models.enums import UserRole, WorkspaceRole
from app.services.access import AccessControl

OWN, EDT, VWR = WorkspaceRole.OWNER, WorkspaceRole.EDITOR, WorkspaceRole.VIEWER


def _access(member_role):
    members = AsyncMock()
    members.get_member.return_value = MagicMock(role=member_role) if member_role else None
    return AccessControl(members)


def test_role_sets():
    assert READ_ROLES == {OWN, EDT, VWR}
    assert WRITE_ROLES == {OWN, EDT}
    assert MANAGE_ROLES == {OWN}


@pytest.mark.parametrize(
    ("role", "allowed", "ok"),
    [
        (OWN, READ_ROLES, True), (EDT, READ_ROLES, True), (VWR, READ_ROLES, True),
        (OWN, WRITE_ROLES, True), (EDT, WRITE_ROLES, True), (VWR, WRITE_ROLES, False),
        (OWN, MANAGE_ROLES, True), (EDT, MANAGE_ROLES, False), (VWR, MANAGE_ROLES, False),
    ],
)  # fmt: skip
async def test_matrix(role, allowed, ok):
    access = _access(role)
    user = MagicMock(id=1, role=UserRole.MEMBER)
    if ok:
        assert await access.require(user, 1, allowed, "nf") == role
    else:
        with pytest.raises(ForbiddenException) as exc:
            await access.require(user, 1, allowed, "nf")
        assert exc.value.message == INSUFFICIENT_PERMISSION


async def test_non_member_gets_not_found_not_forbidden():
    with pytest.raises(NotFoundException) as exc:
        await _access(None).require(MagicMock(id=1, role=UserRole.MEMBER), 1, READ_ROLES, "nf")
    assert exc.value.message == "nf"


async def test_system_admin_bypasses_membership():
    admin = MagicMock(id=1, role=UserRole.ADMIN)
    access = _access(None)
    assert await access.require(admin, 1, MANAGE_ROLES, "nf") == WorkspaceRole.OWNER
    access.members.get_member.assert_not_called()


# ---- quy tắc phụ thuộc resource: nằm cùng ma trận, test cùng kiểu parametrize ----
@pytest.mark.parametrize(
    ("role", "is_creator", "expected"),
    [
        (OWN, True, True), (OWN, False, True),      # OWNER xoá mọi task
        (EDT, True, True), (EDT, False, False),     # EDITOR chỉ xoá task của mình
        (VWR, True, False), (VWR, False, False),    # VIEWER không bao giờ xoá được
    ],
)  # fmt: skip
def test_can_delete_task_matrix(role, is_creator, expected):
    user = MagicMock(id=1)
    task = MagicMock(created_by=1 if is_creator else 2)
    assert can_delete_task(role, task, user) is expected


def test_task_without_creator_can_only_be_deleted_by_owner():
    user, orphan = MagicMock(id=1), MagicMock(created_by=None)
    assert can_delete_task(OWN, orphan, user) is True
    assert can_delete_task(EDT, orphan, user) is False
