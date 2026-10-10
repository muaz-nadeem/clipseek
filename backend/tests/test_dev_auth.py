from unittest.mock import Mock

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("psycopg")

from fastapi import HTTPException
from app.api import deps


def test_local_mode_accepts_requests_without_credentials(monkeypatch):
    user = object()
    monkeypatch.setattr(deps, "DEV_AUTH_BYPASS", True)
    monkeypatch.setattr(deps, "IS_PRODUCTION", False)
    monkeypatch.setattr(deps, "_local_test_user", Mock(return_value=user))
    assert deps.get_current_user(None) is user


@pytest.mark.parametrize("bypass,production", [(False, False), (True, True), (False, True)])
def test_auth_required_outside_local_bypass(monkeypatch, bypass, production):
    monkeypatch.setattr(deps, "DEV_AUTH_BYPASS", bypass)
    monkeypatch.setattr(deps, "IS_PRODUCTION", production)
    local_user = Mock()
    monkeypatch.setattr(deps, "_local_test_user", local_user)
    with pytest.raises(HTTPException) as error:
        deps.get_current_user(None)
    assert error.value.status_code == 401
    local_user.assert_not_called()
