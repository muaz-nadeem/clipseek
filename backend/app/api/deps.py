"""FastAPI auth dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import DEV_AUTH_BYPASS, IS_PRODUCTION

from app.database.connection import db_session
from app.database import models
from app.services.auth_service import AuthError, user_id_from_token

_bearer = HTTPBearer(auto_error=False)


def _local_test_user() -> models.UserRecord:
    """Give local testing a persistent library without requiring a login."""
    with db_session() as conn:
        # A disabled password prevents this internal account from logging in.
        # Keep the legacy internal email stable so existing test uploads retain their owner.
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (%s, %s) "
            "ON CONFLICT (email) DO NOTHING",
            ("local-test@lumenframe.invalid", "!disabled"),
        )
        user = models.get_user_by_email(conn, "local-test@lumenframe.invalid")
    assert user is not None
    return user


def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> models.UserRecord | None:
    if creds is None or not creds.credentials:
        return None
    try:
        uid = user_id_from_token(creds.credentials)
    except AuthError:
        return None
    with db_session() as conn:
        return models.get_user_by_id(conn, uid)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> models.UserRecord:
    if DEV_AUTH_BYPASS and not IS_PRODUCTION:
        return _local_test_user()
    if creds is None or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        uid = user_id_from_token(creds.credentials)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    with db_session() as conn:
        user = models.get_user_by_id(conn, uid)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user
