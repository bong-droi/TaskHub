"""Dependency Injection: repo -> service -> router."""
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Query

from app.repositories.task_repository import TaskRepository
from app.services.task_service import TaskService


@lru_cache
def get_task_repo() -> TaskRepository:
    # Singleton in-memory; Ngày 2 đổi thành repo nhận DB session (dependency có yield)
    return TaskRepository()


def get_task_service(
    repo: Annotated[TaskRepository, Depends(get_task_repo)],
) -> TaskService:
    return TaskService(repo)


class Pagination:
    def __init__(
        self,
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> None:
        self.skip = skip
        self.limit = limit


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
PaginationDep = Annotated[Pagination, Depends()]
