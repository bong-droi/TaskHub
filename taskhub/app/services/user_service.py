from app.core.constants import WRONG_CURRENT_PASSWORD
from app.core.exceptions import BadRequestException
from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.user import PasswordChange, UserUpdate


class UserService:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository) -> None:
        self.users = users
        self.tokens = tokens

    async def update_profile(self, user: User, payload: UserUpdate) -> User:
        data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
        return await self.users.update(user, data)

    async def change_password(self, user: User, payload: PasswordChange) -> None:
        if not verify_password(payload.current_password, user.hashed_password):
            raise BadRequestException(WRONG_CURRENT_PASSWORD)
        await self.users.update(user, {"hashed_password": hash_password(payload.new_password)})
        # Đăng xuất mọi thiết bị: refresh token cũ không dùng được nữa
        await self.tokens.revoke_all_for_user(user.id)
