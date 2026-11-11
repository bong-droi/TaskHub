"""Tầng business logic (async). Chỉ raise exception nghiệp vụ, không biết gì về HTTP."""

from app.core.constants import ASSIGNEE_NOT_FOUND, PROJECT_NOT_FOUND, TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.models import Task
from app.repositories.task_repository import (
    ProjectRepository,
    TaskRepository,
    UserRepository,
)
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        projects: ProjectRepository,
        users: UserRepository,
    ) -> None:
        self.tasks = tasks
        self.projects = projects
        self.users = users

    async def list_tasks(self, skip: int, limit: int) -> tuple[list[Task], int]:
        return await self.tasks.list(skip, limit), await self.tasks.count()

    async def get_task(self, task_id: int) -> Task:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)  # chỉ MỘT chỗ raise cho Task
        return task

    async def _ensure_assignee(self, assignee_id: int | None) -> None:
        if assignee_id is not None and await self.users.get(assignee_id) is None:
            raise NotFoundException(ASSIGNEE_NOT_FOUND)

    async def create_task(self, payload: TaskCreate) -> Task:
        if await self.projects.get(payload.project_id) is None:
            raise NotFoundException(PROJECT_NOT_FOUND)
        await self._ensure_assignee(payload.assignee_id)
        return await self.tasks.create(payload.model_dump())

    async def update_task(self, task_id: int, payload: TaskUpdate) -> Task:
        task = await self.get_task(task_id)
        data = payload.model_dump(exclude_unset=True)
        await self._ensure_assignee(data.get("assignee_id"))
        return await self.tasks.update(task, data)

    async def delete_task(self, task_id: int) -> None:
        await self.tasks.delete(await self.get_task(task_id))
