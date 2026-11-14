"""Company job matching, requirement extraction, and application tracker routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.course_discovery import find_courses_for_skills
from app.agents.job_matching import format_job_summary, is_verified_real_job
from app.agents.orchestrator import run_orchestrator
from app.api.deps import get_current_user
from app.data.catalog import canonical_skill
from app.db.models import Application, AssessmentAttempt, Job, Profile, User
from app.db.session import get_db
from app.schemas.all import (
    ApplicationCreateRequest,
    ApplicationUpdateRequest,
    ExtractJobRequest,
    JobCreateRequest,
)
from app.services.job_ingestion import sync_permitted_feed
from app.services.scoring import aggregate_verified_skills, extract_requirements_from_text, score_job_match

router = APIRouter(tags=["Jobs & Applications"])


def _load_profile_and_verified(db: Session, user: User) -> tuple[Profile, list[dict[str, Any]], set[int]]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.completed_at.is_not(None))
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    verified = aggregate_verified_skills(attempts, profile.technical_skills or [])
    saved_ids = set(db.scalars(select(Application.job_id).where(Application.user_id == user.id)).all())
    return profile, verified, saved_ids


@router.get("/api/jobs")
def list_jobs(
    q: str = Query(default="", max_length=100),
    company: str = Query(default="", max_length=100),
    location: str = Query(default="", max_length=100),
    work_mode: str = Query(default="", max_length=20),
    min_salary: float | None = Query(default=None, ge=0),
    max_experience: float | None = Query(default=None, ge=0),
    min_score: float | None = Query(default=None, ge=0, le=100),
    verified_only: bool = Query(default=False),
    sort: str = Query(default="score"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile, verified, saved_ids = _load_profile_and_verified(db, user)
    stmt = select(Job).where(Job.is_demo.is_(False))
    if company.strip():
        stmt = stmt.where(Job.company.ilike(f"%{company.strip()}%"))
    if location.strip():
        stmt = stmt.where(Job.location.ilike(f"%{location.strip()}%"))
    if work_mode.strip() and work_mode.strip().lower() != "any":
        stmt = stmt.where(Job.work_mode == work_mode.strip().lower())
    if max_experience is not None:
        stmt = stmt.where(Job.experience_min_years <= max_experience)
    if verified_only:
        stmt = stmt.where(Job.verification_status == "Verified")
    jobs = list(db.scalars(stmt).all())

    q_low = q.strip().lower()
    comp_low = company.strip().lower()
    loc_low = location.strip().lower()
    mode_low = work_mode.strip().lower()

    matched_items: list[dict[str, Any]] = []
    for job in jobs:
        if getattr(job, "is_demo", False):
            continue
        if q_low and q_low not in job.title.lower() and q_low not in job.company.lower() and q_low not in job.description.lower():
            continue
        if comp_low and comp_low not in job.company.lower():
            continue
        if loc_low and loc_low not in job.location.lower():
            continue
        if mode_low and mode_low != "any" and job.work_mode.lower() != mode_low:
            continue
        if max_experience is not None and float(job.experience_min_years or 0) > max_experience:
            continue
        if min_salary is not None:
            top_sal = job.salary_max_lpa if job.salary_max_lpa is not None else job.salary_min_lpa
            if top_sal is None or float(top_sal) < min_salary:
                continue

        match = score_job_match(job, profile, verified)
        if min_score is not None and match["score"] < min_score:
            continue
        summary = format_job_summary(job, match, saved=job.id in saved_ids)
        if verified_only and not is_verified_real_job(job):
            continue
        matched_items.append(summary)

    if sort == "date":
        matched_items.sort(key=lambda j: j["posted_date"], reverse=True)
    elif sort == "salary":
        matched_items.sort(key=lambda j: (j["salary"]["max_lpa"] or j["salary"]["min_lpa"] or -1), reverse=True)
    else:
        matched_items.sort(key=lambda j: (-j["score"], j["company"]))

    total = len(matched_items)
    start = (page - 1) * page_size
    return {
        "items": matched_items[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/api/jobs/{job_id}")
def get_job_detail(
    job_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job = db.get(Job, job_id)
    if not job or getattr(job, "is_demo", False):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    profile, verified, saved_ids = _load_profile_and_verified(db, user)
    match = score_job_match(job, profile, verified)
    summary = format_job_summary(job, match, saved=job.id in saved_ids)

    gap_skills = list(
        dict.fromkeys(
            match["missing_mandatory"]
            + [p["skill"] for p in match["partial_matches"]]
            + match["missing_preferred"]
        )
    )
    courses = find_courses_for_skills(gap_skills[:5], preferred_language=profile.learning_language or "en")

    return {
        **summary,
        "description": job.description,
        "education": job.education,
        "match": match,
        "recommended_courses": courses,
    }


@router.post("/api/jobs/extract")
def extract_job_requirements(
    payload: ExtractJobRequest,
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    return extract_requirements_from_text(payload.description)


@router.post("/api/jobs/sync")
async def sync_jobs(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return await sync_permitted_feed(db)


@router.post("/api/jobs", status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    extracted = extract_requirements_from_text(payload.description)
    mandatory = (
        list(dict.fromkeys(canonical_skill(s) for s in payload.mandatory_skills if s.strip()))
        if payload.mandatory_skills is not None
        else extracted["mandatory_skills"]
    )
    preferred = (
        list(dict.fromkeys(canonical_skill(s) for s in payload.preferred_skills if s.strip() and canonical_skill(s) not in mandatory))
        if payload.preferred_skills is not None
        else extracted["preferred_skills"]
    )
    job = Job(
        company=payload.company.strip(),
        title=payload.title.strip(),
        description=payload.description.strip(),
        mandatory_skills=mandatory,
        preferred_skills=preferred,
        education=payload.education.strip() or extracted["education"],
        experience_min_years=payload.experience_min_years or extracted["experience_years"],
        location=payload.location.strip(),
        work_mode=payload.work_mode,
        salary_min_lpa=payload.salary_min_lpa,
        salary_max_lpa=payload.salary_max_lpa,
        posted_date=payload.posted_date,
        last_verified_date=None,
        deadline=payload.deadline,
        apply_url=str(payload.apply_url),
        source=payload.source.strip(),
        verification_status="Pending Verification",
        is_demo=False,
        created_by=user.id,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    run_orchestrator(db, user, trigger="job_added", sync_roadmap=True)
    return get_job_detail(job.id, user=user, db=db)


@router.get("/api/applications")
def list_applications(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    profile, verified, _ = _load_profile_and_verified(db, user)
    apps = list(
        db.scalars(
            select(Application).where(Application.user_id == user.id).order_by(Application.updated_at.desc())
        ).all()
    )
    out: list[dict[str, Any]] = []
    for app in apps:
        match = score_job_match(app.job, profile, verified)
        out.append(
            {
                "id": app.id,
                "job": format_job_summary(app.job, match, saved=True),
                "status": app.status,
                "notes": app.notes,
                "updated_at": app.updated_at.isoformat(),
            }
        )
    return out


@router.post("/api/applications", status_code=status.HTTP_201_CREATED)
def save_application(
    payload: ApplicationCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    job = db.get(Job, payload.job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    existing = db.scalar(
        select(Application).where(Application.user_id == user.id, Application.job_id == payload.job_id)
    )
    if existing:
        existing.status = payload.status
        db.add(existing)
        db.commit()
        db.refresh(existing)
        app = existing
    else:
        app = Application(user_id=user.id, job_id=payload.job_id, status=payload.status)
        db.add(app)
        db.commit()
        db.refresh(app)

    profile, verified, _ = _load_profile_and_verified(db, user)
    match = score_job_match(job, profile, verified)
    return {
        "id": app.id,
        "job": format_job_summary(job, match, saved=True),
        "status": app.status,
        "notes": app.notes,
        "updated_at": app.updated_at.isoformat(),
    }


@router.patch("/api/applications/{app_id}")
def update_application(
    app_id: int,
    payload: ApplicationUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    app = db.get(Application, app_id)
    if not app or app.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")
    if payload.status is not None:
        app.status = payload.status
    if payload.notes is not None:
        app.notes = payload.notes
    db.add(app)
    db.commit()
    db.refresh(app)

    profile, verified, _ = _load_profile_and_verified(db, user)
    match = score_job_match(app.job, profile, verified)
    return {
        "id": app.id,
        "job": format_job_summary(app.job, match, saved=True),
        "status": app.status,
        "notes": app.notes,
        "updated_at": app.updated_at.isoformat(),
    }


@router.delete("/api/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    app = db.get(Application, app_id)
    if not app or app.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application record not found.")
    db.delete(app)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
