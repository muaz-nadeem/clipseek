"""Background video indexing pipeline (YOLO -> ByteTrack -> CLIP -> DB)."""

from __future__ import annotations

import logging
import threading
import time

import cv2
import numpy as np
from PIL import Image

from app.config import (
    CHANGE_THRESHOLD,
    INDEX_STRIDE,
    INDEX_TARGET_FPS,
    CLIP_BATCH_SIZE,
    EMBED_MIN_GAP_SEC,
    EMBED_HEARTBEAT_SEC,
    MAX_GAP_SEC,
    MAX_INDEX_FRAMES_INT,
    SCENE_INTERVAL_SEC,
)
from app.database.connection import db_session
from app.database import models
from app.ml.detector import ObjectDetector
from app.ml.embedding_gate import TrackEmbeddingGate
from app.ml.tracker import ObjectTracker
from app.ml.frame_gate import HashAppearanceGate
from app.utils.index_policy import SCENE_CLASS, SCENE_TRACK_ID, index_stride_for_fps
from app.services.clip_service import clip_service
from app.services.storage import get_storage
from app.utils.video import crop_bgr, probe_duration

logger = logging.getLogger(__name__)

_detector: ObjectDetector | None = None
_detector_lock = threading.Lock()


def _get_detector() -> ObjectDetector:
    global _detector
    if _detector is None:
        with _detector_lock:
            if _detector is None:
                _detector = ObjectDetector()
    return _detector


def warm_models() -> None:
    """Load YOLO and CLIP ahead of the first upload."""
    started = time.perf_counter()
    try:
        _get_detector().detect(np.zeros((64, 64, 3), dtype=np.uint8))
        clip_service.embed_text("warmup")
    except Exception:
        logger.exception("Model warmup failed; models will load on first index")
        return
    logger.info("Models warm in %.1fs", time.perf_counter() - started)


class IndexingService:
    def index_video(self, video_id: int) -> None:
        with db_session() as conn:
            video = models.get_video(conn, video_id)
            if video is None:
                logger.error("index_video: video %s not found", video_id)
                return
            models.update_video_status(conn, video_id, "processing")
            models.update_video_progress(conn, video_id, 0.0, object_count=0)
            stored_path = video.stored_path

        duration = None
        try:
            storage = get_storage()
            local_path = storage.local_path(stored_path, "videos")
            duration = probe_duration(str(local_path))
            inserted = self._run_pipeline(video_id, str(local_path), duration)
            with db_session() as conn:
                models.update_video_status(
                    conn,
                    video_id,
                    "completed",
                    duration=duration,
                    error_message=None,
                    mark_indexed=True,
                )
                models.update_video_progress(conn, video_id, 1.0, object_count=inserted)
            logger.info("Indexed video %s (%s embeddings stored)", video_id, inserted)
        except Exception as exc:
            logger.exception("Indexing failed for video %s", video_id)
            with db_session() as conn:
                models.update_video_status(
                    conn,
                    video_id,
                    "failed",
                    duration=duration,
                    error_message=str(exc),
                )
            raise

    def _run_pipeline(self, video_id: int, video_path: str, duration: float | None) -> int:
        cap = cv2.VideoCapture(video_path)
        started = time.perf_counter()
        sampled = embedded = inserted = 0
        detect_seconds = embed_seconds = 0.0
        try:
            if not cap.isOpened():
                raise RuntimeError(f"Could not open video: {video_path}")
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            stride = index_stride_for_fps(fps, target_fps=INDEX_TARGET_FPS, override=INDEX_STRIDE)
            detector = _get_detector()
            tracker = ObjectTracker(frame_rate=fps / stride)
            gate = TrackEmbeddingGate(threshold=CHANGE_THRESHOLD, max_gap_sec=MAX_GAP_SEC)
            appearance = HashAppearanceGate(max_gap_sec=EMBED_HEARTBEAT_SEC)
            last_embedded: dict[int, float] = {}
            last_scene = float("-inf")
            pending: list[tuple[Image.Image, dict]] = []
            frame_number = 0
            last_progress = time.monotonic()

            with db_session() as conn:
                models.delete_objects_for_video(conn, video_id)
                conn.commit()

                def flush() -> None:
                    nonlocal inserted, embedded, embed_seconds
                    if not pending:
                        return
                    before = time.perf_counter()
                    vectors = clip_service.embed_images([image for image, _ in pending])
                    embed_seconds += time.perf_counter() - before
                    embedded += len(pending)
                    for (_, row), vector in zip(pending, vectors, strict=True):
                        if gate.accept(row["track_id"], vector, row["timestamp"]).store:
                            models.insert_object(conn, video_id=video_id, embedding=vector, **row)
                            inserted += 1
                    pending.clear()

                while MAX_INDEX_FRAMES_INT is None or frame_number < MAX_INDEX_FRAMES_INT:
                    # grab() advances the decoder without materializing skipped BGR frames.
                    if not cap.grab():
                        break
                    current = frame_number
                    frame_number += 1
                    if current % stride != 0:
                        continue
                    ret, frame = cap.retrieve()
                    if not ret:
                        raise RuntimeError(f"Could not decode frame {current}")
                    timestamp = current / fps
                    before = time.perf_counter()
                    result = detector.detect(frame)
                    tracks = tracker.update(result.boxes, frame)
                    detect_seconds += time.perf_counter() - before
                    sampled += 1
                    for track in tracks:
                        x1, y1, x2, y2, track_id, score, cls_id, _ = track.tolist()
                        track_id = int(track_id)
                        if timestamp - last_embedded.get(track_id, float("-inf")) < EMBED_MIN_GAP_SEC:
                            continue
                        crop = crop_bgr(frame, x1, y1, x2, y2)
                        if crop is None or not appearance.accept(track_id, crop, timestamp).store:
                            continue
                        last_embedded[track_id] = timestamp
                        # Bound queued image memory while preserving crop aspect ratio.
                        rgb = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                        rgb.thumbnail((448, 448))
                        pending.append((rgb, dict(
                            track_id=track_id, class_name=result.names[int(cls_id)],
                            confidence=float(score), timestamp=timestamp, frame_number=current,
                            bounding_box=[float(x1), float(y1), float(x2), float(y2)],
                        )))
                        if len(pending) >= CLIP_BATCH_SIZE:
                            flush()
                    # Whole-frame vectors catch attributes the detector crops miss (caps, signs, colors).
                    if SCENE_INTERVAL_SEC > 0 and timestamp - last_scene >= SCENE_INTERVAL_SEC:
                        last_scene = timestamp
                        if appearance.accept(SCENE_TRACK_ID, frame, timestamp).store:
                            height, width = frame.shape[:2]
                            scene = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                            scene.thumbnail((448, 448))
                            pending.append((scene, dict(
                                track_id=SCENE_TRACK_ID, class_name=SCENE_CLASS,
                                confidence=1.0, timestamp=timestamp, frame_number=current,
                                bounding_box=[0.0, 0.0, float(width), float(height)],
                            )))
                            if len(pending) >= CLIP_BATCH_SIZE:
                                flush()
                    if time.monotonic() - last_progress >= 1.0:
                        # Progress reporting must not fragment inference batches.
                        # Pending crops are bounded by CLIP_BATCH_SIZE and flushed at EOF.
                        models.update_video_progress(conn, video_id,
                            min(frame_number / total, 0.99) if total else 0.0,
                            object_count=inserted)
                        conn.commit()
                        last_progress = time.monotonic()
                flush()
        finally:
            cap.release()
        logger.info(
            "Index metrics video=%s elapsed=%.2fs sampled=%s embedded=%s stored=%s detection=%.2fs clip=%.2fs",
            video_id, time.perf_counter() - started, sampled, embedded, inserted,
            detect_seconds, embed_seconds,
        )
        return inserted


indexing_service = IndexingService()
