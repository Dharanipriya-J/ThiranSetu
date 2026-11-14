"""ThiranSetu FastAPI Application Entry Point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app import __version__
from app.api.routers import assessments, auth, insights, jobs, learning, profile
from app.core.config import get_settings
from app.core.rate_limit import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.db.seed import seed_jobs_if_empty
from app.db.session import SessionLocal, init_db

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s — %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    settings.resolved_jwt_secret()
    init_db()
    if settings.seed_demo_data:
        with SessionLocal() as db:
            seed_jobs_if_empty(db)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="ThiranSetu API",
        description="Agentic AI Skill Intelligence, Career Recommendation & Company-Based Job Matching Platform",
        version=__version__,
        lifespan=lifespan,
    )

    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(BodySizeLimitMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    )

    application.include_router(auth.router)
    application.include_router(profile.router)
    application.include_router(assessments.router)
    application.include_router(insights.router)
    application.include_router(jobs.router)
    application.include_router(learning.router)

    @application.get("/api/health", tags=["System"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "llm_mode": "gemini" if get_settings().llm_available else "deterministic",
        }

    return application


app = create_app()
