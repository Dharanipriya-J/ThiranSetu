"""Modular external job-data integration layer.

Supports permitted public JSON employer/job-board feeds when `JOB_FEED_URL` is configured.
Never scrapes websites in violation of their terms and never fabricates live vacancies.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.data.catalog import canonical_skill
from app.db.models import Job
from app.services.scoring import extract_requirements_from_text


class JobFeedProvider(Protocol):
    name: str

    async def fetch(self) -> list[dict[str, Any]]: ...


class PermittedJsonFeedProvider:
    """Fetches vacancies from a configured, permitted HTTPS JSON feed endpoint."""

    name = "permitted_json_feed"

    def __init__(self, feed_url: str, timeout: float = 10.0) -> None:
        self.feed_url = feed_url
        self.timeout = timeout

    async def fetch(self) -> list[dict[str, Any]]:
        if not self.feed_url.startswith("https://"):
            raise ValueError("JOB_FEED_URL must use https://")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self.feed_url)
            resp.raise_for_status()
            data = resp.json()
        items = data.get("items", data) if isinstance(data, dict) else data
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]


async def sync_permitted_feed(db: Session) -> dict[str, Any]:
    """Sync vacancies from `JOB_FEED_URL` if configured; otherwise return demonstration-mode status."""
    settings = get_settings()
    if not settings.job_feed_url:
        return {
            "status": "unconfigured",
            "mode": "demonstration_and_manual",
            "added": 0,
            "message": (
                "No external JOB_FEED_URL is configured. Curated demonstration vacancies and "
                "manual job-description ingestion remain active without fabricating live feeds."
            ),
        }

    provider = PermittedJsonFeedProvider(settings.job_feed_url)
    try:
        raw_items = await provider.fetch()
    except Exception as exc:
        return {
            "status": "error",
            "mode": "demonstration_and_manual",
            "added": 0,
            "message": f"External job feed unavailable ({type(exc).__name__}). Existing local vacancies preserved.",
        }

    added = 0
    today = date.today()
    for item in raw_items[:25]:
        apply_url = str(item.get("apply_url") or "")
        if not apply_url.startswith("https://"):
            continue
        title = str(item.get("title") or "").strip()
        company = str(item.get("company") or "").strip()
        description = str(item.get("description") or "").strip()
        if not title or not company or len(description) < 20:
            continue

        existing = db.scalar(select(Job).where(Job.apply_url == apply_url))
        if existing:
            existing.last_verified_date = today
            db.add(existing)
            continue

        extracted = extract_requirements_from_text(description)
        mandatory = [canonical_skill(s) for s in (item.get("mandatory_skills") or extracted["mandatory_skills"])]
        preferred = [canonical_skill(s) for s in (item.get("preferred_skills") or extracted["preferred_skills"])]
        mode = str(item.get("work_mode") or extracted.get("work_mode") or "hybrid").lower()
        if mode not in {"remote", "hybrid", "onsite"}:
            mode = "hybrid"

        job = Job(
            company=company[:120],
            title=title[:120],
            description=description[:5000],
            mandatory_skills=list(dict.fromkeys(mandatory)),
            preferred_skills=list(dict.fromkeys(preferred)),
            education=str(item.get("education") or extracted.get("education") or "")[:200],
            experience_min_years=float(item.get("experience_min_years") or extracted.get("experience_years") or 0.0),
            location=str(item.get("location") or extracted.get("location") or "India")[:120],
            work_mode=mode,
            salary_min_lpa=item.get("salary_min_lpa"),
            salary_max_lpa=item.get("salary_max_lpa"),
            posted_date=date.fromisoformat(str(item["posted_date"])) if item.get("posted_date") else today,
            last_verified_date=today,
            apply_url=apply_url[:500],
            source=str(item.get("source") or f"Permitted Feed ({provider.name})")[:200],
            verification_status="Verified",
            is_demo=False,
        )
        db.add(job)
        added += 1

    db.commit()
    return {
        "status": "ok",
        "mode": "live_feed",
        "added": added,
        "message": f"Synced {added} verified vacancies from permitted external feed.",
    }
