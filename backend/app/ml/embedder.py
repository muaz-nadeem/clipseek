"""CLIP embedding wrapper (image + text)."""

from __future__ import annotations

import logging

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.config import CLIP_MODEL
from app.ml.runtime import configure_cpu_threads

logger = logging.getLogger(__name__)


class ClipEmbedder:
    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or CLIP_MODEL
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.device.type == "cpu":
            configure_cpu_threads()
        self.model = CLIPModel.from_pretrained(self.model_id).to(self.device).eval()
        self.processor = CLIPProcessor.from_pretrained(self.model_id)
        logger.info("CLIP running on %s", self.device)

    def embed_text(self, text: str) -> np.ndarray:
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)
            features = getattr(outputs, "pooler_output", outputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features[0].cpu().numpy().astype(np.float32)

    def embed_image(self, image_rgb: Image.Image | np.ndarray) -> np.ndarray:
        return self.embed_images([image_rgb])[0]

    def embed_images(self, images: list[Image.Image | np.ndarray]) -> np.ndarray:
        if not images:
            return np.empty((0, 512), dtype=np.float32)
        inputs = self.processor(images=images, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        with torch.inference_mode():
            outputs = self.model.get_image_features(**inputs)
            features = getattr(outputs, "pooler_output", outputs)
            features = features / features.norm(dim=-1, keepdim=True)
        return features.cpu().numpy().astype(np.float32)
