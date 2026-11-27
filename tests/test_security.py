from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_password_async,
    verify_password,
    verify_password_async,
)


def test_hash_and_verify():
    h = hash_password("abc12345")
    assert h != "abc12345" and h.startswith("$2")
    assert verify_password("abc12345", h)
    assert not verify_password("sai-mat-khau", h)
    assert not verify_password("abc12345", "placeholder")  # hash hỏng -> False, không crash


async def test_async_hash_and_verify():
    h = await hash_password_async("abc12345")
    assert h != "abc12345" and h.startswith("$2")
    assert await verify_password_async("abc12345", h)
    assert not await verify_password_async("sai-mat-khau", h)


def test_same_password_gives_different_hashes():
    assert hash_password("abc12345") != hash_password("abc12345")  # salt ngẫu nhiên


def test_token_types_are_not_interchangeable():
    access = create_access_token("1")
    refresh, jti, _ = create_refresh_token("1")
    assert decode_token(access, TokenType.ACCESS)["sub"] == "1"
    assert decode_token(refresh, TokenType.REFRESH)["jti"] == jti
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(access, TokenType.REFRESH)
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(refresh, TokenType.ACCESS)


def test_expired_and_tampered_tokens_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(create_access_token("1", timedelta(seconds=-1)), TokenType.ACCESS)
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(create_access_token("1")[:-2] + "xx", TokenType.ACCESS)
