from fastapi import APIRouter, status

from app.api.deps import CurrentUser, UserServiceDep
from app.schemas.user import PasswordChange, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead, summary="Xem profile của tôi")
async def get_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserRead, summary="Cập nhật profile")
async def update_me(payload: UserUpdate, user: CurrentUser, service: UserServiceDep):
    return await service.update_profile(user, payload)


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Đổi mật khẩu (đăng xuất mọi thiết bị)",
)
async def change_password(payload: PasswordChange, user: CurrentUser, service: UserServiceDep):
    await service.change_password(user, payload)
