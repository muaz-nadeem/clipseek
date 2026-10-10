"""Auth routes: register / login / refresh / reset / me / delete."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.api.schemas import (
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.config import IS_PRODUCTION
from app.database.connection import db_session
from app.database import models
from app.services.auth_service import (
    create_access_token,
    hash_password,
    hash_token,
    new_refresh_token,
    refresh_expiry,
    verify_password,
)
from app.services.email_service import reset_link, send_password_reset
from app.services.storage import get_storage
from app.utils.ratelimit import check_auth_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: models.UserRecord) -> TokenResponse:
    access = create_access_token(user_id=user.id, email=user.email)
    refresh = new_refresh_token()
    with db_session() as conn:
        models.create_refresh_token(conn, user.id, hash_token(refresh), refresh_expiry())
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        email=user.email,
    )


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, request: Request) -> TokenResponse:
    check_auth_rate_limit(request)
    email = body.email.lower().strip()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email")
    with db_session() as conn:
        if models.get_user_by_email(conn, email) is not None:
            raise HTTPException(status_code=400, detail="Email already registered")
        user = models.create_user(conn, email, hash_password(body.password))
    return _issue_tokens(user)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    check_auth_rate_limit(request)
    with db_session() as conn:
        user = models.get_user_by_email(conn, body.email)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _issue_tokens(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, request: Request) -> TokenResponse:
    check_auth_rate_limit(request)
    token_hash = hash_token(body.refresh_token)
    with db_session() as conn:
        row = models.get_refresh_token(conn, token_hash)
        if row is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        _, user_id, expires_at, revoked = row
        if revoked:
            raise HTTPException(status_code=401, detail="Refresh token revoked")
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Refresh token expired")
        models.revoke_refresh_token(conn, token_hash)
        user = models.get_user_by_id(conn, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return _issue_tokens(user)


@router.post("/logout")
def logout(body: RefreshRequest, user: models.UserRecord = Depends(get_current_user)) -> dict:
    with db_session() as conn:
        models.revoke_refresh_token(conn, hash_token(body.refresh_token))
        models.revoke_user_refresh_tokens(conn, user.id)
    return {"ok": True}


@router.post("/forgot-password")
def forgot_password(body: PasswordResetRequest, request: Request) -> dict:
    check_auth_rate_limit(request)
    response: dict = {"ok": True}
    with db_session() as conn:
        user = models.get_user_by_email(conn, body.email)
        if user is not None:
            raw = new_refresh_token()
            models.create_password_reset(
                conn,
                user.id,
                hash_token(raw),
                datetime.now(timezone.utc) + timedelta(hours=1),
            )
            send_password_reset(user.email, raw)
            # Local testing without SMTP; production never reveals whether an account exists.
            if not IS_PRODUCTION:
                response["reset_url"] = reset_link(raw)
    return response


@router.post("/reset-password")
def reset_password(body: PasswordResetConfirm, request: Request) -> dict:
    check_auth_rate_limit(request)
    with db_session() as conn:
        user_id = models.consume_password_reset(conn, hash_token(body.token))
        if user_id is None:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")
        models.update_password(conn, user_id, hash_password(body.password))
        models.revoke_user_refresh_tokens(conn, user_id)
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
def me(user: models.UserRecord = Depends(get_current_user)) -> UserResponse:
    return UserResponse(user_id=user.id, email=user.email)


@router.delete("/me")
def delete_account(user: models.UserRecord = Depends(get_current_user)) -> dict:
    storage = get_storage()
    with db_session() as conn:
        paths = models.delete_user(conn, user.id)
    for path in paths:
        storage.delete(path)
    return {"ok": True}
