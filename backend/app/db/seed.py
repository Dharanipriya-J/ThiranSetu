"""Idempotent database seeding for curated demonstration vacancies."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.data.catalog import load_demo_jobs
from app.db.models import Job


def seed_jobs_if_empty(db: Session) -> int:
    count = db.scalar(select(func.count(Job.id))) or 0
    if count > 0:
        return 0
    added = 0
    for item in load_demo_jobs():
        is_demo = bool(item.get("is_demo", True))
        job = Job(
            company=item["company"],
            title=item["title"],
            role_id=item.get("role_id"),
            description=item["description"],
            mandatory_skills=item["mandatory_skills"],
            preferred_skills=item["preferred_skills"],
            education=item.get("education", ""),
            experience_min_years=float(item.get("experience_min_years", 0.0)),
            location=item["location"],
            work_mode=item["work_mode"],
            salary_min_lpa=item.get("salary_min_lpa"),
            salary_max_lpa=item.get("salary_max_lpa"),
            posted_date=date.fromisoformat(item["posted_date"]),
            last_verified_date=None if is_demo else date.fromisoformat(item["posted_date"]),
            deadline=date.fromisoformat(item["deadline"]) if item.get("deadline") else None,
            apply_url=item["apply_url"],
            source=item["source"],
            verification_status="Synthetic Demo" if is_demo else "Pending Verification",
            is_demo=is_demo,
        )
        db.add(job)
        added += 1
    db.commit()
    return added
