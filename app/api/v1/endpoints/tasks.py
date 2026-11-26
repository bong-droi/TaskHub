from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, TaskServiceDep
from app.api.params import IdPath
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page[TaskRead], summary="Task tôi được phép xem (phân trang)")
async def list_tasks(user: CurrentUser, service: TaskServiceDep, page: PaginationDep):
    items, total = await service.list_tasks(user, page.skip, page.limit)
    return Page[TaskRead].create(
        items=[TaskRead.model_validate(item) for item in items],
        total=total,
        page=page.page,
        limit=page.limit,
    )


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo task (OWNER/EDITOR)",
)
async def create_task(payload: TaskCreate, user: CurrentUser, service: TaskServiceDep):
    return await service.create_task(user, payload.project_id, payload)


@router.get("/{task_id}", response_model=TaskRead, summary="Chi tiết task")
async def get_task(task_id: IdPath, user: CurrentUser, service: TaskServiceDep):
    return await service.get_task(user, task_id)


@router.patch("/{task_id}", response_model=TaskRead, summary="Cập nhật task (OWNER/EDITOR)")
async def update_task(
    task_id: IdPath, payload: TaskUpdate, user: CurrentUser, service: TaskServiceDep
):
    return await service.update_task(user, task_id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá task (OWNER mọi task, EDITOR task của mình)",
)
async def delete_task(task_id: IdPath, user: CurrentUser, service: TaskServiceDep):
    await service.delete_task(user, task_id)


@router.post(
    "/{task_id}/labels/{label_id}",
    response_model=TaskRead,
    summary="Gắn label vào task (OWNER/EDITOR, idempotent)",
)
async def add_label(task_id: IdPath, label_id: IdPath, user: CurrentUser, service: TaskServiceDep):
    return await service.add_label(user, task_id, label_id)


@router.delete(
    "/{task_id}/labels/{label_id}",
    response_model=TaskRead,
    summary="Gỡ label khỏi task (OWNER/EDITOR, idempotent)",
)
async def remove_label(
    task_id: IdPath, label_id: IdPath, user: CurrentUser, service: TaskServiceDep
):
    return await service.remove_label(user, task_id, label_id)
