"""YOLO object detection wrapper."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import torch
from ultralytics import YOLO

from app.config import YOLO_MODEL
from app.ml.runtime import configure_cpu_threads

logger = logging.getLogger(__name__)


class ObjectDetector:
    def __init__(self, model_path: str | None = None) -> None:
        self.model = YOLO(model_path or YOLO_MODEL)
        self.device: int | str = 0 if torch.cuda.is_available() else "cpu"
        self.half = self.device != "cpu"
        if not self.half:
            configure_cpu_threads()
        logger.info("YOLO running on %s", "cuda:0" if self.half else "cpu")

    def detect(self, frame: np.ndarray, conf: float = 0.25) -> Any:
        """Return Ultralytics Results[0] for a single BGR frame."""
        result = self.model(frame, conf=conf, verbose=False, device=self.device, half=self.half)[0]
        if not self.half:
            # First prediction initializes the backend and resets torch threads.
            configure_cpu_threads()
        return result
