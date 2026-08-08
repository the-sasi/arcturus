"""Redis-backed cache adapter.

Fail-open by design: if Redis is down, every operation degrades to a cache
miss and the request proceeds against the live provider.
"""

import logging
from typing import cast

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, url: str) -> None:
        self._client: aioredis.Redis = aioredis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )

    async def get(self, key: str) -> str | None:
        try:
            # decode_responses=True guarantees str; the stubs can't see that
            return cast(str | None, await self._client.get(key))
        except Exception:
            logger.debug("cache get failed for %s", key, exc_info=True)
            return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            await self._client.set(key, value, ex=ttl_seconds)
        except Exception:
            logger.debug("cache set failed for %s", key, exc_info=True)

    async def close(self) -> None:
        try:
            await self._client.aclose()
        except Exception:
            logger.debug("cache close failed", exc_info=True)
