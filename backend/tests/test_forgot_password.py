from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("psycopg")

from app.api import auth as module
from app.api.schemas import PasswordResetRequest


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(module, "check_auth_rate_limit", Mock())
    monkeypatch.setattr(module, "db_session", lambda: nullcontext(None))
    monkeypatch.setattr(module.models, "create_password_reset", Mock())
    send = Mock()
    monkeypatch.setattr(module, "send_password_reset", send)
    return send


def _user(monkeypatch, user):
    monkeypatch.setattr(module.models, "get_user_by_email", Mock(return_value=user))


def test_development_returns_reset_link_for_existing_user(monkeypatch, env):
    _user(monkeypatch, SimpleNamespace(id=1, email="a@b.com"))
    monkeypatch.setattr(module, "IS_PRODUCTION", False)
    response = module.forgot_password(PasswordResetRequest(email="a@b.com"), request=None)
    assert response["ok"] is True
    assert "/reset-password?token=" in response["reset_url"]
    env.assert_called_once()
    # The link carries the same raw token that was hashed and emailed.
    assert response["reset_url"].endswith(env.call_args.args[1])


def test_production_never_reveals_reset_link(monkeypatch, env):
    _user(monkeypatch, SimpleNamespace(id=1, email="a@b.com"))
    monkeypatch.setattr(module, "IS_PRODUCTION", True)
    assert module.forgot_password(PasswordResetRequest(email="a@b.com"), request=None) == {"ok": True}


def test_unknown_email_gets_same_response_without_link(monkeypatch, env):
    _user(monkeypatch, None)
    monkeypatch.setattr(module, "IS_PRODUCTION", False)
    assert module.forgot_password(PasswordResetRequest(email="x@y.com"), request=None) == {"ok": True}
    env.assert_not_called()
