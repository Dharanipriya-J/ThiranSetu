"""Lightweight in-memory sliding-window rate limiter and security headers middleware.

The limiter keys on the socket peer address (X-Forwarded-For is only honoured when
TRUST_PROXY_HEADERS=true, e.g. behind Cloud Run's trusted front end), so clients cannot
bypass it by spoofing headers. It is per-process: multi-instance deployments should swap
`SlidingWindowLimiter` for a shared store (e.g. Redis/Memorystore) behind the same interface.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import get_settings

logger = logging.getLogger("thiransetu.rate_limit")


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float) -> float | None:
        """Register a hit. Returns None if allowed, else seconds until retry."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                return max(0.0, window_seconds - (now - hits[0]))
            hits.append(now)
            if len(self._hits) > 10_000:  # bound memory: drop idle keys
                for idle in [k for k, v in self._hits.items() if not v]:
                    del self._hits[idle]
            return None

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = SlidingWindowLimiter()


def _redis_check(redis_url: str, key: str, limit: int, window_seconds: float) -> tuple[bool, float | None]:
    """Distributed sliding-window check using Redis sorted sets. Returns (ok, retry_after)."""
    try:
        import redis  # type: ignore[import-not-found]
    except ImportError:
        return (False, None)
    try:
        client = redis.from_url(redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        now = time.time()
        rkey = f"ts:rl:{key}"
        pipe = client.pipeline()
        pipe.zremrangebyscore(rkey, 0, now - window_seconds)
        pipe.zcard(rkey)
        pipe.zadd(rkey, {f"{now}:{time.monotonic_ns()}": now})
        pipe.expire(rkey, int(window_seconds) + 2)
        _, count, _, _ = pipe.execute()
        if int(count) >= limit:
            oldest = client.zrange(rkey, 0, 0, withscores=True)
            if oldest:
                return (True, max(0.0, window_seconds - (now - float(oldest[0][1]))))
            return (True, window_seconds)
        return (True, None)
    except Exception as exc:
        logger.warning("Redis rate limiter unavailable (%s)", type(exc).__name__)
        return (False, None)


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(name: str, limit: int, window_seconds: float, *, fail_closed_in_prod: bool = True):
    """FastAPI dependency factory enforcing a per-client limit for one endpoint group."""

    def dependency(request: Request) -> None:
        settings = get_settings()
        key = f"{name}:{client_ip(request)}"
        if settings.redis_url:
            ok, retry_after = _redis_check(settings.redis_url, key, limit, window_seconds)
            if not ok:
                if settings.is_production and fail_closed_in_prod:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Rate-limit service temporarily unavailable.",
                    )
                retry_after = limiter.check(key, limit, window_seconds)
        else:
            retry_after = limiter.check(key, limit, window_seconds)
        if retry_after is not None:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please retry later.",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    return dependency


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(self), camera=(), microphone=()")
        if request.url.path.startswith("/api/"):
            response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        elif not request.url.path.startswith(("/docs", "/redoc", "/openapi.json")):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com data:; "
                "img-src 'self' data: https:; connect-src 'self'; frame-ancestors 'none'",
            )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies larger than `max_bytes` (based on Content-Length)."""

    def __init__(self, app, max_bytes: int = 256_000) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > self.max_bytes:
            return Response('{"detail":"Request body too large"}', status_code=413, media_type="application/json")
        return await call_next(request)
