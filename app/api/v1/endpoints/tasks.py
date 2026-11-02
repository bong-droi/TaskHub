from fastapi import APIRouter, status

from app.api.deps import PaginationDep, TaskServiceDep
from app.schemas.task import TaskCreate, TaskRead, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskRead], summary="Danh sách task")
def list_tasks(service: TaskServiceDep, page: PaginationDep):
    return service.list_tasks(page.skip, page.limit)


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED,
             summary="Tạo task")
def create_task(payload: TaskCreate, service: TaskServiceDep):
    return service.create_task(payload)


@router.get("/{task_id}", response_model=TaskRead, summary="Chi tiết task")
def get_task(task_id: int, service: TaskServiceDep):
    return service.get_task(task_id)


@router.patch("/{task_id}", response_model=TaskRead, summary="Cập nhật task")
def update_task(task_id: int, payload: TaskUpdate, service: TaskServiceDep):
    return service.update_task(task_id, payload)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Xoá task")
def delete_task(task_id: int, service: TaskServiceDep):
    service.delete_task(task_id)
