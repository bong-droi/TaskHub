"""Tầng business logic. Không biết gì về HTTP."""
from fastapi import HTTPException, status

from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repo: TaskRepository) -> None:
        self.repo = repo

    def list_tasks(self, skip: int, limit: int) -> list[dict]:
        return self.repo.list(skip, limit)

    def get_task(self, task_id: int) -> dict:
        task = self.repo.get(task_id)
        if task is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task không tồn tại")
        return task

    def create_task(self, payload: TaskCreate) -> dict:
        return self.repo.create(payload.model_dump())

    def update_task(self, task_id: int, payload: TaskUpdate) -> dict:
        task = self.repo.update(task_id, payload.model_dump(exclude_unset=True))
        if task is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task không tồn tại")
        return task

    def delete_task(self, task_id: int) -> None:
        if not self.repo.delete(task_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task không tồn tại")
