"""Semantic search orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import CLIP_PADDING_SEC, SEARCH_MIN_SCORE, SEARCH_SCORE_MARGIN
from app.database.connection import db_session
from app.database import models
from app.services.clip_service import clip_service
from app.services.storage import get_storage
from app.services.search_cluster import cluster_appearances, filter_relevant_matches, search_class_names
from app.utils.video import format_timestamp, probe_duration


@dataclass
class SearchHit:
    video_id: int
    track_id: int
    class_name: str
    score: float
    confidence: float
    match_time: float
    start: float
    end: float
    start_label: str
    end_label: str
    object_id: int
    bounding_box: list[float]
    clip_url: str


class SearchService:
    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        offset: int = 0,
        video_id: int | None = None,
        padding_sec: float | None = None,
        class_names: list[str] | None = None,
        min_score: float = SEARCH_MIN_SCORE,
        appearance_gap_sec: float = 10.0,
        user_id: int | None = None,
    ) -> list[SearchHit]:
        padding = CLIP_PADDING_SEC if padding_sec is None else padding_sec
        effective_classes = search_class_names(query, class_names)
        query_emb = clip_service.embed_text(query)

        with db_session() as conn:
            if video_id is not None and user_id is not None:
                video = models.get_video(conn, video_id)
                if video is None or (video.user_id is not None and video.user_id != user_id):
                    return []

            raw = models.search_objects_by_embedding(
                conn,
                query_emb,
                top_k=max((top_k + offset) * 8, 40),
                video_id=video_id,
                class_names=effective_classes,
                user_id=user_id,
            )
            raw = filter_relevant_matches(
                raw, min_score=min_score, score_margin=SEARCH_SCORE_MARGIN,
            )
            merged = cluster_appearances(
                raw,
                top_k=top_k + offset,
                appearance_gap_sec=appearance_gap_sec,
            )[offset : offset + top_k]

            duration_cache: dict[int, float | None] = {}
            hits: list[SearchHit] = []
            for row in merged:
                vid = int(row["video_id"])
                if vid not in duration_cache:
                    video = models.get_video(conn, vid)
                    if video is None:
                        duration_cache[vid] = None
                    else:
                        duration_cache[vid] = video.duration or probe_duration(
                            str(get_storage().local_path(video.stored_path, "videos"))
                        )

                match_time = float(row["timestamp"])
                start = max(0.0, match_time - padding)
                end = match_time + padding
                duration = duration_cache[vid]
                if duration is not None:
                    end = min(end, duration)

                clip_url = f"/clips?video_id={vid}&start={start:.3f}&end={end:.3f}"
                hits.append(
                    SearchHit(
                        video_id=vid,
                        track_id=int(row["track_id"]),
                        class_name=row["class_name"],
                        score=float(row["score"]),
                        confidence=float(row["confidence"]),
                        match_time=match_time,
                        start=start,
                        end=end,
                        start_label=format_timestamp(start),
                        end_label=format_timestamp(end),
                        object_id=int(row["object_id"]),
                        bounding_box=[float(x) for x in row["bounding_box"]],
                        clip_url=clip_url,
                    )
                )
            return hits


search_service = SearchService()
