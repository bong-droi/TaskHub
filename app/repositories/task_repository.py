from sqlalchemy import func, select

from app.models import Project, Task, WorkspaceMember
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    model = Task

    def _visible_to(self, user_id: int):
        """Task thuộc project của các workspace mà user là thành viên."""
        return (
            select(Task)
            .join(Project, Task.project_id == Project.id)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Project.workspace_id)
            .where(WorkspaceMember.user_id == user_id)
        )

    async def list_visible(self, user_id: int, skip: int, limit: int) -> list[Task]:
        stmt = self._visible_to(user_id).order_by(Task.id).offset(skip).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def count_visible(self, user_id: int) -> int:
        stmt = select(func.count()).select_from(self._visible_to(user_id).subquery())
        return await self.session.scalar(stmt) or 0
