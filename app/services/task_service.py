"""Tầng business logic. Không biết gì về HTTP."""

from app.core.constants import TASK_NOT_FOUND
from app.core.exceptions import NotFoundException
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo  # luôn đi qua self.repo để test inject được repo giả

    def _get_or_raise(self, task_id: int) -> dict:
        task = self.repo.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)  # chỉ MỘT chỗ raise
        return task

    def list_tasks(self, skip: int, limit: int) -> list[dict]:
        return self.repo.list(skip, limit)

    def get_task(self, task_id: int) -> dict:
        return self._get_or_raise(task_id)

    def create_task(self, payload: TaskCreate) -> dict:
        return self.repo.create(payload.model_dump())

    def update_task(self, task_id: int, payload: TaskUpdate) -> dict:
        self._get_or_raise(task_id)
        updated = self.repo.update(task_id, payload.model_dump(exclude_unset=True))
        assert updated is not None  # đã kiểm tra tồn tại ở trên
        return updated

    def delete_task(self, task_id: int) -> None:
        self._get_or_raise(task_id)
        self.repo.delete(task_id)
