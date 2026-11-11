"""Dependency Injection: get_db -> repositories -> service -> router; get_current_user."""

from typing import Annotated

import jwt
from fastapi import Depends, Query
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import API_PREFIX
from app.core.constants import DEFAULT_PAGE_LIMIT, INVALID_ACCESS_TOKEN, MAX_PAGE_LIMIT
from app.core.exceptions import UnauthorizedException
from app.core.security import ACCESS, decode_token
from app.db.session import get_db
from app.models import User
from app.repositories.task_repository import ProjectRepository, TaskRepository
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.services.auth_service import AuthService
from app.services.task_service import TaskService
from app.services.user_service import UserService

DbSession = Annotated[AsyncSession, Depends(get_db)]

# tokenUrl giúp Swagger hiện nút "Authorize" (Bearer auth scheme)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{API_PREFIX}/auth/login")


def get_task_service(db: DbSession) -> TaskService:
    # Các repo dùng chung 1 session của request
    return TaskService(TaskRepository(db), ProjectRepository(db), UserRepository(db))


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db), RefreshTokenRepository(db))


def get_user_service(db: DbSession) -> UserService:
    return UserService(UserRepository(db), RefreshTokenRepository(db))


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    try:
        payload = decode_token(token, ACCESS)  # refresh token KHÔNG dùng được ở đây
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise UnauthorizedException(INVALID_ACCESS_TOKEN) from None
    user = await UserRepository(db).get(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException(INVALID_ACCESS_TOKEN)
    return user


class Pagination:
    def __init__(
        self,
        skip: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=MAX_PAGE_LIMIT)] = DEFAULT_PAGE_LIMIT,
    ) -> None:
        self.skip = skip
        self.limit = limit


CurrentUser = Annotated[User, Depends(get_current_user)]
TaskServiceDep = Annotated[TaskService, Depends(get_task_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
PaginationDep = Annotated[Pagination, Depends()]
