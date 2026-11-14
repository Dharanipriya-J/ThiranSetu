"""ThiranSetu FastAPI Application Entry Point."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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

    static_dir_env = os.environ.get("STATIC_DIR", "").strip()
    if static_dir_env:
        static_root = Path(static_dir_env).resolve()
        index_html = static_root / "index.html"
        assets_dir = static_root / "assets"
        if assets_dir.is_dir():
            application.mount("/assets", StaticFiles(directory=assets_dir), name="assets")
        if index_html.is_file():

            @application.get("/{full_path:path}", include_in_schema=False)
            def serve_spa(full_path: str):
                if full_path.startswith("api/") or full_path == "api":
                    raise HTTPException(status_code=404, detail="Not Found")
                candidate = (static_root / full_path).resolve()
                if full_path and candidate.is_relative_to(static_root) and candidate.is_file():
                    return FileResponse(candidate)
                return FileResponse(index_html)

    return application


app = create_app()
