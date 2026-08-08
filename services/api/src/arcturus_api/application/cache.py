"""Cache port used by application services.

Values are JSON strings; services own (de)serialization via pydantic. A cache
failure must never break a request — implementations swallow their own errors
and behave as a miss.
"""

from typing import Protocol


class CachePort(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int) -> None: ...


class NullCache:
    """No-op cache for tests and cache-less deployments."""

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        return None
