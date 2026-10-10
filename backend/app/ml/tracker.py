"""ByteTrack multi-object tracker wrapper."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import ultralytics
from ultralytics.cfg import IterableSimpleNamespace
from ultralytics.trackers.byte_tracker import BYTETracker
from ultralytics.utils import YAML


class ObjectTracker:
    def __init__(self, frame_rate: float = 30.0) -> None:
        self.frame_rate = frame_rate
        cfg_path = Path(ultralytics.__file__).parent / "cfg" / "trackers" / "bytetrack.yaml"
        cfg = YAML.load(cfg_path)
        cfg["track_buffer"] = max(1, round(cfg["track_buffer"] * frame_rate / 30))
        self.tracker = BYTETracker(IterableSimpleNamespace(**cfg))

    def update(self, boxes, frame: np.ndarray) -> np.ndarray:
        """Return tracks as ndarray rows: x1,y1,x2,y2,track_id,score,cls,det_idx."""
        # ByteTrack uses NumPy even when detector inference runs on CUDA.
        return self.tracker.update(boxes.cpu().numpy(), img=frame)

    def reset(self) -> None:
        cfg_path = Path(ultralytics.__file__).parent / "cfg" / "trackers" / "bytetrack.yaml"
        cfg = YAML.load(cfg_path)
        cfg["track_buffer"] = max(1, round(cfg["track_buffer"] * self.frame_rate / 30))
        self.tracker = BYTETracker(IterableSimpleNamespace(**cfg))
