"""Restart indexing that was interrupted when the API process stopped."""

from __future__ import annotations

import logging

from app.database.connection import db_session
from app.database import models
from app.workers.queue import enqueue_indexing, redis_available

logger = logging.getLogger(__name__)


def recover_unfinished_jobs() -> list[int]:
    # RQ keeps queued jobs in Redis; re-enqueueing would index them twice.
    if redis_available():
        return []
    with db_session() as conn:
        video_ids = models.list_unfinished_video_ids(conn)
        for video_id in video_ids:
            models.update_video_status(conn, video_id, "queued")
            models.update_video_progress(conn, video_id, 0.0)

    recovered: list[int] = []
    for video_id in video_ids:
        try:
            enqueue_indexing(video_id)
        except RuntimeError as exc:
            logger.warning("Could not re-queue video %s: %s", video_id, exc)
            with db_session() as conn:
                models.update_video_status(conn, video_id, "failed", error_message=str(exc))
            continue
        recovered.append(video_id)
    if recovered:
        logger.info("Re-queued interrupted indexing for videos %s", recovered)
    return recovered
