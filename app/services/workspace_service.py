from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    ALREADY_MEMBER,
    CANNOT_REMOVE_OWNER,
    MEMBER_NOT_FOUND,
    USER_NOT_FOUND,
    WORKSPACE_NOT_FOUND,
)
from app.core.exceptions import BadRequestException, ConflictException, NotFoundException
from app.core.permissions import MANAGE_ROLES, READ_ROLES
from app.models import User, Workspace
from app.models.enums import UserRole
from app.repositories.user_repository import UserRepository
from app.repositories.workspace_repository import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from app.schemas.workspace import MemberInvite, MemberRead, WorkspaceCreate, WorkspaceUpdate
from app.services.access import AccessControl


class WorkspaceService:
    def __init__(
        self,
        workspaces: WorkspaceRepository,
        members: WorkspaceMemberRepository,
        users: UserRepository,
        access: AccessControl,
    ) -> None:
        self.workspaces = workspaces
        self.members = members
        self.users = users
        self.access = access

    async def _get(self, workspace_id: int) -> Workspace:
        ws = await self.workspaces.get(workspace_id)
        if ws is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND)
        return ws

    async def create(self, user: User, payload: WorkspaceCreate) -> Workspace:
        return await self.workspaces.create_with_owner(payload.name, user.id)

    async def list_for(self, user: User, skip: int, limit: int) -> tuple[list[Workspace], int]:
        if user.role == UserRole.ADMIN:
            return await self.workspaces.list(skip, limit), await self.workspaces.count()
        return (
            await self.workspaces.list_for_user(user.id, skip, limit),
            await self.workspaces.count_for_user(user.id),
        )

    async def get(self, user: User, workspace_id: int) -> Workspace:
        ws = await self._get(workspace_id)
        await self.access.require(user, workspace_id, READ_ROLES, WORKSPACE_NOT_FOUND)
        return ws

    async def update(self, user: User, workspace_id: int, payload: WorkspaceUpdate) -> Workspace:
        ws = await self._get(workspace_id)
        await self.access.require(user, workspace_id, MANAGE_ROLES, WORKSPACE_NOT_FOUND)
        return await self.workspaces.update(ws, payload.model_dump(exclude_unset=True))

    async def delete(self, user: User, workspace_id: int) -> None:
        ws = await self._get(workspace_id)
        await self.access.require(user, workspace_id, MANAGE_ROLES, WORKSPACE_NOT_FOUND)
        await self.workspaces.delete(ws)

    # ---- members ----
    async def invite_member(
        self, user: User, workspace_id: int, payload: MemberInvite
    ) -> MemberRead:
        await self._get(workspace_id)
        await self.access.require(user, workspace_id, MANAGE_ROLES, WORKSPACE_NOT_FOUND)
        target = await self.users.get_by_email(payload.email.lower())
        if target is None:
            raise NotFoundException(USER_NOT_FOUND)
        if await self.members.get_member(workspace_id, target.id):
            raise ConflictException(ALREADY_MEMBER)
        try:
            member = await self.members.create(
                {"workspace_id": workspace_id, "user_id": target.id, "role": payload.role}
            )
        except (
            IntegrityError
        ):  # 2 lời mời cùng lúc: cả hai qua bước kiểm tra, khoá chính chặn bản sau
            await self.members.session.rollback()
            raise ConflictException(ALREADY_MEMBER) from None
        return MemberRead(
            user_id=target.id, email=target.email, full_name=target.full_name, role=member.role
        )

    async def list_members(self, user: User, workspace_id: int) -> list[MemberRead]:
        await self._get(workspace_id)
        await self.access.require(user, workspace_id, READ_ROLES, WORKSPACE_NOT_FOUND)
        return [
            MemberRead(
                user_id=m.user_id, email=m.user.email, full_name=m.user.full_name, role=m.role
            )
            for m in await self.members.list_for_workspace(workspace_id)
        ]

    async def remove_member(self, user: User, workspace_id: int, target_id: int) -> None:
        ws = await self._get(workspace_id)
        await self.access.require(user, workspace_id, MANAGE_ROLES, WORKSPACE_NOT_FOUND)
        if target_id == ws.owner_id:
            raise BadRequestException(CANNOT_REMOVE_OWNER)
        member = await self.members.get_member(workspace_id, target_id)
        if member is None:
            raise NotFoundException(MEMBER_NOT_FOUND)
        await self.members.delete(member)
