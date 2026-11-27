from app.core.constants import (
    ALREADY_MEMBER,
    CANNOT_CHANGE_OWNER_ROLE,
    CANNOT_REMOVE_OWNER,
    INSUFFICIENT_PERMISSION,
    MEMBER_NOT_FOUND,
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


async def test_update_member_role_rules(team, anon):
    base = f"{WS}/{team.ws['id']}/members"
    # Chỉ OWNER được đổi role (EDITOR/VIEWER -> 403, người ngoài -> 404)
    assert (
        await anon.patch(
            f"{base}/{team.ids['carol']}", json={"role": "EDITOR"}, headers=team.h["bob"]
        )
    ).status_code == 403
    assert (
        await anon.patch(
            f"{base}/{team.ids['bob']}", json={"role": "VIEWER"}, headers=team.h["carol"]
        )
    ).status_code == 403
    assert (
        await anon.patch(
            f"{base}/{team.ids['bob']}", json={"role": "VIEWER"}, headers=team.h["dave"]
        )
    ).status_code == 404

    # Không thể đổi role của OWNER (400) hoặc gán role OWNER cho thành viên (422)
    owner_err = await anon.patch(
        f"{base}/{team.ids['alice']}", json={"role": "EDITOR"}, headers=team.h["alice"]
    )
    assert owner_err.status_code == 400 and owner_err.json() == {"detail": CANNOT_CHANGE_OWNER_ROLE}
    assert (
        await anon.patch(
            f"{base}/{team.ids['bob']}", json={"role": "OWNER"}, headers=team.h["alice"]
        )
    ).status_code == 422

    # User không phải thành viên -> 404
    not_member = await anon.patch(
        f"{base}/{team.ids['dave']}", json={"role": "EDITOR"}, headers=team.h["alice"]
    )
    assert not_member.status_code == 404 and not_member.json() == {"detail": MEMBER_NOT_FOUND}

    # Hạ quyền bob EDITOR -> VIEWER và nâng quyền carol VIEWER -> EDITOR
    demote = await anon.patch(
        f"{base}/{team.ids['bob']}", json={"role": "VIEWER"}, headers=team.h["alice"]
    )
    assert demote.status_code == 200 and demote.json()["role"] == "VIEWER"
    promote = await anon.patch(
        f"{base}/{team.ids['carol']}", json={"role": "EDITOR"}, headers=team.h["alice"]
    )
    assert promote.status_code == 200 and promote.json()["role"] == "EDITOR"

    # Quyền mới có hiệu lực ngay: bob không còn tạo được task, carol tạo được task
    task_url = f"/api/v1/projects/{team.project['id']}/tasks"
    assert (
        await anon.post(task_url, json={"title": "B"}, headers=team.h["bob"])
    ).status_code == 403
    assert (
        await anon.post(task_url, json={"title": "C"}, headers=team.h["carol"])
    ).status_code == 201


async def test_concurrent_duplicate_invite_returns_409_not_500(
    team, anon, monkeypatch, session_factory
):
    """Hai lời mời cùng lúc: cả hai qua bước kiểm tra "đã là thành viên chưa" rồi mới ghi.
    Mô phỏng bằng cách làm bước kiểm tra luôn trả "chưa" cho bob, để khoá chính của DB phải chặn."""
    from sqlalchemy import func, select

    from app.models import WorkspaceMember
    from app.repositories.workspace_repository import WorkspaceMemberRepository

    original = WorkspaceMemberRepository.get_member

    async def blind_for_bob(self, workspace_id, user_id):
        if user_id == team.ids["bob"]:
            return None  # bob đã là EDITOR nhưng kiểm tra "không thấy"
        return await original(self, workspace_id, user_id)

    monkeypatch.setattr(WorkspaceMemberRepository, "get_member", blind_for_bob)
    url = f"{WS}/{team.ws['id']}/members"
    r = await anon.post(url, json={"email": "bob@t.dev", "role": "VIEWER"}, headers=team.h["alice"])
    assert r.status_code == 409 and r.json() == {"detail": ALREADY_MEMBER}
    async with session_factory() as db:  # vẫn đúng 1 dòng, role cũ không bị ghi đè
        rows = (
            await db.scalars(
                select(WorkspaceMember).where(WorkspaceMember.user_id == team.ids["bob"])
            )
        ).all()
        assert len(rows) == 1 and rows[0].role.value == "EDITOR"
        total = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == team.ws["id"])
        )
        assert await db.scalar(total) == 3  # alice, bob, carol
