"""Clip streaming endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from app.api.deps import get_current_user
from app.database.connection import db_session
from app.database import models
from app.services.clip_extract_service import clip_extract_service

router = APIRouter(tags=["clips"])


@router.get("/clips")
def get_clip(
    video_id: int = Query(...),
    start: float = Query(..., ge=0),
    end: float = Query(...),
    user: models.UserRecord = Depends(get_current_user),
):
    with db_session() as conn:
        video = models.get_video(conn, video_id)
        if video is None or (video.user_id is not None and video.user_id != user.id):
            raise HTTPException(status_code=404, detail="Video not found")

    try:
        path = clip_extract_service.extract_clip(video_id, start, end)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clip extraction failed: {exc}") from exc

    return FileResponse(
        path,
        media_type="video/webm",
        filename=path.name,
    )
