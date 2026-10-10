"""CLIP service — lazy singleton over the ML embedder."""

from __future__ import annotations

import threading

import numpy as np
from PIL import Image

from app.ml.embedder import ClipEmbedder


class ClipService:
    def __init__(self) -> None:
        self._embedder: ClipEmbedder | None = None
        self._lock = threading.Lock()

    def _get(self) -> ClipEmbedder:
        if self._embedder is None:
            with self._lock:
                if self._embedder is None:
                    self._embedder = ClipEmbedder()
        return self._embedder

    def embed_text(self, text: str) -> np.ndarray:
        return self._get().embed_text(text)

    def embed_image(self, image_rgb: Image.Image | np.ndarray) -> np.ndarray:
        return self._get().embed_image(image_rgb)

    def embed_images(self, images: list[Image.Image | np.ndarray]) -> np.ndarray:
        return self._get().embed_images(images)


clip_service = ClipService()
