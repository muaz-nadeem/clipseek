"""Small video helpers."""

from __future__ import annotations

import cv2
import numpy as np


def crop_bgr(frame: np.ndarray, x1: float, y1: float, x2: float, y2: float) -> np.ndarray | None:
    h, w = frame.shape[:2]
    left = max(int(np.floor(x1)), 0)
    top = max(int(np.floor(y1)), 0)
    right = min(int(np.ceil(x2)), w)
    bottom = min(int(np.ceil(y2)), h)
    if right <= left or bottom <= top:
        return None
    return frame[top:bottom, left:right]


def probe_duration(video_path: str) -> float | None:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    cap.release()
    if fps <= 0:
        return None
    return float(frames / fps)


def format_timestamp(seconds: float) -> str:
    total = max(int(seconds), 0)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"
