import jwt
from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    ACCOUNT_DISABLED,
    ACCOUNT_UNAVAILABLE,
    EMAIL_ALREADY_REGISTERED,
    INVALID_CREDENTIALS,
    INVALID_REFRESH_TOKEN,
    REFRESH_TOKEN_REVOKED,
)
from app.core.exceptions import ConflictException, ForbiddenException, UnauthorizedException
from app.core.security import (
    DUMMY_HASH,
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import User
from app.repositories.user_repository import RefreshTokenRepository, UserRepository
from app.schemas.auth import RegisterRequest, TokenPair


class AuthService:
    def __init__(self, users: UserRepository, tokens: RefreshTokenRepository) -> None:
        self.users = users
        self.tokens = tokens

    async def register(self, payload: RegisterRequest) -> User:
        email = payload.email.lower()
        if await self.users.get_by_email(email):
            raise ConflictException(EMAIL_ALREADY_REGISTERED)
        try:
            return await self.users.create(
                {
                    "email": email,
                    "full_name": payload.full_name,
                    "hashed_password": hash_password(payload.password),
                }
            )
        except IntegrityError:  # 2 request đăng ký cùng lúc
            await self.users.session.rollback()
            raise ConflictException(EMAIL_ALREADY_REGISTERED) from None

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.users.get_by_email(email.lower())
        if user is None:
            verify_password(password, DUMMY_HASH)  # cân bằng thời gian xử lý
            raise UnauthorizedException(INVALID_CREDENTIALS)
        if not verify_password(password, user.hashed_password):
            raise UnauthorizedException(INVALID_CREDENTIALS)
        if not user.is_active:
            raise ForbiddenException(ACCOUNT_DISABLED)
        return await self._issue_pair(user.id)

    async def refresh(self, refresh_token: str) -> TokenPair:
        payload = self._decode_refresh(refresh_token)
        record = await self.tokens.get_by_jti(payload["jti"])
        if record is None:
            raise UnauthorizedException(INVALID_REFRESH_TOKEN)
        if record.revoked:
            # Token đã dùng/thu hồi mà vẫn bị gửi lại -> nghi bị đánh cắp: thu hồi toàn bộ
            await self.tokens.revoke_all_for_user(record.user_id)
            raise UnauthorizedException(REFRESH_TOKEN_REVOKED)
        user = await self.users.get(record.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException(ACCOUNT_UNAVAILABLE)
        await self.tokens.update(record, {"revoked": True})  # rotation: mỗi token dùng 1 lần
        return await self._issue_pair(user.id)

    async def logout(self, refresh_token: str) -> None:
        payload = self._decode_refresh(refresh_token)
        record = await self.tokens.get_by_jti(payload["jti"])
        if record is not None and not record.revoked:
            await self.tokens.update(record, {"revoked": True})

    @staticmethod
    def _decode_refresh(token: str) -> dict:
        try:
            return decode_token(token, REFRESH)
        except jwt.InvalidTokenError:
            raise UnauthorizedException(INVALID_REFRESH_TOKEN) from None

    async def _issue_pair(self, user_id: int) -> TokenPair:
        refresh, jti, expires_at = create_refresh_token(str(user_id))
        await self.tokens.create({"jti": jti, "user_id": user_id, "expires_at": expires_at})
        return TokenPair(access_token=create_access_token(str(user_id)), refresh_token=refresh)
