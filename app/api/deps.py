"""Dependency Injection: get_db -> repositories -> service -> router."""

from typing import Annotated

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT
from app.db.session import get_db
from app.repositories.task_repository import (
    ProjectRepository,
    TaskRepository,
    UserRepository,
)
from app.services.task_service import TaskService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_task_service(db: DbSession) -> TaskService:
    # Cả 3 repo dùng chung 1 session của request
    return TaskService(TaskRepository(db), ProjectRepository(db), UserRepository(db))


class Pagination:
    def __init__(
        self,
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    ) -> None:
        self.skip = skip
        self.limit = limit


TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
PaginationDep = Annotated[Pagination, Depends()]
