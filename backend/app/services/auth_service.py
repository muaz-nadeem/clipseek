"""Auth helpers: password hashing, JWT, refresh tokens."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import JWT_ALGORITHM, JWT_EXPIRE_MINUTES, JWT_REFRESH_DAYS, JWT_SECRET


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256$120000${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, rounds_s, salt, digest_hex = password_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        rounds = int(rounds_s)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            rounds,
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(*, user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "exp": expire, "typ": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("typ") not in {None, "access"}:
        raise AuthError("Invalid token")
    return payload


class AuthError(Exception):
    pass


def user_id_from_token(token: str) -> int:
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise AuthError("Invalid token")
        return int(sub)
    except (JWTError, ValueError, TypeError) as exc:
        raise AuthError("Invalid token") from exc


def refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=JWT_REFRESH_DAYS)
