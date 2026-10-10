"""RQ job entrypoints."""

from __future__ import annotations

from app.services.indexing_service import indexing_service


def index_video_job(video_id: int) -> None:
    indexing_service.index_video(video_id)
