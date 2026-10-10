from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock
from pathlib import Path
import subprocess

import pytest

pytest.importorskip("cv2")
pytest.importorskip("psycopg")
from app.services import clip_extract_service as module


@pytest.fixture
def export(monkeypatch, tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    monkeypatch.setattr(module, "CLIPS_DIR", tmp_path)
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(None))
    monkeypatch.setattr(module.models, "get_video", lambda *args: SimpleNamespace(stored_path=str(source)))
    monkeypatch.setattr(module, "get_storage", lambda: SimpleNamespace(local_path=lambda *args: source))
    monkeypatch.setattr(module, "probe_duration", lambda path: 24.0)
    monkeypatch.setattr(module, "ffmpeg_executable", lambda: "ffmpeg")
    return module.ClipService(), tmp_path


def test_old_mp4_cache_is_not_reused_and_export_is_atomic(monkeypatch, export):
    service, directory = export
    (directory / "video3_16.00_23.00.mp4").write_bytes(b"old mp4v")
    def encode(command, **kwargs):
        assert "libvpx-vp9" in command and "libopus" in command
        assert not (directory / "video3_webm_v1_16.000_23.000.webm").exists()
        Path(command[-1]).write_bytes(b"encoded")
    run = Mock(side_effect=encode)
    monkeypatch.setattr(module.subprocess, "run", run)
    path = service.extract_clip(3, 16, 23)
    assert path.suffix == ".webm" and path.read_bytes() == b"encoded"
    assert service.extract_clip(3, 16, 23) == path
    run.assert_called_once()


def test_failed_export_never_leaves_cached_partial_file(monkeypatch, export):
    service, directory = export
    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b"partial")
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(module.subprocess, "run", fail)
    with pytest.raises(RuntimeError, match="encode"):
        service.extract_clip(3, 16, 23)
    assert not list(directory.glob("*.webm"))


def test_range_after_video_end_is_rejected(export):
    service, _ = export
    with pytest.raises(ValueError, match="outside"):
        service.extract_clip(3, 30, 40)
