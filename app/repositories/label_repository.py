from sqlalchemy import func, select

from app.models import Label
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    model = Label

    async def list_by_project(self, project_id: int, skip: int, limit: int) -> list[Label]:
        stmt = (
            select(Label)
            .where(Label.project_id == project_id)
            .order_by(Label.id)
            .offset(skip)
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def count_by_project(self, project_id: int) -> int:
        stmt = select(func.count()).select_from(Label).where(Label.project_id == project_id)
        return await self.session.scalar(stmt) or 0

    async def get_by_name(self, project_id: int, name: str) -> Label | None:
        """So khớp không phân biệt hoa thường: 'Bug' và 'bug' coi là trùng."""
        stmt = select(Label).where(
            Label.project_id == project_id, func.lower(Label.name) == name.lower()
        )
        return await self.session.scalar(stmt)
