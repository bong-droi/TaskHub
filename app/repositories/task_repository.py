"""Tầng data access. Ngày 1: in-memory. Ngày 2: thay bằng SQLAlchemy."""

from datetime import UTC, datetime

from app.schemas.enums import TaskStatus


class TaskRepository:
    def __init__(self) -> None:
        self._data: dict[int, dict] = {}
        self._next_id = 1

    def list(self, skip: int = 0, limit: int = 20) -> list[dict]:
        sorted_tasks = sorted(self._data.values(), key=lambda t: t["id"])
        return sorted_tasks[skip : skip + limit]

    def total(self) -> int:
        return len(self._data)

    def get(self, task_id: int) -> dict | None:
        return self._data.get(task_id)

    def create(self, data: dict) -> dict:
        task = {
            **data,
            "id": self._next_id,
            "status": TaskStatus.TODO,
            "created_at": datetime.now(UTC),
        }
        self._data[self._next_id] = task
        self._next_id += 1
        return task

    def update(self, task_id: int, data: dict) -> dict | None:
        task = self._data.get(task_id)
        if task is None:
            return None
        task.update(data)
        return task

    def delete(self, task_id: int) -> bool:
        return self._data.pop(task_id, None) is not None
