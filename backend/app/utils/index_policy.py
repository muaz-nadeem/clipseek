"""Indexing sampling and duration rules (no ML imports)."""

from __future__ import annotations

# Full-frame embeddings share the objects table; ByteTrack IDs are always positive.
SCENE_CLASS = "scene"
SCENE_TRACK_ID = -1


def index_stride_for_fps(
    fps: float,
    *,
    target_fps: float = 5.0,
    override: int | None = None,
) -> int:
    if override is not None:
        return max(int(override), 1)
    safe_fps = fps if fps and fps > 0 else 25.0
    safe_target = target_fps if target_fps and target_fps > 0 else 5.0
    return max(1, int(round(safe_fps / safe_target)))


def duration_exceeds_limit(duration: float | None, max_sec: float) -> bool:
    if duration is None:
        return False
    return float(duration) > float(max_sec)


def iter_sampled_frame_indices(total_frames: int, stride: int) -> list[int]:
    stride = max(int(stride), 1)
    return list(range(0, max(int(total_frames), 0), stride))
