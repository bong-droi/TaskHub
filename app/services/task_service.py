"""Tầng business logic (async). Chỉ raise exception nghiệp vụ, không biết gì về HTTP."""

from typing import Any

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
from app.models import Label, Task, User
from app.models.enums import UserRole
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Page
from app.schemas.task import TaskCreateInProject, TaskRead, TaskUpdate
from app.services.notifier import Notifier
from app.services.resource_access import ResourceAccess
from app.services.task_cache import TaskListCache, TaskListParams, TaskListResult


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        users: UserRepository,
        resources: ResourceAccess,
        cache: TaskListCache,
        notifier: Notifier,
    ) -> None:
        self.tasks = tasks
        self.users = users
        self.resources = resources
        self.cache = cache
        self.notifier = notifier

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

    async def _query_page(self, project_id: int, params: TaskListParams) -> Page[TaskRead]:
        filters: dict[str, Any] = {
            "status": params.status,
            "priority": params.priority,
            "assignee_id": params.assignee_id,
            "label_id": params.label_id,
        }
        items = await self.tasks.list_by_project(project_id, params.skip, params.limit, **filters)
        total = await self.tasks.count_by_project(project_id, **filters)
        return Page[TaskRead].create(
            items=[TaskRead.model_validate(t) for t in items],
            total=total,
            page=params.page,
            limit=params.limit,
        )

    async def list_in_project(
        self, user: User, project_id: int, params: TaskListParams
    ) -> TaskListResult:
        # 1) Quyền TRƯỚC: người không có quyền không bao giờ chạm tới cache
        await self.resources.project(user, project_id, READ_ROLES)
        if not self.cache.enabled:
            return TaskListResult(await self._query_page(project_id, params), "BYPASS")
        # 2) Đọc version TRƯỚC khi query DB (xem giải thích ở services/task_cache.py)
        version = await self.cache.version(project_id)
        if version is None:
            return TaskListResult(await self._query_page(project_id, params), "BYPASS")
        cached = await self.cache.get(project_id, version, params)
        if cached is not None:
            return TaskListResult(cached, "HIT")
        page = await self._query_page(project_id, params)
        await self.cache.set(project_id, version, params, page)
        return TaskListResult(page, "MISS")

    # ------------------------------------------------------------------ ghi
    async def _ensure_assignee(self, assignee_id: int | None, workspace_id: int) -> User | None:
        if assignee_id is None:
            return None
        assignee = await self.users.get(assignee_id)
        if assignee is None:
            raise NotFoundException(ASSIGNEE_NOT_FOUND)
        if not await self.resources.is_member(assignee_id, workspace_id):
            raise BadRequestException(ASSIGNEE_NOT_IN_WORKSPACE)
        return assignee

    async def create_task(self, user: User, project_id: int, payload: TaskCreateInProject) -> Task:
        """`project_id` truyền riêng (từ URL hoặc body của endpoint cũ), KHÔNG dựng lại schema:
        dựng lại sẽ validate lần hai và có thể ném ValidationError trong service (thành 500)."""
        project = await self.resources.project(user, project_id, WRITE_ROLES)
        self.resources.ensure_active(project)
        assignee = await self._ensure_assignee(payload.assignee_id, project.workspace_id)
        data = payload.model_dump(exclude={"project_id"})  # TaskCreate (endpoint cũ) có field này
        task = await self.tasks.create({**data, "project_id": project.id, "created_by": user.id})
        await self.cache.invalidate(project.id)  # sau commit
        if assignee is not None:
            self.notifier.task_assigned(task, project, assignee, user)
        return task

    async def update_task(self, user: User, task_id: int, payload: TaskUpdate) -> Task:
        ctx = await self.resources.task(user, task_id, WRITE_ROLES)
        self.resources.ensure_active(ctx.project)
        data = payload.model_dump(exclude_unset=True)
        previous_assignee_id = ctx.task.assignee_id  # lấy TRƯỚC khi update ghi đè
        assignee = await self._ensure_assignee(data.get("assignee_id"), ctx.project.workspace_id)
        task = await self.tasks.update(ctx.task, data)
        await self.cache.invalidate(ctx.project.id)
        # Chỉ báo khi giao cho một người MỚI (đổi người, hoặc từ chưa giao sang có người)
        if assignee is not None and assignee.id != previous_assignee_id:
            self.notifier.task_assigned(task, ctx.project, assignee, user)
        return task

    async def delete_task(self, user: User, task_id: int) -> None:
        ctx = await self.resources.task(user, task_id, READ_ROLES)
        if not can_delete_task(ctx.role, ctx.task, user):
            raise ForbiddenException(INSUFFICIENT_PERMISSION)
        await self.tasks.delete(ctx.task)
        await self.cache.invalidate(ctx.project.id)

    # ------------------------------------------------------------------ gắn / gỡ label
    async def _task_and_label(self, user: User, task_id: int, label_id: int) -> tuple[Task, Label]:
        ctx = await self.resources.task(user, task_id, WRITE_ROLES)
        self.resources.ensure_active(ctx.project)
        # Phải có quyền xem label: label của workspace khác thì như không tồn tại (404)
        label = (await self.resources.label(user, label_id, READ_ROLES)).label
        if label.project_id != ctx.project.id:
            raise BadRequestException(LABEL_NOT_IN_PROJECT)
        return ctx.task, label

    async def add_label(self, user: User, task_id: int, label_id: int) -> Task:
        task, label = await self._task_and_label(user, task_id, label_id)
        task = await self.tasks.add_label(task, label)
        await self.cache.invalidate(task.project_id)  # labels nằm trong dữ liệu task được cache
        return task

    async def remove_label(self, user: User, task_id: int, label_id: int) -> Task:
        task, label = await self._task_and_label(user, task_id, label_id)
        task = await self.tasks.remove_label(task, label)
        await self.cache.invalidate(task.project_id)
        return task
