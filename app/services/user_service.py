from app.core.constants import WRONG_CURRENT_PASSWORD
from app.core.exceptions import BadRequestException
from app.core.security import hash_password_async, verify_password_async
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
        if not await verify_password_async(payload.current_password, user.hashed_password):
            raise BadRequestException(WRONG_CURRENT_PASSWORD)
        user.hashed_password = await hash_password_async(payload.new_password)
        self.users.session.add(user)
        # Gom cập nhật mật khẩu + thu hồi mọi refresh token vào 1 transaction (1 lần commit)
        await self.tokens.revoke_all_for_user(user.id)
