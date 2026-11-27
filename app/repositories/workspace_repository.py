from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import selectinload

from app.models import Workspace, WorkspaceMember
from app.models.enums import WorkspaceRole
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    async def create_with_owner(self, name: str, owner_id: int) -> Workspace:
        """Tạo workspace và membership OWNER trong cùng một transaction (flush + commit)."""
        ws = Workspace(name=name, owner_id=owner_id)
        self.session.add(ws)
        await self.session.flush()
        self.session.add(
            WorkspaceMember(workspace_id=ws.id, user_id=owner_id, role=WorkspaceRole.OWNER)
        )
        await self.session.commit()
        await self.session.refresh(ws)
        return ws

    def _of_user(self, user_id: int) -> Select[Any]:
        return (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
        )

    async def list_for_user(self, user_id: int, skip: int, limit: int) -> list[Workspace]:
        stmt = self._of_user(user_id).order_by(Workspace.id).offset(skip).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def count_for_user(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(self._of_user(user_id).subquery())
        return await self.session.scalar(stmt) or 0


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    model = WorkspaceMember  # khoá chính kép nên KHÔNG dùng get()/list() của lớp cha

    async def get_member(self, workspace_id: int, user_id: int) -> WorkspaceMember | None:
        return await self.session.get(WorkspaceMember, (workspace_id, user_id))

    async def list_for_workspace(self, workspace_id: int) -> list[WorkspaceMember]:
        stmt = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMember.user))  # async: phải nạp sẵn quan hệ
            .order_by(WorkspaceMember.user_id)
        )
        return list((await self.session.scalars(stmt)).all())
