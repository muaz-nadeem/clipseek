from contextlib import nullcontext
from unittest.mock import Mock

import pytest

pytest.importorskip("psycopg")

from app.workers import recovery as module


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(module, "redis_available", Mock(return_value=False))
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(None))
    monkeypatch.setattr(module.models, "list_unfinished_video_ids", Mock(return_value=[3, 4]))
    status = Mock()
    monkeypatch.setattr(module.models, "update_video_status", status)
    monkeypatch.setattr(module.models, "update_video_progress", Mock())
    enqueue = Mock()
    monkeypatch.setattr(module, "enqueue_indexing", enqueue)
    return status, enqueue


def test_interrupted_videos_are_reset_and_requeued(env):
    status, enqueue = env
    assert module.recover_unfinished_jobs() == [3, 4]
    assert [call.args[1:] for call in status.call_args_list] == [(3, "queued"), (4, "queued")]
    assert [call.args[0] for call in enqueue.call_args_list] == [3, 4]


def test_redis_queue_is_left_alone(monkeypatch, env):
    status, enqueue = env
    monkeypatch.setattr(module, "redis_available", Mock(return_value=True))
    assert module.recover_unfinished_jobs() == []
    module.models.list_unfinished_video_ids.assert_not_called()
    enqueue.assert_not_called()


def test_enqueue_failure_marks_only_that_video_failed(env):
    status, enqueue = env
    enqueue.side_effect = [RuntimeError("Redis is required"), None]
    assert module.recover_unfinished_jobs() == [4]
    assert status.call_args_list[-1].args[1:] == (3, "failed")
    assert status.call_args_list[-1].kwargs["error_message"] == "Redis is required"
