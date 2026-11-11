from datetime import timedelta

from app.core.constants import (
    EMAIL_ALREADY_REGISTERED,
    INVALID_ACCESS_TOKEN,
    INVALID_CREDENTIALS,
    INVALID_REFRESH_TOKEN,
    REFRESH_TOKEN_REVOKED,
)
from app.core.security import create_access_token
from tests.conftest import EMAIL, PASSWORD

AUTH = "/api/v1/auth"
ME = "/api/v1/users/me"
NEW = {"email": "New@TaskHub.dev", "password": "password123", "full_name": "Người Mới"}


async def login(c, email=EMAIL, password=PASSWORD):
    return await c.post(f"{AUTH}/login", data={"username": email, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


async def test_register_ok_hides_password_and_forces_member_role(anon):
    r = await anon.post(f"{AUTH}/register", json={**NEW, "role": "ADMIN"})  # cố tự nâng quyền
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "new@taskhub.dev"  # chuẩn hoá lower-case
    assert body["role"] == "MEMBER"
    assert "hashed_password" not in body and "password" not in body


async def test_register_duplicate_email_case_insensitive(anon):
    assert (await anon.post(f"{AUTH}/register", json=NEW)).status_code == 201
    dup = await anon.post(f"{AUTH}/register", json={**NEW, "email": "new@taskhub.dev"})
    assert dup.status_code == 409
    assert dup.json() == {"detail": EMAIL_ALREADY_REGISTERED}


async def test_register_validation(anon):
    bad_email = {**NEW, "email": "khong-phai-email"}
    assert (await anon.post(f"{AUTH}/register", json=bad_email)).status_code == 422
    assert (
        await anon.post(f"{AUTH}/register", json={**NEW, "password": "short"})
    ).status_code == 422
    too_long = "ế" * 30  # 90 byte > 72 byte của bcrypt
    assert (
        await anon.post(f"{AUTH}/register", json={**NEW, "password": too_long})
    ).status_code == 422
    blank_name = {**NEW, "full_name": "   "}
    assert (await anon.post(f"{AUTH}/register", json=blank_name)).status_code == 422


async def test_full_name_is_trimmed_but_password_is_not(anon):
    """Review #3: strip chuỗi đầu vào, NGOẠI TRỪ mật khẩu (phải giữ nguyên từng ký tự)."""
    body = {**NEW, "full_name": "  Người Mới  ", "password": " pass word "}
    r = await anon.post(f"{AUTH}/register", json=body)
    assert r.json()["full_name"] == "Người Mới"
    assert (await login(anon, "new@taskhub.dev", " pass word ")).status_code == 200
    assert (await login(anon, "new@taskhub.dev", "pass word")).status_code == 401


async def test_login_success_and_use_token(anon):
    r = await login(anon)
    assert r.status_code == 200
    tokens = r.json()
    assert tokens["token_type"] == "bearer" and tokens["access_token"] and tokens["refresh_token"]
    me = await anon.get(ME, headers=bearer(tokens["access_token"]))
    assert me.status_code == 200 and me.json()["email"] == EMAIL


async def test_login_wrong_password_or_unknown_email_same_message(anon):
    wrong_pw = await login(anon, password="sai-roi-nhe")
    unknown = await login(anon, email="ghost@taskhub.dev")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json() == {"detail": INVALID_CREDENTIALS}
    assert wrong_pw.headers["www-authenticate"] == "Bearer"


async def test_login_inactive_user_forbidden(anon, session_factory, seeded):
    from app.models import User

    async with session_factory() as db:
        (await db.get(User, seeded["user_id"])).is_active = False
        await db.commit()
    assert (await login(anon)).status_code == 403


async def test_protected_endpoints_require_valid_access_token(anon):
    assert (await anon.get("/api/v1/tasks")).status_code == 401
    assert (await anon.get(ME)).status_code == 401
    bad = await anon.get(ME, headers=bearer("abc.def.ghi"))
    assert bad.status_code == 401
    assert bad.json() == {"detail": INVALID_ACCESS_TOKEN}
    assert bad.headers["www-authenticate"] == "Bearer"
    expired = create_access_token("1", timedelta(seconds=-1))
    assert (await anon.get(ME, headers=bearer(expired))).status_code == 401


async def test_refresh_token_cannot_be_used_as_access_token(anon):
    tokens = (await login(anon)).json()
    assert (await anon.get(ME, headers=bearer(tokens["refresh_token"]))).status_code == 401


async def test_refresh_rotates_tokens(anon):
    old = (await login(anon)).json()
    r = await anon.post(f"{AUTH}/refresh", json={"refresh_token": old["refresh_token"]})
    assert r.status_code == 200
    new = r.json()
    assert new["refresh_token"] != old["refresh_token"]
    assert (await anon.get(ME, headers=bearer(new["access_token"]))).status_code == 200


async def test_refresh_reuse_revokes_whole_family(anon):
    old = (await login(anon)).json()
    new = (await anon.post(f"{AUTH}/refresh", json={"refresh_token": old["refresh_token"]})).json()
    # Dùng lại token cũ (đã xoay) -> bị từ chối...
    reuse = await anon.post(f"{AUTH}/refresh", json={"refresh_token": old["refresh_token"]})
    assert reuse.status_code == 401 and reuse.json() == {"detail": REFRESH_TOKEN_REVOKED}
    # ...và token mới cũng bị thu hồi theo (nghi bị đánh cắp)
    again = await anon.post(f"{AUTH}/refresh", json={"refresh_token": new["refresh_token"]})
    assert again.status_code == 401


async def test_refresh_rejects_access_token_and_garbage(anon):
    tokens = (await login(anon)).json()
    r = await anon.post(f"{AUTH}/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401 and r.json() == {"detail": INVALID_REFRESH_TOKEN}
    assert (await anon.post(f"{AUTH}/refresh", json={"refresh_token": "rác"})).status_code == 401


async def test_logout_revokes_refresh_token(anon):
    token = (await login(anon)).json()["refresh_token"]
    assert (await anon.post(f"{AUTH}/logout", json={"refresh_token": token})).status_code == 204
    assert (await anon.post(f"{AUTH}/refresh", json={"refresh_token": token})).status_code == 401
    # logout lặp lại vẫn an toàn (idempotent)
    assert (await anon.post(f"{AUTH}/logout", json={"refresh_token": token})).status_code == 204
