"""RQ queue. Without Redis, indexing runs in a background thread."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Callable

from app.config import REDIS_URL, REQUIRE_REDIS

logger = logging.getLogger(__name__)

_QUEUE = None
_LOCAL_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="video-index")


def _try_queue():
    global _QUEUE
    if _QUEUE is not None:
        return _QUEUE
    try:
        from redis import Redis
        from redis.backoff import NoBackoff
        from redis.retry import Retry
        from rq import Queue

        conn = Redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5,
                              retry=Retry(NoBackoff(), 0))
        conn.ping()
        _QUEUE = Queue("indexing", connection=conn, default_timeout="2h")
        logger.info("Connected to Redis for RQ indexing queue")
        return _QUEUE
    except Exception as exc:
        logger.warning("Redis/RQ unavailable: %s", exc)
        _QUEUE = None
        return None


def enqueue_indexing(video_id: int, *, fallback: Callable[[int], None] | None = None) -> str:
    from app.workers.jobs import index_video_job

    queue = _try_queue()
    if queue is not None:
        queue.enqueue(
            index_video_job,
            video_id,
            job_timeout="2h",
            failure_ttl=86400,
            retry=None,
            result_ttl=86400,
        )
        return "rq"

    if REQUIRE_REDIS:
        raise RuntimeError("Redis is required for indexing in this environment")

    if fallback is not None:
        fallback(video_id)
        return "inline"

    logger.info("Starting inline indexing thread for video %s", video_id)
    # Serialize local inference: concurrent jobs compete for CPU and share YOLO.
    _LOCAL_EXECUTOR.submit(index_video_job, video_id)
    return "inline"


def redis_available() -> bool:
    try:
        from redis import Redis

        Redis.from_url(REDIS_URL, socket_connect_timeout=2).ping()
        return True
    except Exception:
        return False
