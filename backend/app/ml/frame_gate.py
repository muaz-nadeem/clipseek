"""Cheap perceptual-hash gate so CLIP only runs on new-looking crops/frames."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def dhash64(image_bgr: np.ndarray, hash_size: int = 8) -> int:
    """64-bit difference hash. Independent of CLIP."""
    import cv2

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY) if image_bgr.ndim == 3 else image_bgr
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    bits = np.packbits(diff.flatten().astype(np.uint8))
    value = 0
    for byte in bits:
        value = (value << 8) | int(byte)
    return int(value)


def hamming64(a: int, b: int) -> int:
    return (a ^ b).bit_count()


@dataclass
class HashDecision:
    store: bool
    reason: str  # "first" | "changed" | "heartbeat" | "skip"
    distance: int | None


class HashAppearanceGate:
    """Skip near-duplicate crops using dHash, with a time heartbeat."""

    def __init__(self, max_distance: int = 8, max_gap_sec: float = 15.0) -> None:
        self.max_distance = max_distance
        self.max_gap_sec = max_gap_sec
        self._last_hash: dict[int, int] = {}
        self._last_time: dict[int, float] = {}
        self._last_color: dict[int, np.ndarray] = {}

    def decide(self, key: int, image_bgr: np.ndarray, timestamp: float) -> HashDecision:
        digest = dhash64(image_bgr)
        previous = self._last_hash.get(key)
        if previous is None:
            return HashDecision(store=True, reason="first", distance=None)

        distance = hamming64(previous, digest)
        # Grayscale hashes alone miss changes in clothing/object color.
        color = image_bgr.reshape(-1, image_bgr.shape[-1]).mean(axis=0) if image_bgr.ndim == 3 else np.array([image_bgr.mean()])
        if distance > self.max_distance or np.max(np.abs(color - self._last_color[key])) > 20:
            return HashDecision(store=True, reason="changed", distance=distance)

        last_time = self._last_time[key]
        if timestamp - last_time >= self.max_gap_sec:
            return HashDecision(store=True, reason="heartbeat", distance=distance)

        return HashDecision(store=False, reason="skip", distance=distance)

    def remember(self, key: int, image_bgr: np.ndarray, timestamp: float) -> None:
        self._last_hash[key] = dhash64(image_bgr)
        self._last_time[key] = float(timestamp)
        self._last_color[key] = image_bgr.reshape(-1, image_bgr.shape[-1]).mean(axis=0) if image_bgr.ndim == 3 else np.array([image_bgr.mean()])

    def accept(self, key: int, image_bgr: np.ndarray, timestamp: float) -> HashDecision:
        decision = self.decide(key, image_bgr, timestamp)
        if decision.store:
            self.remember(key, image_bgr, timestamp)
        return decision
