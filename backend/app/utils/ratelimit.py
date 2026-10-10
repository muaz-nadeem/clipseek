"""Simple sliding-window rate limiter (Redis when available, memory otherwise)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import AUTH_RATE_LIMIT, AUTH_RATE_WINDOW_SEC, REDIS_URL

_memory: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_auth_rate_limit(request: Request) -> None:
    key = f"auth:{_client_ip(request)}"
    if not allow(key, AUTH_RATE_LIMIT, AUTH_RATE_WINDOW_SEC):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many auth attempts. Try again shortly.",
        )


def allow(key: str, limit: int, window_sec: int) -> bool:
    now = time.time()
    try:
        from redis import Redis

        r = Redis.from_url(REDIS_URL, socket_connect_timeout=0.3)
        pipe = r.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_sec)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_sec)
        count = pipe.execute()[2]
        return int(count) <= limit
    except Exception:
        bucket = _memory[key]
        while bucket and bucket[0] < now - window_sec:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True
