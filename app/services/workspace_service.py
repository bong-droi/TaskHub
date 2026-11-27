from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    ALREADY_MEMBER,
    CANNOT_CHANGE_OWNER_ROLE,
    CANNOT_REMOVE_OWNER,
    MEMBER_NOT_FOUND,
    USER_NOT_FOUND,
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
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from app.services.resource_access import ResourceAccess


class WorkspaceService:
    def __init__(
        self,
        workspaces: WorkspaceRepository,
        members: WorkspaceMemberRepository,
        users: UserRepository,
        resources: ResourceAccess,
    ) -> None:
        self.workspaces = workspaces
        self.members = members
        self.users = users
        self.resources = resources

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
        return await self.resources.workspace(user, workspace_id, READ_ROLES)

    async def update(self, user: User, workspace_id: int, payload: WorkspaceUpdate) -> Workspace:
        ws = await self.resources.workspace(user, workspace_id, MANAGE_ROLES)
        return await self.workspaces.update(ws, payload.model_dump(exclude_unset=True))

    async def delete(self, user: User, workspace_id: int) -> None:
        ws = await self.resources.workspace(user, workspace_id, MANAGE_ROLES)
        await self.workspaces.delete(ws)

    # ---- members ----
    async def invite_member(
        self, user: User, workspace_id: int, payload: MemberInvite
    ) -> MemberRead:
        await self.resources.workspace(user, workspace_id, MANAGE_ROLES)
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
        await self.resources.workspace(user, workspace_id, READ_ROLES)
        return [
            MemberRead(
                user_id=m.user_id, email=m.user.email, full_name=m.user.full_name, role=m.role
            )
            for m in await self.members.list_for_workspace(workspace_id)
        ]

    async def update_member_role(
        self, user: User, workspace_id: int, target_id: int, payload: MemberRoleUpdate
    ) -> MemberRead:
        ws = await self.resources.workspace(user, workspace_id, MANAGE_ROLES)
        if target_id == ws.owner_id:
            raise BadRequestException(CANNOT_CHANGE_OWNER_ROLE)
        member = await self.members.get_member(workspace_id, target_id)
        if member is None:
            raise NotFoundException(MEMBER_NOT_FOUND)
        target = await self.users.get(target_id)
        if target is None:
            raise NotFoundException(USER_NOT_FOUND)
        updated = await self.members.update(member, {"role": payload.role})
        return MemberRead(
            user_id=target.id, email=target.email, full_name=target.full_name, role=updated.role
        )

    async def remove_member(self, user: User, workspace_id: int, target_id: int) -> None:
        ws = await self.resources.workspace(user, workspace_id, MANAGE_ROLES)
        if target_id == ws.owner_id:
            raise BadRequestException(CANNOT_REMOVE_OWNER)
        member = await self.members.get_member(workspace_id, target_id)
        if member is None:
            raise NotFoundException(MEMBER_NOT_FOUND)
        await self.members.delete(member)
