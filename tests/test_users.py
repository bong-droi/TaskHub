from app.core.constants import WRONG_CURRENT_PASSWORD
from tests.conftest import EMAIL, PASSWORD

ME = "/api/v1/users/me"
LOGIN = "/api/v1/auth/login"


async def test_get_me_hides_password(client):
    body = (await client.get(ME)).json()
    assert body["email"] == EMAIL and "hashed_password" not in body


async def test_patch_profile_only_changes_given_fields(client):
    r = await client.patch(ME, json={"full_name": "  Tên Mới  "})
    assert r.status_code == 200 and r.json()["full_name"] == "Tên Mới"  # đã strip
    assert r.json()["email"] == EMAIL
    assert (await client.patch(ME, json={"full_name": ""})).status_code == 422
    assert (await client.patch(ME, json={"full_name": "   "})).status_code == 422
    # không thể tự đổi role / email qua PATCH
    r = await client.patch(ME, json={"role": "ADMIN", "email": "x@x.dev"})
    assert r.json()["email"] == EMAIL


async def test_patch_null_full_name_does_not_break_data(client):
    """Cùng lớp lỗi với review #1: `null` gửi tường minh không được ghi đè field NOT NULL."""
    r = await client.patch(ME, json={"full_name": None})
    assert r.status_code == 200 and r.json()["full_name"] == "T"
    assert (await client.get(ME)).status_code == 200


async def test_change_password_flow(anon, client):
    refresh = (await anon.post(LOGIN, data={"username": EMAIL, "password": PASSWORD})).json()[
        "refresh_token"
    ]

    wrong = await client.post(
        f"{ME}/password", json={"current_password": "sai", "new_password": "newpass123"}
    )
    assert wrong.status_code == 400 and wrong.json() == {"detail": WRONG_CURRENT_PASSWORD}
    weak = await client.post(
        f"{ME}/password", json={"current_password": PASSWORD, "new_password": "123"}
    )
    assert weak.status_code == 422

    ok = await client.post(
        f"{ME}/password", json={"current_password": PASSWORD, "new_password": "newpass123"}
    )
    assert ok.status_code == 204

    old = await anon.post(LOGIN, data={"username": EMAIL, "password": PASSWORD})
    new = await anon.post(LOGIN, data={"username": EMAIL, "password": "newpass123"})
    assert old.status_code == 401 and new.status_code == 200
    # refresh token cũ bị thu hồi khi đổi mật khẩu
    assert (
        await anon.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    ).status_code == 401
