"""Authentication routes with scrypt hashing, short-lived JWTs, HttpOnly refresh rotation, and CSRF."""

from __future__ import annotations

import hmac
import secrets

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.rate_limit import rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    new_jti,
    verify_password,
)
from app.db.models import Profile, User
from app.db.session import get_db
from app.schemas.all import LoginRequest, RegisterRequest, TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

REFRESH_COOKIE = "ts_refresh"
CSRF_COOKIE = "ts_csrf"


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, created_at=user.created_at)


def _issue_session(response: Response, user: User, db: Session) -> TokenResponse:
    settings = get_settings()
    jti = new_jti()
    user.refresh_jti = jti
    db.add(user)
    db.commit()
    db.refresh(user)

    access = create_access_token(user.id, user.token_version)
    refresh = create_refresh_token(user.id, user.token_version, jti)
    csrf_token = secrets.token_urlsafe(24)
    max_age = settings.refresh_token_days * 86400

    response.set_cookie(
        key=REFRESH_COOKIE,
        value=refresh,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/api/auth",
        max_age=max_age,
    )
    response.set_cookie(
        key=CSRF_COOKIE,
        value=csrf_token,
        httponly=False,
        secure=settings.is_production,
        samesite="lax",
        path="/",
        max_age=max_age,
    )
    return TokenResponse(access_token=access, user=_user_out(user))


def _clear_session_cookies(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth")
    response.delete_cookie(key=CSRF_COOKIE, path="/")


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit("auth_register", limit=15, window_seconds=60))],
)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    email_norm = payload.email.strip().lower()
    existing = db.scalar(select(User).where(User.email == email_norm))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists.")

    user = User(
        email=email_norm,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
    )
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return _issue_session(response, user, db)


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_login", limit=20, window_seconds=60))],
)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> TokenResponse:
    email_norm = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email == email_norm))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password.")
    return _issue_session(response, user, db)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(rate_limit("auth_refresh", limit=40, window_seconds=60))],
)
def refresh_session(
    response: Response,
    db: Session = Depends(get_db),
    ts_refresh: str | None = Cookie(default=None),
    ts_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> TokenResponse:
    if not ts_refresh:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh session not found.")
    if not ts_csrf or not x_csrf_token or not hmac.compare_digest(ts_csrf, x_csrf_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF verification failed.")

    payload = decode_refresh_token(ts_refresh)
    if not payload or not payload.get("sub") or not payload.get("jti"):
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    user = db.get(User, int(payload["sub"]))
    if not user or user.token_version != payload.get("ver"):
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session revoked or expired.")

    if user.refresh_jti != payload.get("jti"):
        # Refresh token reuse detected — revoke all sessions for safety
        user.token_version += 1
        user.refresh_jti = None
        db.add(user)
        db.commit()
        _clear_session_cookies(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token reuse detected. Please sign in again.")

    return _issue_session(response, user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ts_refresh: str | None = Cookie(default=None),
    ts_csrf: str | None = Cookie(default=None),
    x_csrf_token: str | None = Header(default=None),
) -> Response:
    if ts_refresh and (not ts_csrf or not x_csrf_token or not hmac.compare_digest(ts_csrf, x_csrf_token)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF verification failed.")
    user.token_version += 1
    user.refresh_jti = None
    db.add(user)
    db.commit()
    _clear_session_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
