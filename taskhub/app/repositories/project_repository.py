from sqlalchemy import func, select

from app.models import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def list_by_workspace(self, workspace_id: int, skip: int, limit: int) -> list[Project]:
        stmt = (
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.id)
            .offset(skip)
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_by_workspace(self, workspace_id: int) -> int:
        stmt = select(func.count()).select_from(Project).where(Project.workspace_id == workspace_id)
        return await self.session.scalar(stmt) or 0
