from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, PaginationDep, TaskServiceDep
from app.models.enums import TaskPriority, TaskStatus
from app.schemas.common import Page
from app.schemas.task import TaskCreateInProject, TaskRead

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


class TaskFilters:
    """Bộ lọc task: tất cả đều tuỳ chọn và có thể kết hợp (AND)."""

    def __init__(
        self,
        status: Annotated[TaskStatus | None, Query(description="Lọc theo trạng thái")] = None,
        priority: Annotated[TaskPriority | None, Query(description="Lọc theo độ ưu tiên")] = None,
        assignee_id: Annotated[
            int | None, Query(gt=0, description="Lọc theo người được gán")
        ] = None,
        label_id: Annotated[int | None, Query(gt=0, description="Lọc theo label")] = None,
    ) -> None:
        self.status = status
        self.priority = priority
        self.assignee_id = assignee_id
        self.label_id = label_id


@router.get(
    "",
    response_model=Page[TaskRead],
    summary="Task trong project (lọc status/priority/assignee/label + phân trang)",
)
async def list_project_tasks(
    project_id: int,
    user: CurrentUser,
    service: TaskServiceDep,
    page: PaginationDep,
    filters: Annotated[TaskFilters, Depends()],
):
    items, total = await service.list_in_project(
        user,
        project_id,
        page.skip,
        page.limit,
        status=filters.status,
        priority=filters.priority,
        assignee_id=filters.assignee_id,
        label_id=filters.label_id,
    )
    return Page[TaskRead](items=items, total=total, page=page.page, limit=page.limit)


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo task trong project (OWNER/EDITOR)",
)
async def create_project_task(
    project_id: int, payload: TaskCreateInProject, user: CurrentUser, service: TaskServiceDep
):
    return await service.create_in_project(user, project_id, payload)
