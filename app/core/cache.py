"""Cache backend: Redis (khi có REDIS_URL) hoặc NullCache (tắt cache).

Chỉ cần 3 thao tác: get / set có TTL / incr có TTL. `incr` dùng cho "version counter" để vô hiệu
hoá cả nhóm key mà không phải SCAN/xoá hàng loạt (xem services/task_cache.py).
"""

import logging
from typing import Protocol

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("taskhub.cache")

# Redis chậm/chết không được làm API treo: timeout ngắn, lỗi thì bỏ qua cache (xem TaskListCache)
SOCKET_TIMEOUT_SECONDS = 1.0


class CacheBackend(Protocol):
    enabled: bool

    async def get(self, key: str) -> str | None: ...
    async def set(self, key: str, value: str, ttl: int) -> None: ...
    async def incr(self, key: str, ttl: int) -> int: ...
    async def close(self) -> None: ...


class NullCache:
    """Cache bị tắt: luôn miss, ghi bỏ qua."""

    enabled = False

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl: int) -> None:
        return None

    async def incr(self, key: str, ttl: int) -> int:
        return 0

    async def close(self) -> None:
        return None


class RedisCache:
    enabled = True

    def __init__(self, client: Redis) -> None:
        self._client = client

    @classmethod
    def from_url(cls, url: str) -> "RedisCache":
        client = Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=SOCKET_TIMEOUT_SECONDS,
            socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
        )
        return cls(client)

    async def get(self, key: str) -> str | None:
        val = await self._client.get(key)
        return str(val) if val is not None else None

    async def set(self, key: str, value: str, ttl: int) -> None:
        await self._client.set(key, value, ex=ttl)

    async def incr(self, key: str, ttl: int) -> int:
        # INCR + EXPIRE trong cùng một transaction để không có lúc key tồn tại mà không có TTL
        async with self._client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, ttl)
            new_value, _ = await pipe.execute()
        return int(new_value)

    async def close(self) -> None:
        await self._client.aclose()


_backend: CacheBackend | None = None


def get_cache_backend() -> CacheBackend:
    """Singleton dùng chung cho cả app; test ghi đè bằng dependency_overrides."""
    global _backend
    if _backend is None:
        _backend = (
            RedisCache.from_url(settings.REDIS_URL) if settings.cache_enabled else NullCache()
        )
        logger.info("Cache: %s", "Redis" if settings.cache_enabled else "tắt (REDIS_URL trống)")
    return _backend


async def close_cache_backend() -> None:
    global _backend
    if _backend is not None:
        await _backend.close()
        _backend = None
