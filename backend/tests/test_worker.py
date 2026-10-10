from unittest.mock import Mock

import pytest

pytest.importorskip("redis")
pytest.importorskip("rq")
pytest.importorskip("psycopg")

from app.workers import worker


def test_worker_initializes_before_accepting_jobs(monkeypatch):
    calls = []
    for name in ("configure_logging", "validate_production_config", "ensure_storage_dirs", "apply_schema"):
        monkeypatch.setattr(worker, name, lambda name=name: calls.append(name))
    monkeypatch.setattr(worker.Redis, "from_url", Mock(return_value="connection"))
    instance = Mock()
    instance.work.side_effect = lambda **kwargs: calls.append("work")
    monkeypatch.setattr(worker, "Worker", Mock(return_value=instance))
    worker.main()
    assert calls == ["configure_logging", "validate_production_config", "ensure_storage_dirs", "apply_schema", "work"]


def test_invalid_config_prevents_worker_start(monkeypatch):
    monkeypatch.setattr(worker, "configure_logging", Mock())
    monkeypatch.setattr(worker, "validate_production_config", Mock(side_effect=RuntimeError("invalid config")))
    factory = Mock()
    monkeypatch.setattr(worker, "Worker", factory)
    with pytest.raises(RuntimeError, match="invalid config"):
        worker.main()
    factory.assert_not_called()
