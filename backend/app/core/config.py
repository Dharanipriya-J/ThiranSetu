"""Centralised, typed application configuration loaded from environment variables / `.env`."""

from __future__ import annotations

import logging
import secrets
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("thiransetu.config")

MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./thiransetu.db"
    jwt_secret: str = ""
    access_token_minutes: int = Field(default=15, ge=5, le=1440)
    refresh_token_days: int = Field(default=7, ge=1, le=30)
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_seconds: float = 20.0
    llm_enabled: bool = True
    trust_proxy_headers: bool = False
    redis_url: str | None = None
    job_feed_url: str | None = None
    seed_demo_data: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_available(self) -> bool:
        return bool(self.llm_enabled and self.gemini_api_key)

    def resolved_jwt_secret(self) -> str:
        """Return the JWT secret. Production refuses to start without a strong one."""
        if self.jwt_secret and len(self.jwt_secret) >= MIN_SECRET_LENGTH:
            return self.jwt_secret
        if self.is_production:
            raise RuntimeError(f"JWT_SECRET must be set to at least {MIN_SECRET_LENGTH} characters in production.")
        return _ephemeral_dev_secret()


@lru_cache(maxsize=1)
def _ephemeral_dev_secret() -> str:
    logger.warning("JWT_SECRET not set: using an ephemeral development secret (tokens reset on restart).")
    return secrets.token_urlsafe(48)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
