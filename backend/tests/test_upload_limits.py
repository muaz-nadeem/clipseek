import asyncio
import io
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("cv2")
pytest.importorskip("fastapi")
pytest.importorskip("psycopg")

from fastapi import HTTPException, UploadFile

from app.api import upload as module


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(module, "VIDEOS_DIR", tmp_path)
    monkeypatch.setattr(module, "MAX_DURATION_SEC", 600)
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(None))
    monkeypatch.setattr(module.models, "count_active_jobs", Mock(return_value=0))
    create = Mock(return_value=SimpleNamespace(id=5))
    monkeypatch.setattr(module.models, "create_video", create)
    monkeypatch.setattr(module, "get_storage", lambda: SimpleNamespace(put_file=lambda key, path: str(path)))
    enqueue = Mock()
    monkeypatch.setattr(module, "enqueue_indexing", enqueue)
    return tmp_path, create, enqueue


def _upload(user=SimpleNamespace(id=1)):
    file = UploadFile(file=io.BytesIO(b"fake video bytes"), filename="clip.mp4")
    return asyncio.run(module.upload_video(file=file, user=user))


def test_video_over_ten_minutes_is_rejected_before_any_row_exists(monkeypatch, env):
    directory, create, enqueue = env
    monkeypatch.setattr(module, "probe_duration", Mock(return_value=900.0))
    with pytest.raises(HTTPException) as error:
        _upload()
    assert error.value.status_code == 400
    assert "15.0 minutes" in error.value.detail
    assert not list(directory.iterdir())
    create.assert_not_called()
    enqueue.assert_not_called()


def test_video_within_limit_is_saved_and_queued(monkeypatch, env):
    directory, create, enqueue = env
    monkeypatch.setattr(module, "probe_duration", Mock(return_value=25.0))
    response = _upload()
    assert response.video_id == 5 and response.status == "queued"
    assert len(list(directory.iterdir())) == 1
    enqueue.assert_called_once_with(5)
