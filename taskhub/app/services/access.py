"""Kiểm tra quyền truy cập theo workspace. Mọi service dùng chung lớp này."""

from collections.abc import Collection

from app.core.constants import INSUFFICIENT_PERMISSION
from app.core.exceptions import ForbiddenException, NotFoundException
from app.models import User
from app.models.enums import UserRole, WorkspaceRole
from app.repositories.workspace_repository import WorkspaceMemberRepository


class AccessControl:
    def __init__(self, members: WorkspaceMemberRepository) -> None:
        self.members = members

    async def role_in(self, user: User, workspace_id: int) -> WorkspaceRole | None:
        """Role của user trong workspace; None nếu không phải thành viên."""
        if user.role == UserRole.ADMIN:
            return WorkspaceRole.OWNER  # ADMIN toàn hệ thống: vượt qua kiểm tra membership
        member = await self.members.get_member(workspace_id, user.id)
        return member.role if member else None

    async def is_member(self, user_id: int, workspace_id: int) -> bool:
        return await self.members.get_member(workspace_id, user_id) is not None

    async def require(
        self,
        user: User,
        workspace_id: int,
        allowed: Collection[WorkspaceRole],
        not_found_message: str,
    ) -> WorkspaceRole:
        """Không phải thành viên -> 404 (không lộ resource có tồn tại hay không).
        Là thành viên nhưng thiếu quyền -> 403."""
        role = await self.role_in(user, workspace_id)
        if role is None:
            raise NotFoundException(not_found_message)
        if role not in allowed:
            raise ForbiddenException(INSUFFICIENT_PERMISSION)
        return role
