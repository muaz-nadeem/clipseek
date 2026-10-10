"""Search endpoint — FastAPI only orchestrates; ML lives in services."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.api.schemas import SearchRequest, SearchResponse, SearchResult
from app.database import models
from app.services.search_service import search_service

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(
    body: SearchRequest,
    user: models.UserRecord = Depends(get_current_user),
) -> SearchResponse:
    hits = search_service.search(
        body.query,
        top_k=body.top_k,
        offset=body.offset,
        video_id=body.video_id,
        padding_sec=body.padding_sec,
        class_names=body.class_names,
        min_score=body.min_score,
        appearance_gap_sec=body.appearance_gap_sec,
        user_id=user.id,
    )
    return SearchResponse(
        query=body.query,
        results=[
            SearchResult(
                video_id=h.video_id,
                track_id=h.track_id,
                class_name=h.class_name,
                score=h.score,
                confidence=h.confidence,
                match_time=h.match_time,
                start=h.start,
                end=h.end,
                start_label=h.start_label,
                end_label=h.end_label,
                object_id=h.object_id,
                bounding_box=h.bounding_box,
                clip_url=h.clip_url,
            )
            for h in hits
        ],
    )
