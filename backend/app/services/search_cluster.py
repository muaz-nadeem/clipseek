"""Search ranking helpers with no ML imports (safe for unit tests)."""

from __future__ import annotations

import math
import re

from app.config import PERSON_QUERY_WORDS
from app.utils.index_policy import SCENE_CLASS

# Detector class names; keep this lightweight rather than importing an ML model.
OBJECT_CLASSES = "person|bicycle|car|motorcycle|airplane|bus|train|truck|boat|traffic light|fire hydrant|stop sign|parking meter|bench|bird|cat|dog|horse|sheep|cow|elephant|bear|zebra|giraffe|backpack|umbrella|handbag|tie|suitcase|frisbee|skis|snowboard|sports ball|kite|baseball bat|baseball glove|skateboard|surfboard|tennis racket|bottle|wine glass|cup|fork|knife|spoon|bowl|banana|apple|sandwich|orange|broccoli|carrot|hot dog|pizza|donut|cake|chair|couch|potted plant|bed|dining table|toilet|tv|laptop|mouse|remote|keyboard|cell phone|microwave|oven|toaster|sink|refrigerator|book|clock|vase|scissors|teddy bear|hair drier|toothbrush".split("|")
ALIASES = {word: "person" for word in PERSON_QUERY_WORDS}
ALIASES.update({"men": "person", "women": "person", "children": "person",
    "bike": "bicycle", "bikes": "bicycle", "motorbike": "motorcycle",
    "plane": "airplane", "planes": "airplane", "lorry": "truck",
    "sofa": "couch", "television": "tv", "phone": "cell phone",
    "mice": "mouse", "knives": "knife", "buses": "bus"})


def _class_patterns() -> dict[str, str]:
    aliases = dict(ALIASES)
    for name in OBJECT_CLASSES:
        aliases[name] = name
        aliases[name + ("es" if name.endswith(("s", "ch")) else "s")] = name
    return aliases


_CLASS_ALIASES = _class_patterns()
_CLASS_PATTERN = re.compile(r"\b(?:" + "|".join(
    re.escape(name) for name in sorted(_CLASS_ALIASES, key=len, reverse=True)
) + r")\b", re.IGNORECASE)


def infer_class_names(query: str, class_names: list[str] | None) -> list[str] | None:
    if class_names:
        return class_names
    matches = [_CLASS_ALIASES[match.group().lower()] for match in _CLASS_PATTERN.finditer(query)]
    return list(dict.fromkeys(matches)) or None


def search_class_names(query: str, class_names: list[str] | None) -> list[str] | None:
    """Explicit filters are exact; inferred ones also admit full-frame scene rows."""
    if class_names:
        return class_names
    inferred = infer_class_names(query, None)
    return [*inferred, SCENE_CLASS] if inferred else None


def filter_relevant_matches(
    rows: list[dict], *, min_score: float, score_margin: float,
) -> list[dict]:
    """Reject weak absolute scores and the low-relevance tail before pagination.

    CLIP cosine scores are not probabilities. The absolute floor permits no-match
    responses; the relative margin avoids filling top_k with weak alternatives.
    """
    candidates = [row for row in rows if math.isfinite(float(row["score"]))]
    if not candidates:
        return []
    best = max(float(row["score"]) for row in candidates)
    cutoff = max(min_score, best - score_margin)
    return [row for row in candidates if float(row["score"]) >= cutoff]


def cluster_appearances(
    rows: list[dict],
    *,
    top_k: int,
    appearance_gap_sec: float,
) -> list[dict]:
    """Keep multiple hits per track when separated enough in time; sorted by score."""
    rows_sorted = sorted(rows, key=lambda r: r["score"], reverse=True)
    kept: list[dict] = []
    by_track: dict[tuple[int, int], list[float]] = {}

    for row in rows_sorted:
        key = (int(row["video_id"]), int(row["track_id"]))
        t = float(row["timestamp"])
        times = by_track.setdefault(key, [])
        if any(abs(t - prev) < appearance_gap_sec for prev in times):
            continue
        times.append(t)
        kept.append(row)
        if len(kept) >= top_k:
            break
    return kept
