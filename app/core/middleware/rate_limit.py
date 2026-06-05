"""Redis fixed-window rate limiter, used as a route dependency.

    @router.post("/login", dependencies=[Depends(RateLimiter(settings.rate_limit_auth))])

Keyed by (route, identity, window) where identity = user id when authenticated
else client IP. Disabled wholesale via ``RATE_LIMIT_ENABLED=false``.
"""

from __future__ import annotations

from fastapi import Request

from app.core import context as ctx
from app.core.cache import get_redis
from app.core.config import settings
from app.shared.exceptions import RateLimitError

_UNITS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def parse_rate(spec: str) -> tuple[int, int]:
    """'10/minute' -> (10, 60)."""
    times, _, unit = spec.partition("/")
    return int(times), _UNITS[unit.strip().rstrip("s")]


class RateLimiter:
    def __init__(self, spec: str | None = None) -> None:
        self.times, self.seconds = parse_rate(spec or settings.rate_limit_default)

    async def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled:
            return

        redis = get_redis()
        if redis is None:
            return

        rc = ctx.get_context()
        identity = (
            str(rc.user_id) if rc and rc.user_id else (rc.ip_address if rc else None)
        ) or "anon"
        route = request.scope.get("route")
        path = getattr(route, "path", request.url.path)

        redis = get_redis()
        key = f"rl:{path}:{identity}"
        # fixed window via INCR + first-hit EXPIRE
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, self.seconds)
        if count > self.times:
            ttl = await redis.ttl(key)
            raise RateLimitError(
                f"Rate limit exceeded ({self.times}/{self.seconds}s)",
                details={"retry_after": max(ttl, 1)},
            )
