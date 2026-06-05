"""Async Redis client + small helpers (used by licensing, RBAC, rate limiting).

Returns ``None`` when ``REDIS_URL`` is not set — callers must handle gracefully.
"""

from __future__ import annotations

import redis.asyncio as redis

from app.core.config import settings

_client: redis.Redis | None = None
_initialised: bool = False


def get_redis() -> redis.Redis | None:
    global _client, _initialised
    if not _initialised:
        _initialised = True
        if settings.redis_url:
            _client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _client


async def close_redis() -> None:
    global _client, _initialised
    if _client is not None:
        await _client.aclose()
        _client = None
    _initialised = False
