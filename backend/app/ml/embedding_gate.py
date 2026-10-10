"""Per-track embedding change detection for storage gating."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=np.float32).reshape(-1)
    b = np.asarray(b, dtype=np.float32).reshape(-1)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


@dataclass
class GateDecision:
    store: bool
    similarity: float | None
    reason: str  # "first" | "changed" | "heartbeat" | "skip"


class TrackEmbeddingGate:
    """Store when first seen, appearance changed, or max time gap elapsed."""

    def __init__(self, threshold: float = 0.95, max_gap_sec: float = 15.0) -> None:
        self.threshold = threshold
        self.max_gap_sec = max_gap_sec
        self._last_stored: dict[int, np.ndarray] = {}
        self._last_stored_time: dict[int, float] = {}

    def decide(
        self,
        track_id: int,
        embedding: np.ndarray,
        timestamp: float,
    ) -> GateDecision:
        previous = self._last_stored.get(track_id)
        if previous is None:
            return GateDecision(store=True, similarity=None, reason="first")

        similarity = cosine_similarity(previous, embedding)
        if similarity < self.threshold:
            return GateDecision(store=True, similarity=similarity, reason="changed")

        last_time = self._last_stored_time[track_id]
        if timestamp - last_time >= self.max_gap_sec:
            return GateDecision(store=True, similarity=similarity, reason="heartbeat")

        return GateDecision(store=False, similarity=similarity, reason="skip")

    def remember(self, track_id: int, embedding: np.ndarray, timestamp: float) -> None:
        self._last_stored[track_id] = np.asarray(embedding, dtype=np.float32).copy()
        self._last_stored_time[track_id] = float(timestamp)

    def accept(
        self,
        track_id: int,
        embedding: np.ndarray,
        timestamp: float,
    ) -> GateDecision:
        decision = self.decide(track_id, embedding, timestamp)
        if decision.store:
            self.remember(track_id, embedding, timestamp)
        return decision
