from app.core.constants import (
    ALREADY_MEMBER,
    CANNOT_REMOVE_OWNER,
    INSUFFICIENT_PERMISSION,
    USER_NOT_FOUND,
    WORKSPACE_NOT_FOUND,
)
from tests.conftest import WS


async def test_creator_becomes_owner_member(team, anon):
    members = (await anon.get(f"{WS}/{team.ws['id']}/members", headers=team.h["alice"])).json()
    roles = {m["email"]: m["role"] for m in members}
    assert roles == {"alice@t.dev": "OWNER", "bob@t.dev": "EDITOR", "carol@t.dev": "VIEWER"}
    assert team.ws["owner_id"] == team.ids["alice"]


async def test_list_shows_only_my_workspaces(team, anon):
    mine = (await anon.get(WS, headers=team.h["bob"])).json()
    assert mine["total"] == 1 and mine["items"][0]["name"] == "Team"
    assert (await anon.get(WS, headers=team.h["dave"])).json()["total"] == 0


async def test_non_member_gets_404_member_without_rights_gets_403(team, anon):
    url = f"{WS}/{team.ws['id']}"
    outsider = await anon.get(url, headers=team.h["dave"])
    assert outsider.status_code == 404 and outsider.json() == {"detail": WORKSPACE_NOT_FOUND}
    viewer = await anon.patch(url, json={"name": "X"}, headers=team.h["carol"])
    assert viewer.status_code == 403 and viewer.json() == {"detail": INSUFFICIENT_PERMISSION}
    editor = await anon.patch(url, json={"name": "X"}, headers=team.h["bob"])
    assert editor.status_code == 403


async def test_owner_updates_and_validates(team, anon):
    url = f"{WS}/{team.ws['id']}"
    r = await anon.patch(url, json={"name": "  Mới  "}, headers=team.h["alice"])
    assert r.status_code == 200 and r.json()["name"] == "Mới"
    for bad in ({"name": None}, {"name": "   "}, {"name": ""}):
        assert (await anon.patch(url, json=bad, headers=team.h["alice"])).status_code == 422
    assert (await anon.get(url, headers=team.h["alice"])).json()["name"] == "Mới"


async def test_system_admin_can_see_everything(team, anon):
    admin = {
        "Authorization": (
            "Bearer "
            + (
                await anon.post(
                    "/api/v1/auth/login", data={"username": "t@t.dev", "password": "secret123"}
                )
            ).json()["access_token"]
        )
    }
    assert (await anon.get(f"{WS}/{team.ws['id']}", headers=admin)).status_code == 200
    assert (await anon.get(WS, headers=admin)).json()["total"] >= 2


async def test_only_owner_can_delete_workspace(team, anon):
    url = f"{WS}/{team.ws['id']}"
    assert (await anon.delete(url, headers=team.h["bob"])).status_code == 403
    assert (await anon.delete(url, headers=team.h["alice"])).status_code == 204
    assert (await anon.get(url, headers=team.h["alice"])).status_code == 404
    # project bên trong bị xoá theo (cascade)
    assert (
        await anon.get(f"/api/v1/projects/{team.project['id']}", headers=team.h["alice"])
    ).status_code == 404


async def test_invite_rules(team, anon):
    url = f"{WS}/{team.ws['id']}/members"
    body = {"email": "dave@t.dev", "role": "VIEWER"}
    # chỉ OWNER được mời
    assert (await anon.post(url, json=body, headers=team.h["bob"])).status_code == 403
    assert (await anon.post(url, json=body, headers=team.h["dave"])).status_code == 404
    ok = await anon.post(url, json=body, headers=team.h["alice"])
    assert (
        ok.status_code == 201
        and ok.json()["role"] == "VIEWER"
        and ok.json()["email"] == "dave@t.dev"
    )
    # trùng, email lạ, role OWNER
    dup = await anon.post(url, json=body, headers=team.h["alice"])
    assert dup.status_code == 409 and dup.json() == {"detail": ALREADY_MEMBER}
    ghost = await anon.post(url, json={"email": "ghost@t.dev"}, headers=team.h["alice"])
    assert ghost.status_code == 404 and ghost.json() == {"detail": USER_NOT_FOUND}
    owner_role = await anon.post(
        url, json={"email": "dave@t.dev", "role": "OWNER"}, headers=team.h["alice"]
    )
    assert owner_role.status_code == 422


async def test_invite_is_case_insensitive_and_defaults_to_viewer(team, anon):
    r = await anon.post(
        f"{WS}/{team.ws['id']}/members", json={"email": "DAVE@T.dev"}, headers=team.h["alice"]
    )
    assert r.status_code == 201 and r.json()["role"] == "VIEWER"


async def test_remove_member(team, anon):
    base = f"{WS}/{team.ws['id']}/members"
    assert (
        await anon.delete(f"{base}/{team.ids['carol']}", headers=team.h["bob"])
    ).status_code == 403
    owner = await anon.delete(f"{base}/{team.ids['alice']}", headers=team.h["alice"])
    assert owner.status_code == 400 and owner.json() == {"detail": CANNOT_REMOVE_OWNER}
    assert (
        await anon.delete(f"{base}/{team.ids['dave']}", headers=team.h["alice"])
    ).status_code == 404
    assert (
        await anon.delete(f"{base}/{team.ids['carol']}", headers=team.h["alice"])
    ).status_code == 204
    # carol mất quyền truy cập ngay lập tức
    assert (await anon.get(f"{WS}/{team.ws['id']}", headers=team.h["carol"])).status_code == 404


async def test_members_hidden_from_outsiders(team, anon):
    r = await anon.get(f"{WS}/{team.ws['id']}/members", headers=team.h["dave"])
    assert r.status_code == 404
