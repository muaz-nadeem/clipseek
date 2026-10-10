"""Benchmark real inference without reading or modifying the database.

Run from backend/: python -m scripts.benchmark_indexing samples/traffic-video.mp4 --output result.json
Model weights must already be cached locally. Timings exclude model warmup.
"""

from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
import time
from unittest.mock import Mock, patch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video")
    parser.add_argument("--max-frames", type=int, default=None)
    parser.add_argument("--output")
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
    from app.services import indexing_service as pipeline
    import torch

    pipeline.warm_models()
    rows = []
    batch_sizes = []
    embed_images = pipeline.clip_service.embed_images

    def embed(images):
        batch_sizes.append(len(images))
        return embed_images(images)

    def store(conn, **row):
        rows.append({key: value for key, value in row.items() if key != "embedding"})

    with (
        patch.object(pipeline, "db_session", lambda: nullcontext(Mock())),
        patch.object(pipeline, "MAX_INDEX_FRAMES_INT", args.max_frames),
        patch.object(pipeline.models, "delete_objects_for_video"),
        patch.object(pipeline.models, "insert_object", side_effect=store),
        patch.object(pipeline.models, "update_video_progress"),
        patch.object(pipeline.clip_service, "embed_images", side_effect=embed),
    ):
        started = time.perf_counter()
        count = pipeline.IndexingService()._run_pipeline(0, args.video, None)
        elapsed = time.perf_counter() - started
    result = dict(seconds=round(elapsed, 3), threads=torch.get_num_threads(),
                  stored=count, embedded=sum(batch_sizes), batches=batch_sizes, rows=rows)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
