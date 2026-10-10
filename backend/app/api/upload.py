"""POST /videos/upload — accept file, save, enqueue indexing."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.api.schemas import VideoUploadResponse
from app.config import (
    ALLOWED_VIDEO_EXTENSIONS,
    MAX_ACTIVE_INDEX_JOBS,
    MAX_DURATION_SEC,
    MAX_UPLOAD_BYTES,
    VIDEOS_DIR,
)
from app.database.connection import db_session
from app.database import models
from app.services.storage import get_storage
from app.utils.index_policy import duration_exceeds_limit
from app.utils.video import probe_duration
from app.workers.queue import enqueue_indexing

router = APIRouter(prefix="/videos", tags=["upload"])


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: UploadFile = File(...),
    user: models.UserRecord = Depends(get_current_user),
) -> VideoUploadResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}",
        )

    with db_session() as conn:
        active = models.count_active_jobs(conn, user.id)
    if active >= MAX_ACTIVE_INDEX_JOBS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many videos indexing (max {MAX_ACTIVE_INDEX_JOBS}). Wait and retry.",
        )

    dest_name = f"{uuid.uuid4().hex}{suffix}"
    dest_path = VIDEOS_DIR / dest_name
    total = 0
    try:
        with dest_path.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File too large")
                out.write(chunk)
    except HTTPException:
        if dest_path.exists():
            dest_path.unlink()
        raise
    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc
    finally:
        await file.close()

    duration = await run_in_threadpool(probe_duration, str(dest_path))
    if duration_exceeds_limit(duration, MAX_DURATION_SEC):
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail=f"Video is {duration / 60:.1f} minutes long; the limit is {MAX_DURATION_SEC / 60:g} minutes.",
        )

    storage = get_storage()
    stored = storage.put_file(f"videos/{dest_name}", dest_path)

    with db_session() as conn:
        video = models.create_video(
            conn,
            filename=file.filename,
            stored_path=stored,
            user_id=user.id,
            status="queued",
        )
        video_id = video.id

    try:
        enqueue_indexing(video_id)
    except RuntimeError as exc:
        with db_session() as conn:
            models.update_video_status(conn, video_id, "failed", error_message=str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return VideoUploadResponse(
        video_id=video_id,
        filename=file.filename,
        status="queued",
    )
