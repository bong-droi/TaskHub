import logging
import re

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError

from app.core.constants import DATA_CONFLICT, INTERNAL_ERROR
from app.main import app

HEALTH = "/api/v1/health"


async def test_every_response_has_request_id_and_process_time(anon):
    r = await anon.get(HEALTH)
    assert re.fullmatch(r"[0-9a-f]{32}", r.headers["x-request-id"])
    assert re.fullmatch(r"\d+\.\d+ms", r.headers["x-process-time"])
    other = await anon.get(HEALTH)
    assert other.headers["x-request-id"] != r.headers["x-request-id"]  # mỗi request một id


async def test_error_responses_also_carry_request_id(anon):
    for r in (await anon.get("/api/v1/khong-ton-tai"), await anon.get("/api/v1/tasks")):
        assert r.status_code in (401, 404) and "x-request-id" in r.headers


async def test_valid_client_request_id_is_echoed(anon):
    r = await anon.get(HEALTH, headers={"X-Request-ID": "trace-abc_123.x"})
    assert r.headers["x-request-id"] == "trace-abc_123.x"


@pytest.mark.parametrize("bad", ["has space", "x" * 65, "semi;colon", "<script>"])
async def test_unsafe_client_request_id_is_replaced(anon, bad):
    r = await anon.get(HEALTH, headers={"X-Request-ID": bad})
    assert r.headers["x-request-id"] != bad
    assert re.fullmatch(r"[0-9a-f]{32}", r.headers["x-request-id"])


async def test_access_log_line(anon, caplog):
    caplog.set_level(logging.INFO, logger="taskhub.access")
    r = await anon.get(HEALTH, headers={"X-Request-ID": "log-me"})
    assert r.status_code == 200
    assert any("GET /api/v1/health -> 200" in m and "rid=log-me" in m for m in caplog.messages)


# ------------------------------------------------------------ exception handlers
@pytest.fixture
def boom_routes():
    """Gắn tạm 2 route lỗi vào app, gỡ ra sau khi test xong."""

    async def unexpected():
        raise RuntimeError("secret internal detail: password=hunter2")

    async def integrity():
        raise IntegrityError("INSERT ...", {}, Exception("UNIQUE constraint failed"))

    before = len(app.router.routes)
    app.add_api_route("/__boom", unexpected)
    app.add_api_route("/__integrity", integrity)
    yield
    del app.router.routes[before:]


@pytest.fixture
async def lenient_client():
    """Client không re-raise exception của app, để kiểm tra response 500 thật sự."""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def test_unhandled_error_returns_generic_500_without_leaking(
    boom_routes, lenient_client, caplog
):
    r = await lenient_client.get("/__boom", headers={"X-Request-ID": "rid-500"})
    assert r.status_code == 500
    body = r.json()
    assert body == {"detail": INTERNAL_ERROR, "request_id": "rid-500"}
    assert "hunter2" not in r.text and "RuntimeError" not in r.text  # không lộ chi tiết nội bộ
    assert r.headers["x-request-id"] == "rid-500"
    # chi tiết đầy đủ chỉ nằm trong log, kèm request id để tra cứu
    assert any("rid=rid-500" in m for m in caplog.messages)
    assert any(rec.exc_info and "hunter2" in str(rec.exc_info[1]) for rec in caplog.records)


async def test_integrity_error_becomes_409(boom_routes, lenient_client):
    r = await lenient_client.get("/__integrity")
    assert r.status_code == 409 and r.json() == {"detail": DATA_CONFLICT}
    assert "UNIQUE" not in r.text
