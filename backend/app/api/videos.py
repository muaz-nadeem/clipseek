"""Video status, list, re-index, and delete endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.api.schemas import VideoListResponse, VideoStatusResponse
from app.database.connection import db_session
from app.database import models
from app.services.storage import get_storage
from app.workers.queue import enqueue_indexing

router = APIRouter(prefix="/videos", tags=["videos"])


def _to_status(video: models.VideoRecord) -> VideoStatusResponse:
    return VideoStatusResponse(
        video_id=video.id,
        filename=video.filename,
        status=video.status,
        duration=video.duration,
        error_message=video.error_message,
        created_at=video.created_at,
        indexed_at=video.indexed_at,
        progress=video.progress,
        object_count=video.object_count,
    )


@router.get("/", response_model=VideoListResponse)
def list_videos(user: models.UserRecord = Depends(get_current_user)) -> VideoListResponse:
    with db_session() as conn:
        videos = models.list_videos(conn, user_id=user.id)
    return VideoListResponse(videos=[_to_status(v) for v in videos])


@router.get("/{video_id}", response_model=VideoStatusResponse)
def get_video(
    video_id: int,
    user: models.UserRecord = Depends(get_current_user),
) -> VideoStatusResponse:
    with db_session() as conn:
        video = models.get_video(conn, video_id)
        if video is None or (video.user_id is not None and video.user_id != user.id):
            raise HTTPException(status_code=404, detail="Video not found")
    return _to_status(video)


@router.post("/{video_id}/index", response_model=VideoStatusResponse)
def reindex_video(
    video_id: int,
    user: models.UserRecord = Depends(get_current_user),
) -> VideoStatusResponse:
    with db_session() as conn:
        video = models.get_video(conn, video_id)
        if video is None or (video.user_id is not None and video.user_id != user.id):
            raise HTTPException(status_code=404, detail="Video not found")
        models.update_video_status(conn, video_id, "queued", error_message=None)

    try:
        enqueue_indexing(video_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    with db_session() as conn:
        video = models.get_video(conn, video_id)
    assert video is not None
    return _to_status(video)


@router.delete("/{video_id}")
def delete_video(
    video_id: int,
    user: models.UserRecord = Depends(get_current_user),
) -> dict:
    storage = get_storage()
    with db_session() as conn:
        video = models.get_video(conn, video_id)
        if video is None or (video.user_id is not None and video.user_id != user.id):
            raise HTTPException(status_code=404, detail="Video not found")
        stored = video.stored_path
        models.delete_video(conn, video_id)
    storage.delete(stored)
    return {"ok": True}
