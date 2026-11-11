"""Băm mật khẩu (bcrypt) và tạo/giải mã JWT (PyJWT)."""

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    BCRYPT_ROUNDS,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)

ACCESS = "access"
REFRESH = "refresh"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:  # hash hỏng/placeholder -> coi như sai mật khẩu
        return False


# Dùng khi email không tồn tại: vẫn tốn thời gian bcrypt để không lộ "email có tồn tại hay không"
DUMMY_HASH = hash_password("dummy-password")


def _encode(sub: str, token_type: str, expires_delta: timedelta) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    jti = uuid.uuid4().hex
    exp = now + expires_delta
    payload = {"sub": sub, "type": token_type, "jti": jti, "iat": now, "exp": exp}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), jti, exp


def create_access_token(sub: str, expires_delta: timedelta | None = None) -> str:
    delta = expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return _encode(sub, ACCESS, delta)[0]


def create_refresh_token(sub: str) -> tuple[str, str, datetime]:
    """Trả về (token, jti, hạn dùng). jti được lưu DB để có thể thu hồi."""
    return _encode(sub, REFRESH, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: str) -> dict:
    """Raise jwt.InvalidTokenError nếu token sai chữ ký, hết hạn hoặc sai loại."""
    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM],  # luôn chỉ định algorithms
        options={"require": ["exp", "sub", "jti"]},
    )
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Sai loại token")
    return payload
