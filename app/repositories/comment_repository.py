from sqlalchemy import func, select

from app.models import Comment
from app.repositories.base import BaseRepository


class CommentRepository(BaseRepository[Comment]):
    model = Comment

    async def list_by_task(self, task_id: int, skip: int, limit: int) -> list[Comment]:
        stmt = (
            select(Comment)
            .where(Comment.task_id == task_id)
            .order_by(Comment.id)  # cũ nhất trước
            .offset(skip)
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_by_task(self, task_id: int) -> int:
        stmt = select(func.count()).select_from(Comment).where(Comment.task_id == task_id)
        return await self.session.scalar(stmt) or 0
