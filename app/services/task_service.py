"""Tầng business logic (async). Chỉ raise exception nghiệp vụ, không biết gì về HTTP."""

from app.core.constants import (
    ASSIGNEE_NOT_FOUND,
    ASSIGNEE_NOT_IN_WORKSPACE,
    INSUFFICIENT_PERMISSION,
    LABEL_NOT_IN_PROJECT,
)
from app.core.exceptions import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from app.core.permissions import READ_ROLES, WRITE_ROLES, can_delete_task
from app.models import Task, User
from app.models.enums import TaskPriority, TaskStatus, UserRole
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.task import TaskCreateInProject, TaskRead, TaskUpdate
from app.services.resource_access import ResourceAccess


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        users: UserRepository,
        resources: ResourceAccess,
    ) -> None:
        self.tasks = tasks
        self.users = users
        self.resources = resources

    # ------------------------------------------------------------------ đọc
    async def list_tasks(self, user: User, skip: int, limit: int) -> tuple[list[Task], int]:
        if user.role == UserRole.ADMIN:
            return await self.tasks.list(skip, limit), await self.tasks.count()
        # Chỉ thấy task thuộc workspace mình là thành viên
        return (
            await self.tasks.list_visible(user.id, skip, limit),
            await self.tasks.count_visible(user.id),
        )

    async def get_task(self, user: User, task_id: int) -> Task:
        return (await self.resources.task(user, task_id, READ_ROLES)).task

    async def list_in_project(
        self,
        user: User,
        project_id: int,
        page: int,
        limit: int,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        label_id: int | None = None,
    ) -> Page[TaskRead]:
        await self.resources.project(user, project_id, READ_ROLES)
        filters = {
            "status": status,
            "priority": priority,
            "assignee_id": assignee_id,
            "label_id": label_id,
        }
        skip = (page - 1) * limit
        items = await self.tasks.list_by_project(project_id, skip, limit, **filters)
        total = await self.tasks.count_by_project(project_id, **filters)
        return Page[TaskRead](
            items=[TaskRead.model_validate(t) for t in items],
            total=total,
            page=page,
            limit=limit,
        )

    # ------------------------------------------------------------------ ghi
    async def _ensure_assignee(self, assignee_id: int | None, workspace_id: int) -> None:
        if assignee_id is None:
            return
        if await self.users.get(assignee_id) is None:
            raise NotFoundException(ASSIGNEE_NOT_FOUND)
        if not await self.resources.is_member(assignee_id, workspace_id):
            raise BadRequestException(ASSIGNEE_NOT_IN_WORKSPACE)

    async def create_task(self, user: User, project_id: int, payload: TaskCreateInProject) -> Task:
        """`project_id` truyền riêng (từ URL hoặc body của endpoint cũ), KHÔNG dựng lại schema:
        dựng lại sẽ validate lần hai và có thể ném ValidationError trong service (thành 500)."""
        project = await self.resources.project(user, project_id, WRITE_ROLES)
        self.resources.ensure_active(project)
        await self._ensure_assignee(payload.assignee_id, project.workspace_id)
        data = payload.model_dump(exclude={"project_id"})  # TaskCreate (endpoint cũ) có field này
        return await self.tasks.create({**data, "project_id": project.id, "created_by": user.id})

    async def update_task(self, user: User, task_id: int, payload: TaskUpdate) -> Task:
        ctx = await self.resources.task(user, task_id, WRITE_ROLES)
        self.resources.ensure_active(ctx.project)
        data = payload.model_dump(exclude_unset=True)
        await self._ensure_assignee(data.get("assignee_id"), ctx.project.workspace_id)
        return await self.tasks.update(ctx.task, data)

    async def delete_task(self, user: User, task_id: int) -> None:
        ctx = await self.resources.task(user, task_id, READ_ROLES)
        if not can_delete_task(ctx.role, ctx.task, user):
            raise ForbiddenException(INSUFFICIENT_PERMISSION)
        await self.tasks.delete(ctx.task)

    # ------------------------------------------------------------------ gắn / gỡ label
    async def _task_and_label(self, user: User, task_id: int, label_id: int):
        ctx = await self.resources.task(user, task_id, WRITE_ROLES)
        self.resources.ensure_active(ctx.project)
        # Phải có quyền xem label: label của workspace khác thì như không tồn tại (404)
        label = (await self.resources.label(user, label_id, READ_ROLES)).label
        if label.project_id != ctx.project.id:
            raise BadRequestException(LABEL_NOT_IN_PROJECT)
        return ctx.task, label

    async def add_label(self, user: User, task_id: int, label_id: int) -> Task:
        task, label = await self._task_and_label(user, task_id, label_id)
        return await self.tasks.add_label(task, label)

    async def remove_label(self, user: User, task_id: int, label_id: int) -> Task:
        task, label = await self._task_and_label(user, task_id, label_id)
        return await self.tasks.remove_label(task, label)
