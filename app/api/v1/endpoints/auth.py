from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import AuthServiceDep
from app.api.responses import error_responses
from app.schemas.auth import RefreshRequest, RegisterRequest, TokenPair
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
    responses=error_responses(409),
)
async def register(payload: RegisterRequest, service: AuthServiceDep):
    return await service.register(payload)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Đăng nhập (username = email)",
    responses=error_responses(401, 403),
)
async def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], service: AuthServiceDep):
    return await service.login(form.username, form.password)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Đổi refresh token lấy cặp token mới",
    responses=error_responses(401),
)
async def refresh(payload: RefreshRequest, service: AuthServiceDep):
    return await service.refresh(payload.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đăng xuất (thu hồi refresh token)",
    responses=error_responses(401),
)
async def logout(payload: RefreshRequest, service: AuthServiceDep):
    await service.logout(payload.refresh_token)
