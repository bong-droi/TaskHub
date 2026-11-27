"""Băm mật khẩu (bcrypt) và tạo/giải mã JWT (PyJWT)."""

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum

import bcrypt
import jwt
from starlette.concurrency import run_in_threadpool

from app.core.config import ALGORITHM, settings


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:  # hash hỏng/placeholder -> coi như sai mật khẩu
        return False


async def hash_password_async(password: str) -> str:
    """Chạy bcrypt trong thread pool để không chặn event loop khi đăng ký/đổi mật khẩu."""
    return await run_in_threadpool(hash_password, password)


async def verify_password_async(password: str, hashed: str) -> bool:
    """Chạy bcrypt trong thread pool để không chặn event loop khi đăng nhập."""
    return await run_in_threadpool(verify_password, password, hashed)


# Dùng khi email không tồn tại: vẫn tốn thời gian bcrypt để không lộ "email có tồn tại hay không"
DUMMY_HASH = hash_password("dummy-password")


def _encode(sub: str, token_type: TokenType, expires_delta: timedelta) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    exp = now + expires_delta
    payload = {"sub": sub, "type": token_type.value, "jti": jti, "iat": now, "exp": exp}
    return (
        jwt.encode(payload, settings.SECRET_KEY.get_secret_value(), algorithm=ALGORITHM),
        jti,
        exp,
    )


def create_access_token(sub: str, expires_delta: timedelta | None = None) -> str:
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _encode(sub, TokenType.ACCESS, delta)[0]


def create_refresh_token(sub: str) -> tuple[str, str, datetime]:
    """Trả về (token, jti, hạn dùng). jti được lưu DB để có thể thu hồi."""
    return _encode(sub, TokenType.REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType) -> dict:
    """Raise jwt.InvalidTokenError nếu token sai chữ ký, hết hạn hoặc sai loại."""
    payload = jwt.decode(
        token,
        settings.SECRET_KEY.get_secret_value(),
        algorithms=[ALGORITHM],  # luôn chỉ định algorithms
        options={"require": ["exp", "sub", "jti"]},
    )
    if payload.get("type") != expected_type.value:
        raise jwt.InvalidTokenError("Sai loại token")
    return payload
