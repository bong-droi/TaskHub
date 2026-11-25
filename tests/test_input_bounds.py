"""Số nguyên đầu vào không có giới hạn từng làm DB báo lỗi và API trả 500 (review PR #5).

Thay vì chỉ test 2 chỗ reviewer nêu, test này QUÉT TOÀN BỘ endpoint theo schema OpenAPI của app
(API công khai, ổn định giữa các phiên bản FastAPI): endpoint nào được thêm sau này mà quên giới
hạn id/page sẽ bị bắt ngay.
"""

import re

import pytest

from app.core.constants import MAX_DB_ID, MAX_PAGE_LIMIT, MAX_PAGE_NUMBER
from app.main import app

BAD_IDS = ["0", "-1", "-3", str(MAX_DB_ID + 1), "99999999999999999999"]
BAD_PAGES = ["0", "-1", str(MAX_PAGE_NUMBER + 1), "1000000000000000000"]
BAD_FILTER_IDS = ["0", "-1", str(MAX_DB_ID + 1), "100000000000000000000"]
BODY_METHODS = {"POST", "PATCH", "PUT"}
OPENAPI = app.openapi()


def _int_schema(schema: dict) -> dict | None:
    """Phần kiểu số nguyên của schema (field nullable nằm trong anyOf)."""
    if schema.get("type") == "integer":
        return schema
    return next((s for s in schema.get("anyOf", []) if s.get("type") == "integer"), None)


def _operations():
    """(path, METHOD, [tham số]) của mọi endpoint /api/v1."""
    for path, item in OPENAPI["paths"].items():
        if not path.startswith("/api/v1"):
            continue
        for method, op in item.items():
            yield path, method.upper(), op.get("parameters", [])


def _int_params(where: str, only: set[str] | None = None):
    return [
        (path, method, p["name"], _int_schema(p["schema"]))
        for path, method, params in _operations()
        for p in params
        if p["in"] == where and _int_schema(p["schema"]) and (only is None or p["name"] in only)
    ]


def _fill(path: str, **values: str) -> str:
    return re.sub(r"\{(\w+)\}", lambda m: values.get(m.group(1), "1"), path)


PATH_PARAMS = _int_params("path")
PAGE_PARAMS = _int_params("query", {"page"})
FILTER_PARAMS = _int_params("query", {"assignee_id", "label_id"})
PATH_CASES = [(p, m, n, bad) for p, m, n, _ in PATH_PARAMS for bad in BAD_IDS]
PAGE_CASES = [(p, n, bad) for p, _, n, _ in PAGE_PARAMS for bad in BAD_PAGES]
FILTER_CASES = [(p, n, bad) for p, _, n, _ in FILTER_PARAMS for bad in BAD_FILTER_IDS]


def _errors(response, where: str, name: str) -> list[dict]:
    return [e for e in response.json()["detail"] if e["loc"][:2] == [where, name]]


def test_the_sweep_actually_covers_the_app():
    """Chống test rỗng: nếu việc quét route hỏng thì các test bên dưới sẽ không chạy gì."""
    assert len(PATH_PARAMS) >= 29 and len(PAGE_PARAMS) >= 6 and len(FILTER_PARAMS) >= 2


def test_every_integer_path_and_filter_param_has_both_bounds_in_the_schema():
    """Kiểm tra tĩnh trên OpenAPI: có cận dưới (>= 1) VÀ cận trên (<= MAX_DB_ID)."""
    for path, method, name, schema in PATH_PARAMS + FILTER_PARAMS:
        assert schema.get("minimum") == 1, f"{method} {path} {name}: thiếu cận dưới"
        assert schema.get("maximum") == MAX_DB_ID, f"{method} {path} {name}: thiếu cận trên"
    for path, _, _name, schema in PAGE_PARAMS:
        assert schema.get("minimum") == 1 and schema.get("maximum") == MAX_PAGE_NUMBER, path


@pytest.mark.parametrize(("path", "method", "name", "bad"), PATH_CASES)
async def test_invalid_path_id_is_422_on_every_route(client, path, method, name, bad):
    url = _fill(path, **{name: bad})
    r = await client.request(method, url, json={} if method in BODY_METHODS else None)
    assert r.status_code == 422, f"{method} {url} -> {r.status_code}"
    assert _errors(r, "path", name), r.text


@pytest.mark.parametrize(("path", "method", "name"), sorted({c[:3] for c in PATH_CASES}))
async def test_largest_valid_id_is_accepted_not_500(client, path, method, name):
    url = _fill(path, **{name: str(MAX_DB_ID)})
    r = await client.request(method, url, json={} if method in BODY_METHODS else None)
    assert r.status_code < 500, f"{method} {url} -> {r.status_code}"
    if r.status_code == 422:
        assert not _errors(r, "path", name)  # có 422 thì phải do body, không phải do id hợp lệ


@pytest.mark.parametrize(("path", "name", "bad"), PAGE_CASES)
async def test_invalid_page_is_422_on_every_list_route(client, path, name, bad):
    r = await client.get(f"{_fill(path)}?page={bad}")
    assert r.status_code == 422, f"{path}?page={bad} -> {r.status_code}"
    assert _errors(r, "query", "page"), r.text


@pytest.mark.parametrize("path", sorted({c[0] for c in PAGE_CASES}))
async def test_largest_page_is_accepted_and_empty_not_500(client, path):
    await client.post("/api/v1/projects/1/tasks", json={"title": "để task 1 tồn tại"})
    url = f"{_fill(path)}?page={MAX_PAGE_NUMBER}&limit={MAX_PAGE_LIMIT}"
    r = await client.get(url)
    assert r.status_code == 200, f"{url} -> {r.status_code}"  # offset 10 triệu vẫn an toàn
    assert r.json()["items"] == [] and r.json()["page"] == MAX_PAGE_NUMBER


@pytest.mark.parametrize(("path", "name", "bad"), FILTER_CASES)
async def test_invalid_filter_ids_are_422(client, path, name, bad):
    r = await client.get(f"{_fill(path)}?{name}={bad}")
    assert r.status_code == 422 and _errors(r, "query", name), r.text


# ---------------------------------------------------------------- id trong body
BAD_BODY_IDS = [0, -1, MAX_DB_ID + 1, 10**20]


@pytest.mark.parametrize("bad", BAD_BODY_IDS)
async def test_invalid_ids_in_json_body_are_422(client, seeded, bad):
    pid = seeded["project_id"]
    legacy = await client.post("/api/v1/tasks", json={"title": "x", "project_id": bad})
    assert legacy.status_code == 422 and _errors(legacy, "body", "project_id")
    nested = await client.post(
        f"/api/v1/projects/{pid}/tasks", json={"title": "x", "assignee_id": bad}
    )
    assert nested.status_code == 422 and _errors(nested, "body", "assignee_id")
    task = (await client.post(f"/api/v1/projects/{pid}/tasks", json={"title": "x"})).json()
    patched = await client.patch(f"/api/v1/tasks/{task['id']}", json={"assignee_id": bad})
    assert patched.status_code == 422 and _errors(patched, "body", "assignee_id")


# ---------------------------------------------------------------- đúng 2 ca reviewer nêu
@pytest.mark.parametrize("project_id", [0, -3])
async def test_review_case_post_task_to_project_zero_or_negative(client, project_id):
    r = await client.post(f"/api/v1/projects/{project_id}/tasks", json={"title": "x"})
    assert r.status_code == 422 and _errors(r, "path", "project_id")


async def test_review_case_huge_page_number(client):
    r = await client.get("/api/v1/tasks?page=1000000000000000000")
    assert r.status_code == 422 and _errors(r, "query", "page")


async def test_a_project_that_does_not_exist_is_404_not_422_or_500(client):
    r = await client.post(f"/api/v1/projects/{MAX_DB_ID}/tasks", json={"title": "x"})
    assert r.status_code == 404
