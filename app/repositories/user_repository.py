from datetime import datetime
from typing import Any, cast

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult

from app.models import RefreshToken, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        return await self.session.scalar(select(User).where(User.email == email))


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    async def get_by_jti(self, jti: str) -> RefreshToken | None:
        return await self.session.scalar(select(RefreshToken).where(RefreshToken.jti == jti))

    async def revoke_if_active(self, jti: str) -> bool:
        """Thu hồi token nguyên tử (atomic): chỉ 1 request đồng thời nhận True."""
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(RefreshToken)
                .where(RefreshToken.jti == jti, RefreshToken.revoked.is_(False))
                .values(revoked=True)
            ),
        )
        await self.session.commit()
        return (result.rowcount or 0) == 1

    async def rotate(self, old_jti: str, new_jti: str, user_id: int, expires_at: datetime) -> bool:
        """Thu hồi token cũ (WHERE revoked IS FALSE) và tạo token mới trong CÙNG 1 transaction."""
        result = cast(
            CursorResult[Any],
            await self.session.execute(
                update(RefreshToken)
                .where(RefreshToken.jti == old_jti, RefreshToken.revoked.is_(False))
                .values(revoked=True)
            ),
        )
        if (result.rowcount or 0) != 1:
            await self.session.rollback()
            return False
        self.session.add(RefreshToken(jti=new_jti, user_id=user_id, expires_at=expires_at))
        await self.session.commit()
        return True

    async def revoke_all_for_user(self, user_id: int) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
            .values(revoked=True)
        )
        await self.session.commit()
