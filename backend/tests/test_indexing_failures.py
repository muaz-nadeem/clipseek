"""Regression tests; require the backend runtime dependencies."""
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("cv2")
pytest.importorskip("ultralytics")
pytest.importorskip("transformers")
pytest.importorskip("psycopg")

from app.services import indexing_service as module


@pytest.fixture
def state(monkeypatch):
    conn = Mock()
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(conn))
    monkeypatch.setattr(module.models, "get_video", Mock(return_value=SimpleNamespace(stored_path="sample.mp4")))
    status = Mock()
    progress = Mock()
    monkeypatch.setattr(module.models, "update_video_status", status)
    monkeypatch.setattr(module.models, "update_video_progress", progress)
    return status, progress


@pytest.mark.parametrize("stage", ["storage", "download", "probe", "pipeline"])
def test_failure_marks_video_failed_and_propagates(monkeypatch, state, stage):
    storage = Mock()
    storage.local_path.return_value = "sample.mp4"
    factory = Mock(return_value=storage)
    probe = Mock(return_value=2.0)
    service = module.IndexingService()
    pipeline = Mock(return_value=3)
    monkeypatch.setattr(module, "get_storage", factory)
    monkeypatch.setattr(module, "probe_duration", probe)
    monkeypatch.setattr(service, "_run_pipeline", pipeline)
    {"storage": factory, "download": storage.local_path, "probe": probe, "pipeline": pipeline}[stage].side_effect = RuntimeError("test failure")
    with pytest.raises(RuntimeError, match="test failure"):
        service.index_video(1)
    status, progress = state
    assert [call.args[2] for call in status.call_args_list] == ["processing", "failed"]
    assert status.call_args.kwargs["error_message"] == "test failure"
    assert progress.call_args.args[2] == 0.0


def test_success_clears_error_and_completes_progress(monkeypatch, state):
    monkeypatch.setattr(module, "get_storage", Mock())
    monkeypatch.setattr(module, "probe_duration", Mock(return_value=2.0))
    service = module.IndexingService()
    monkeypatch.setattr(service, "_run_pipeline", Mock(return_value=3))
    service.index_video(1)
    status, progress = state
    assert status.call_args.args[2] == "completed"
    assert status.call_args.kwargs["error_message"] is None
    assert progress.call_args.args[2] == 1.0
    assert progress.call_args.kwargs["object_count"] == 3


def test_capture_released_when_model_loading_fails(monkeypatch):
    capture = Mock()
    capture.get.return_value = 25
    monkeypatch.setattr(module.cv2, "VideoCapture", Mock(return_value=capture))
    monkeypatch.setattr(module, "_get_detector", Mock(side_effect=RuntimeError("model unavailable")))
    with pytest.raises(RuntimeError, match="model unavailable"):
        module.IndexingService()._run_pipeline(1, "sample.mp4", None)
    capture.release.assert_called_once()


def test_sampling_gates_before_clip_and_flushes_final_batch(monkeypatch):
    import numpy as np

    cap = Mock()
    cap.get.side_effect = lambda prop: 30 if prop == module.cv2.CAP_PROP_FPS else 61
    cap.grab.side_effect = [True] * 61 + [False]
    cap.retrieve.return_value = (True, np.zeros((10, 10, 3), dtype=np.uint8))
    monkeypatch.setattr(module.cv2, "VideoCapture", Mock(return_value=cap))
    detector = Mock()
    detector.detect.return_value = SimpleNamespace(boxes=None, names={0: "person"})
    tracker = Mock()
    tracker.update.return_value = np.array([[0, 0, 8, 8, 1, 0.9, 0, 0]])
    monkeypatch.setattr(module, "_get_detector", lambda: detector)
    monkeypatch.setattr(module, "ObjectTracker", Mock(return_value=tracker))
    monkeypatch.setattr(module, "INDEX_STRIDE", None)
    monkeypatch.setattr(module, "INDEX_TARGET_FPS", 5)
    monkeypatch.setattr(module, "MAX_INDEX_FRAMES_INT", None)
    monkeypatch.setattr(module, "EMBED_HEARTBEAT_SEC", 2)
    monkeypatch.setattr(module, "EMBED_MIN_GAP_SEC", 0.5)
    monkeypatch.setattr(module, "CLIP_BATCH_SIZE", 8)
    monkeypatch.setattr(module, "SCENE_INTERVAL_SEC", 0)
    # Even frequent progress updates must preserve batches across frames.
    ticks = iter(range(0, 1000, 2))
    monkeypatch.setattr(module.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(Mock()))
    monkeypatch.setattr(module.models, "delete_objects_for_video", Mock())
    insert = Mock()
    monkeypatch.setattr(module.models, "insert_object", insert)
    monkeypatch.setattr(module.models, "update_video_progress", Mock())
    batches = Mock(side_effect=lambda images: np.tile([1.0, 0.0], (len(images), 1)))
    monkeypatch.setattr(module.clip_service, "embed_images", batches)
    module.IndexingService()._run_pipeline(1, "sample.mp4", None)
    assert detector.detect.call_count == 11
    assert sum(len(call.args[0]) for call in batches.call_args_list) == 2
    assert batches.call_count == 1
    assert insert.call_args.kwargs["frame_number"] == 0
    cap.release.assert_called_once()


def test_scene_embeddings_are_sampled_and_stored_as_whole_frames(monkeypatch):
    import numpy as np

    cap = Mock()
    cap.get.side_effect = lambda prop: 10 if prop == module.cv2.CAP_PROP_FPS else 50
    cap.grab.side_effect = [True] * 50 + [False]
    frames = iter(np.full((12, 16, 3), value, dtype=np.uint8) for value in range(0, 250, 5))
    cap.retrieve.side_effect = lambda: (True, next(frames))
    monkeypatch.setattr(module.cv2, "VideoCapture", Mock(return_value=cap))
    detector = Mock()
    detector.detect.return_value = SimpleNamespace(boxes=None, names={0: "person"})
    tracker = Mock()
    tracker.update.return_value = np.empty((0, 8))
    monkeypatch.setattr(module, "_get_detector", lambda: detector)
    monkeypatch.setattr(module, "ObjectTracker", Mock(return_value=tracker))
    monkeypatch.setattr(module, "INDEX_STRIDE", 1)
    monkeypatch.setattr(module, "MAX_INDEX_FRAMES_INT", None)
    monkeypatch.setattr(module, "SCENE_INTERVAL_SEC", 2)
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(Mock()))
    monkeypatch.setattr(module.models, "delete_objects_for_video", Mock())
    insert = Mock()
    monkeypatch.setattr(module.models, "insert_object", insert)
    monkeypatch.setattr(module.models, "update_video_progress", Mock())
    # Each scene vector points a different way, so every sampled scene is stored.
    axes = iter(np.eye(8, dtype=np.float32))
    embed = Mock(side_effect=lambda images: np.stack([next(axes) for _ in images]))
    monkeypatch.setattr(module.clip_service, "embed_images", embed)
    module.IndexingService()._run_pipeline(1, "sample.mp4", None)

    scene_rows = [call.kwargs for call in insert.call_args_list]
    # 5 seconds at 10 fps: whole-frame checks at 0, 2 and 4 seconds only.
    assert [row["timestamp"] for row in scene_rows] == [0.0, 2.0, 4.0]
    assert {row["class_name"] for row in scene_rows} == {"scene"}
    assert {row["track_id"] for row in scene_rows} == {-1}
    assert scene_rows[0]["bounding_box"] == [0.0, 0.0, 16.0, 12.0]


def test_hash_gate_detects_color_changes_and_heartbeat():
    import numpy as np
    from app.ml.frame_gate import HashAppearanceGate

    gate = HashAppearanceGate(max_gap_sec=2)
    red = np.full((8, 8, 3), [0, 0, 255], dtype=np.uint8)
    blue = np.full((8, 8, 3), [255, 0, 0], dtype=np.uint8)
    assert gate.accept(1, red, 0).store
    assert not gate.accept(1, red, 0.5).store
    assert gate.accept(1, blue, 1).store
    assert gate.accept(1, blue, 3).reason == "heartbeat"
