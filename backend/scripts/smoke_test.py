"""Run real ML/API smoke checks in a temporary schema and media directory.

Run: python -m scripts.smoke_test
Requires a running configured Postgres and locally cached YOLO/CLIP models.
"""
from __future__ import annotations

import os
from pathlib import Path
import tempfile
import time
import uuid


def main() -> None:
    import cv2
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    with tempfile.TemporaryDirectory(prefix="ivs-smoke-") as directory:
        os.environ.update({
            "IVS_STORAGE_DIR": directory,
            "IVS_ENV": "development",
            "IVS_DEV_AUTH_BYPASS": "0",
            "IVS_REQUIRE_PGVECTOR": "0",
            "IVS_REQUIRE_REDIS": "0",
            "IVS_S3_BUCKET": "",
            "IVS_INDEX_STRIDE": "1",
            "IVS_MAX_INDEX_FRAMES": "",
            "HF_HUB_OFFLINE": "1",
            "HF_HUB_DISABLE_PROGRESS_BARS": "1",
        })
        from app import config

        original_url = config.DATABASE_URL
        schema = "ivs_smoke_" + uuid.uuid4().hex
        config.DATABASE_URL = make_conninfo(original_url, options=f"-c search_path={schema}")
        with psycopg.connect(original_url, autocommit=True) as admin:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            try:
                from fastapi.testclient import TestClient
                from app.main import app
                from app.workers import queue

                # Exercise the local background-thread path regardless of local Redis.
                queue._try_queue = lambda: None
                sample = Path(directory) / "sample.mp4"
                capture = cv2.VideoCapture(str(config.SAMPLES_DIR / "traffic-video.mp4"))
                writer = None
                try:
                    for _ in range(12):
                        ok, frame = capture.read()
                        assert ok, "Sample video must contain at least 12 frames"
                        height, width = frame.shape[:2]
                        scaled_height = max(2, round(height * 640 / width) // 2 * 2)
                        frame = cv2.resize(frame, (640, scaled_height))
                        if writer is None:
                            writer = cv2.VideoWriter(str(sample), cv2.VideoWriter_fourcc(*"mp4v"), 6, (640, scaled_height))
                            assert writer.isOpened()
                        writer.write(frame)
                finally:
                    capture.release()
                    if writer is not None:
                        writer.release()

                with TestClient(app) as client:
                    response = client.post("/auth/register", json={"email": "smoke@example.test", "password": uuid.uuid4().hex})
                    assert response.status_code == 200, response.text
                    headers = {"Authorization": "Bearer " + response.json()["access_token"]}
                    with sample.open("rb") as source:
                        response = client.post("/videos/upload", files={"file": ("sample.mp4", source, "video/mp4")}, headers=headers)
                    assert response.status_code == 200, response.text
                    video_id = response.json()["video_id"]
                    print(f"Uploaded sample: video {video_id}", flush=True)
                    deadline = time.monotonic() + 240
                    while True:
                        status = client.get(f"/videos/{video_id}", headers=headers).json()
                        if status["status"] in {"completed", "failed"}:
                            break
                        assert time.monotonic() < deadline, "Indexing timed out"
                        time.sleep(1)
                    assert status["status"] == "completed", status
                    assert status["object_count"] > 0, status
                    print(f"Indexing completed: {status['object_count']} embeddings", flush=True)
                    response = client.post("/search", json={"query": "car on a road", "video_id": video_id, "min_score": 0.0}, headers=headers)
                    assert response.status_code == 200, response.text
                    results = response.json()["results"]
                    assert results, "Search returned no matches"
                    response = client.get(results[0]["clip_url"], headers=headers)
                    assert response.status_code == 200, response.text
                    assert response.headers["content-type"] == "video/webm"
                    exported = Path(directory) / "result.webm"
                    exported.write_bytes(response.content)
                    decoder = cv2.VideoCapture(str(exported))
                    try:
                        assert decoder.read()[0], "Returned clip is not decodable"
                    finally:
                        decoder.release()
                    print(f"Search returned {len(results)} matches; clip decodes successfully", flush=True)
                    assert client.get(results[0]["clip_url"]).status_code == 401
                    other = client.post("/auth/register", json={"email": "other@example.test", "password": uuid.uuid4().hex})
                    other_headers = {"Authorization": "Bearer " + other.json()["access_token"]}
                    assert client.get(f"/videos/{video_id}", headers=other_headers).status_code == 404
                    assert client.get(results[0]["clip_url"], headers=other_headers).status_code == 404
                    assert client.delete(f"/videos/{video_id}", headers=headers).status_code == 200
                    print("Authentication, user isolation and deletion checks passed", flush=True)
            finally:
                # Only remove the uniquely named schema created by this invocation.
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
