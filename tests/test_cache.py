import logging

import pytest

from app.core.config import settings
from app.repositories.task_repository import TaskRepository
from app.schemas.common import Page
from app.schemas.task import TaskRead
from app.services.task_cache import VERSION_TTL_SECONDS, TaskListCache, TaskListParams

PRJ = "/api/v1/projects"
TASKS = "/api/v1/tasks"
WS = "/api/v1/workspaces"


def _url(team, query=""):
    return f"{PRJ}/{team.project['id']}/tasks{query}"


async def _mk(anon, team, title, who="alice", **extra):
    r = await anon.post(_url(team), json={"title": title, **extra}, headers=team.h[who])
    assert r.status_code == 201, r.text
    return r.json()


async def _list(anon, team, query="", who="alice"):
    return await anon.get(_url(team, query), headers=team.h[who])


def _cache(response) -> str:
    return response.headers["x-cache"]


def _titles(response) -> list[str]:
    return [t["title"] for t in response.json()["items"]]


# ------------------------------------------------------------------ hit / miss
async def test_miss_then_hit_with_identical_body(redis_cache, team, anon):
    await _mk(anon, team, "t1")
    first, second = await _list(anon, team), await _list(anon, team)
    assert (_cache(first), _cache(second)) == ("MISS", "HIT")
    assert first.json() == second.json()
    assert second.json()["total"] == 1 and second.json()["pages"] == 1


async def test_hit_is_served_without_touching_the_database(redis_cache, team, anon, monkeypatch):
    await _mk(anon, team, "t1")
    await _list(anon, team)  # làm nóng cache

    async def boom(*args, **kwargs):
        raise AssertionError("HIT mà vẫn query DB")

    monkeypatch.setattr(TaskRepository, "list_by_project", boom)
    monkeypatch.setattr(TaskRepository, "count_by_project", boom)
    r = await _list(anon, team)
    assert r.status_code == 200 and _cache(r) == "HIT" and _titles(r) == ["t1"]


async def test_each_filter_and_page_has_its_own_entry(redis_cache, team, anon):
    for i in range(3):
        await _mk(anon, team, f"t{i}", priority="HIGH" if i else "LOW")
    queries = ["", "?priority=HIGH", "?page=2&limit=1", "?status=TODO&priority=HIGH"]
    for q in queries:
        assert _cache(await _list(anon, team, q)) == "MISS", q
    for q in queries:
        assert _cache(await _list(anon, team, q)) == "HIT", q
    assert _titles(await _list(anon, team, "?priority=HIGH")) == ["t1", "t2"]


async def test_cache_disabled_reports_bypass(team, anon):
    """Không có Redis (NullCache): vẫn chạy bình thường, header báo BYPASS."""
    await _mk(anon, team, "t1")
    r = await _list(anon, team)
    assert r.status_code == 200 and _cache(r) == "BYPASS" and _titles(r) == ["t1"]


# ------------------------------------------------------------------ vô hiệu hoá
async def test_create_invalidates(redis_cache, team, anon):
    await _mk(anon, team, "t1")
    assert _cache(await _list(anon, team)) == "MISS"
    assert _cache(await _list(anon, team)) == "HIT"
    await _mk(anon, team, "t2")
    after = await _list(anon, team)
    assert _cache(after) == "MISS" and _titles(after) == ["t1", "t2"] and after.json()["total"] == 2


async def test_update_invalidates_and_filter_results_follow(redis_cache, team, anon):
    task = await _mk(anon, team, "t1")
    assert _titles(await _list(anon, team, "?status=DONE")) == []
    await _list(anon, team, "?status=DONE")  # HIT, danh sách rỗng
    await anon.patch(f"{TASKS}/{task['id']}", json={"status": "DONE"}, headers=team.h["bob"])
    after = await _list(anon, team, "?status=DONE")
    assert _cache(after) == "MISS" and _titles(after) == ["t1"]


async def test_delete_invalidates(redis_cache, team, anon):
    task = await _mk(anon, team, "t1")
    await _list(anon, team)
    await anon.delete(f"{TASKS}/{task['id']}", headers=team.h["alice"])
    after = await _list(anon, team)
    assert _cache(after) == "MISS" and after.json()["total"] == 0


async def test_assignee_change_invalidates(redis_cache, team, anon):
    task = await _mk(anon, team, "t1")
    bob = team.ids["bob"]
    assert _titles(await _list(anon, team, f"?assignee_id={bob}")) == []
    await anon.patch(f"{TASKS}/{task['id']}", json={"assignee_id": bob}, headers=team.h["alice"])
    assert _titles(await _list(anon, team, f"?assignee_id={bob}")) == ["t1"]


async def test_label_attach_detach_rename_delete_invalidate(redis_cache, team, anon):
    h = team.h["alice"]
    task = await _mk(anon, team, "t1")
    label = (
        await anon.post(f"{PRJ}/{team.project['id']}/labels", json={"name": "bug"}, headers=h)
    ).json()

    async def labels_in_list():
        r = await _list(anon, team)
        return [lb["name"] for lb in r.json()["items"][0]["labels"]]

    assert await labels_in_list() == []
    await anon.post(f"{TASKS}/{task['id']}/labels/{label['id']}", headers=h)
    assert await labels_in_list() == ["bug"]  # gắn
    await anon.patch(f"/api/v1/labels/{label['id']}", json={"name": "defect"}, headers=h)
    assert await labels_in_list() == ["defect"]  # đổi tên (dữ liệu task cache có tên label)
    await anon.delete(f"{TASKS}/{task['id']}/labels/{label['id']}", headers=h)
    assert await labels_in_list() == []  # gỡ
    await anon.post(f"{TASKS}/{task['id']}/labels/{label['id']}", headers=h)
    assert await labels_in_list() == ["defect"]
    await anon.delete(f"/api/v1/labels/{label['id']}", headers=h)
    assert await labels_in_list() == []  # xoá hẳn label


async def test_invalidation_is_scoped_to_one_project(redis_cache, team, anon):
    other = (
        await anon.post(
            f"{WS}/{team.ws['id']}/projects", json={"name": "B"}, headers=team.h["alice"]
        )
    ).json()
    other_url = f"{PRJ}/{other['id']}/tasks"
    await anon.post(other_url, json={"title": "b1"}, headers=team.h["alice"])
    await _list(anon, team)
    await anon.get(other_url, headers=team.h["alice"])
    await _mk(anon, team, "a2")  # chỉ đổi project A
    assert _cache(await _list(anon, team)) == "MISS"
    assert _cache(await anon.get(other_url, headers=team.h["alice"])) == "HIT"


async def test_reused_project_id_never_serves_stale_data(redis_cache, team, anon):
    """SQLite dùng lại id của project vừa xoá: project mới không được thấy cache của project cũ."""
    h = team.h["alice"]
    old = (await anon.post(f"{WS}/{team.ws['id']}/projects", json={"name": "X"}, headers=h)).json()
    await anon.post(f"{PRJ}/{old['id']}/tasks", json={"title": "cũ"}, headers=h)
    assert (await anon.get(f"{PRJ}/{old['id']}/tasks", headers=h)).json()["total"] == 1
    await anon.delete(f"{PRJ}/{old['id']}", headers=h)
    new = (await anon.post(f"{WS}/{team.ws['id']}/projects", json={"name": "Y"}, headers=h)).json()
    assert new["id"] == old["id"], "kịch bản kiểm tra phải thực sự tái sử dụng id"
    fresh = await anon.get(f"{PRJ}/{new['id']}/tasks", headers=h)
    assert fresh.json()["total"] == 0 and fresh.json()["items"] == []


async def test_reused_id_after_workspace_cascade_delete_never_serves_stale(redis_cache, team, anon):
    """Xoá cả workspace xoá project bằng cascade (không đi qua ProjectService.delete), nên chỉ
    việc tăng version lúc TẠO project mới giữ được cache sạch khi id bị dùng lại."""
    h = team.h["alice"]
    ws_b = (await anon.post(WS, json={"name": "B"}, headers=h)).json()
    old = (await anon.post(f"{WS}/{ws_b['id']}/projects", json={"name": "X"}, headers=h)).json()
    await anon.post(f"{PRJ}/{old['id']}/tasks", json={"title": "cũ"}, headers=h)
    assert (await anon.get(f"{PRJ}/{old['id']}/tasks", headers=h)).json()["total"] == 1
    assert (await anon.delete(f"{WS}/{ws_b['id']}", headers=h)).status_code == 204
    ws_c = (await anon.post(WS, json={"name": "C"}, headers=h)).json()
    new = (await anon.post(f"{WS}/{ws_c['id']}/projects", json={"name": "Y"}, headers=h)).json()
    assert new["id"] == old["id"], "kịch bản kiểm tra phải thực sự tái sử dụng id"
    fresh = await anon.get(f"{PRJ}/{new['id']}/tasks", headers=h)
    assert fresh.json()["total"] == 0 and fresh.json()["items"] == []


# ------------------------------------------------------------------ bảo mật
async def test_permissions_are_checked_before_cache(redis_cache, team, anon):
    await _mk(anon, team, "t1")
    await _list(anon, team)  # cache đã nóng
    assert _cache(await _list(anon, team, who="carol")) == "HIT"  # VIEWER vẫn đọc được
    outsider = await _list(anon, team, who="dave")
    assert outsider.status_code == 404 and "x-cache" not in outsider.headers
    assert (await anon.get(_url(team))).status_code == 401  # chưa đăng nhập
    # bị gỡ khỏi workspace là mất quyền ngay, dù cache vẫn còn
    await anon.delete(f"{WS}/{team.ws['id']}/members/{team.ids['carol']}", headers=team.h["alice"])
    assert (await _list(anon, team, who="carol")).status_code == 404


# ------------------------------------------------------------------ TTL
async def test_entries_expire_and_version_outlives_data(redis_cache, team, anon):
    await _mk(anon, team, "t1")  # tạo -> invalidate -> có key version
    await _list(anon, team)
    client = redis_cache._client
    data_keys = [k for k in await client.keys("tasks:p*")]
    assert len(data_keys) == 1
    assert 0 < await client.ttl(data_keys[0]) <= settings.CACHE_TTL_SECONDS
    version_key = f"tasks:ver:{team.project['id']}"
    assert await client.ttl(version_key) > settings.CACHE_TTL_SECONDS  # sống lâu hơn dữ liệu
    assert await client.ttl(version_key) <= VERSION_TTL_SECONDS


# ------------------------------------------------------------------ Redis hỏng
class BrokenCache:
    enabled = True

    async def get(self, key):
        raise ConnectionError("redis down")

    async def set(self, key, value, ttl):
        raise ConnectionError("redis down")

    async def incr(self, key, ttl):
        raise ConnectionError("redis down")

    async def close(self):
        return None


async def test_redis_outage_never_breaks_the_api(team, anon, caplog):
    from app.core.cache import get_cache_backend
    from app.main import app

    app.dependency_overrides[get_cache_backend] = BrokenCache
    caplog.set_level(logging.WARNING, logger="taskhub.cache")
    created = await anon.post(_url(team), json={"title": "vẫn tạo được"}, headers=team.h["alice"])
    assert created.status_code == 201  # ghi OK dù không vô hiệu hoá được cache
    r = await _list(anon, team)
    assert r.status_code == 200 and _titles(r) == ["vẫn tạo được"]
    assert _cache(r) == "MISS"  # chạy thẳng bằng DB
    patched = await anon.patch(
        f"{TASKS}/{created.json()['id']}", json={"status": "DONE"}, headers=team.h["alice"]
    )
    assert patched.status_code == 200
    assert any("Cache" in m for m in caplog.messages)  # có ghi cảnh báo để vận hành biết


# ------------------------------------------------------------------ TaskListCache (đơn vị)
async def test_write_under_stale_version_is_invisible_after_invalidate(redis_cache):
    """Race: đọc version, query DB, trong lúc đó có người ghi (invalidate), rồi mới set cache.
    Dữ liệu cũ nằm dưới version cũ nên không ai đọc được."""
    cache = TaskListCache(redis_cache, ttl=60)
    params = TaskListParams(page=1, limit=20)
    old_version = await cache.version(7)
    await cache.invalidate(7)  # có ghi xen giữa
    stale = Page[TaskRead](items=[], total=99, page=1, limit=20)
    await cache.set(7, old_version, params, stale)  # ghi dưới version cũ
    new_version = await cache.version(7)
    assert new_version == old_version + 1
    assert await cache.get(7, new_version, params) is None


async def test_cache_key_is_readable_and_deterministic():
    params = TaskListParams(page=2, limit=10, assignee_id=5)
    assert params.key_part == "status=*&priority=*&assignee=5&label=*&page=2&limit=10"
    assert params.skip == 10
    assert TaskListCache._data_key(3, 4, params) == f"tasks:p3:v4:{params.key_part}"


@pytest.mark.parametrize("ttl", [30, 60])
async def test_ttl_comes_from_settings(redis_cache, team, anon, monkeypatch, ttl):
    monkeypatch.setattr(settings, "CACHE_TTL_SECONDS", ttl)
    await _mk(anon, team, "t1")
    await _list(anon, team)
    key = (await redis_cache._client.keys("tasks:p*"))[0]
    assert ttl - 5 < await redis_cache._client.ttl(key) <= ttl
