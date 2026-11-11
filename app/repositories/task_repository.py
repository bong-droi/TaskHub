"""Tầng data access. Ngày 1: in-memory. Ngày 2: thay bằng SQLAlchemy."""

from datetime import UTC, datetime


class TaskRepository:
    def __init__(self) -> None:
        self._data: dict[int, dict] = {}
        self._next_id = 1

    def list(self, skip: int = 0, limit: int = 20) -> list[dict]:
        return list(self._data.values())[skip : skip + limit]

    def get(self, task_id: int) -> dict | None:
        return self._data.get(task_id)

    def create(self, data: dict) -> dict:
        task = {
            **data,
            "id": self._next_id,
            "status": "TODO",
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
