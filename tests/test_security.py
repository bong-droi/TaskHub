from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    ACCESS,
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify():
    h = hash_password("abc12345")
    assert h != "abc12345" and h.startswith("$2")
    assert verify_password("abc12345", h)
    assert not verify_password("sai-mat-khau", h)
    assert not verify_password("abc12345", "placeholder")  # hash hỏng -> False, không crash


def test_same_password_gives_different_hashes():
    assert hash_password("abc12345") != hash_password("abc12345")  # salt ngẫu nhiên


def test_token_types_are_not_interchangeable():
    access = create_access_token("1")
    refresh, jti, _ = create_refresh_token("1")
    assert decode_token(access, ACCESS)["sub"] == "1"
    assert decode_token(refresh, REFRESH)["jti"] == jti
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(access, REFRESH)
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(refresh, ACCESS)


def test_expired_and_tampered_tokens_rejected():
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(create_access_token("1", timedelta(seconds=-1)), ACCESS)
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(create_access_token("1")[:-2] + "xx", ACCESS)
