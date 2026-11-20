from sqlalchemy import func, select

from app.models import Label, Project, Task, WorkspaceMember, task_labels
from app.models.enums import TaskPriority, TaskStatus
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

    # ---- lọc trong một project ----
    @staticmethod
    def _filters(
        project_id: int,
        status: TaskStatus | None,
        priority: TaskPriority | None,
        assignee_id: int | None,
        label_id: int | None,
    ) -> list:
        conds = [Task.project_id == project_id]
        if status is not None:
            conds.append(Task.status == status)
        if priority is not None:
            conds.append(Task.priority == priority)
        if assignee_id is not None:
            conds.append(Task.assignee_id == assignee_id)
        if label_id is not None:
            conds.append(
                Task.id.in_(select(task_labels.c.task_id).where(task_labels.c.label_id == label_id))
            )
        return conds

    async def list_by_project(
        self,
        project_id: int,
        skip: int,
        limit: int,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        label_id: int | None = None,
    ) -> list[Task]:
        conds = self._filters(project_id, status, priority, assignee_id, label_id)
        stmt = select(Task).where(*conds).order_by(Task.id).offset(skip).limit(limit)
        return list((await self.session.scalars(stmt)).all())

    async def count_by_project(
        self,
        project_id: int,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        label_id: int | None = None,
    ) -> int:
        conds = self._filters(project_id, status, priority, assignee_id, label_id)
        return await self.session.scalar(select(func.count()).select_from(Task).where(*conds)) or 0

    async def add_label(self, task: Task, label: Label) -> Task:
        if label not in task.labels:  # idempotent
            task.labels.append(label)
            await self.session.commit()
            await self.session.refresh(task)
        return task

    async def remove_label(self, task: Task, label: Label) -> Task:
        if label in task.labels:  # idempotent
            task.labels.remove(label)
            await self.session.commit()
            await self.session.refresh(task)
        return task
