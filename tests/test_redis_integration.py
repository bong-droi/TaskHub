"""Chạy với Redis THẬT (fakeredis chỉ mô phỏng). Mặc định bị bỏ qua, bật bằng:

    docker run -d -p 6379:6379 redis:7
    TEST_REDIS_URL=redis://localhost:6379/15 pytest tests/test_redis_integration.py

PowerShell:  $env:TEST_REDIS_URL = "redis://localhost:6379/15"
Dùng database số 15 vì test sẽ FLUSHDB để dọn dẹp.
"""

import os
import uuid

import pytest

from app.core.cache import RedisCache
from app.schemas.common import Page
from app.schemas.task import TaskRead
from app.services.task_cache import TaskListCache, TaskListParams

REDIS_URL = os.getenv("TEST_REDIS_URL", "")
pytestmark = pytest.mark.skipif(not REDIS_URL, reason="đặt TEST_REDIS_URL để chạy với Redis thật")


@pytest.fixture
async def real_cache():
    backend = RedisCache.from_url(REDIS_URL)
    await backend._client.flushdb()
    yield backend
    await backend._client.flushdb()
    await backend.close()


async def test_set_get_and_ttl_on_real_redis(real_cache):
    key = f"it:{uuid.uuid4().hex}"
    await real_cache.set(key, "giá trị tiếng Việt", ttl=30)
    assert await real_cache.get(key) == "giá trị tiếng Việt"
    assert 0 < await real_cache._client.ttl(key) <= 30
    assert await real_cache.get("khong-co") is None


async def test_incr_is_atomic_and_always_has_ttl(real_cache):
    values = [await real_cache.incr("it:ver", ttl=100) for _ in range(3)]
    assert values == [1, 2, 3]
    assert 0 < await real_cache._client.ttl("it:ver") <= 100  # INCR+EXPIRE cùng transaction


async def test_task_list_cache_roundtrip_and_invalidate(real_cache):
    cache = TaskListCache(real_cache, ttl=30)
    params = TaskListParams(page=1, limit=20)
    page = Page[TaskRead](items=[], total=0, page=1, limit=20)
    version = await cache.version(1)
    await cache.set(1, version, params, page)
    hit = await cache.get(1, version, params)
    assert hit is not None and hit.total == 0 and hit.pages == 0
    await cache.invalidate(1)
    assert await cache.get(1, await cache.version(1), params) is None
