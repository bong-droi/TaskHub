from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, TaskServiceDep
from app.schemas.common import Page
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=Page[TaskRead], summary="Danh sách task (phân trang)")
async def list_tasks(service: TaskServiceDep, page: PaginationDep):
    items, total = await service.list_tasks(page.skip, page.limit)
    return Page[TaskRead](items=items, total=total, skip=page.skip, limit=page.limit)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED, summary="Tạo task")
async def create_task(payload: TaskCreate, service: TaskServiceDep, user: CurrentUser):
    return await service.create_task(payload, created_by=user.id)


@router.get("/{task_id}", response_model=TaskRead, summary="Chi tiết task")
async def get_task(task_id: int, service: TaskServiceDep):
    return await service.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskRead, summary="Cập nhật task")
async def update_task(task_id: int, payload: TaskUpdate, service: TaskServiceDep):
    return await service.update_task(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xoá task")
async def delete_task(task_id: int, service: TaskServiceDep):
    await service.delete_task(task_id)
