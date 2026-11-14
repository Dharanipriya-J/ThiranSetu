"""Password hashing (scrypt, stdlib) and JWT access tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LEN = 64
_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password with a random salt using scrypt (memory-hard KDF)."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_LEN)
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verification of a password against a stored scrypt hash."""
    try:
        scheme, n, r, p, salt_b64, digest_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            password.encode(), salt=base64.b64decode(salt_b64), n=int(n), r=int(r), p=int(p), dklen=len(expected)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def new_jti() -> str:
    """Return a cryptographically random token identifier for refresh rotation."""
    return secrets.token_urlsafe(24)


def create_access_token(user_id: int, token_version: int) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ver": token_version,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.resolved_jwt_secret(), algorithm=_ALGORITHM)


def create_refresh_token(user_id: int, token_version: int, jti: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "ver": token_version,
        "jti": jti,
        "iat": now,
        "exp": now + timedelta(days=settings.refresh_token_days),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.resolved_jwt_secret(), algorithm=_ALGORITHM)


def _decode_token(token: str, expected_type: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, get_settings().resolved_jwt_secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Return the access token payload, or None if invalid/expired."""
    return _decode_token(token, "access")


def decode_refresh_token(token: str) -> dict[str, Any] | None:
    """Return the refresh token payload, or None if invalid/expired."""
    return _decode_token(token, "refresh")
