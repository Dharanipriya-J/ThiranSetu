"""Student profile and reference taxonomy routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_orchestrator
from app.api.deps import get_current_user
from app.data.catalog import canonical_skill, load_roles, load_skills, role_map
from app.db.models import Profile, User
from app.db.session import get_db
from app.schemas.all import ProfileUpdate
from app.services.scoring import compute_profile_completeness

router = APIRouter(tags=["Profile & Reference"])


def serialize_profile(user: User, profile: Profile) -> dict[str, Any]:
    return {
        "full_name": user.full_name,
        "education": profile.education,
        "college": profile.college,
        "graduation_year": profile.graduation_year,
        "technical_skills": profile.technical_skills or [],
        "soft_skills": profile.soft_skills or [],
        "projects": profile.projects or [],
        "certifications": profile.certifications or [],
        "experience_years": profile.experience_years,
        "experience_summary": profile.experience_summary,
        "career_interests": profile.career_interests or [],
        "target_role": profile.target_role,
        "current_location": profile.current_location,
        "preferred_locations": profile.preferred_locations or [],
        "willing_to_relocate": profile.willing_to_relocate,
        "work_mode": profile.work_mode,
        "expected_salary_lpa": profile.expected_salary_lpa,
        "min_salary_lpa": profile.min_salary_lpa,
        "learning_language": profile.learning_language,
        "app_language": profile.app_language,
        "completeness": compute_profile_completeness(user, profile),
    }


@router.get("/api/profile")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, Any]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return serialize_profile(user, profile)


@router.put("/api/profile")
def update_profile(
    payload: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()

    prev_goal = profile.target_role
    data = payload.model_dump(exclude_unset=True)

    if "expected_salary_lpa" in data or "min_salary_lpa" in data:
        exp = data.get("expected_salary_lpa", profile.expected_salary_lpa)
        min_s = data.get("min_salary_lpa", profile.min_salary_lpa)
        if exp is not None and min_s is not None and min_s > exp:
            raise HTTPException(status_code=422, detail="min_salary_lpa cannot exceed expected_salary_lpa.")

    if "target_role" in data and data["target_role"] is not None:
        if data["target_role"] and data["target_role"] not in role_map():
            raise HTTPException(status_code=422, detail="Unknown target_role.")

    if "full_name" in data and data["full_name"] is not None:
        user.full_name = data.pop("full_name").strip()
        db.add(user)

    if "technical_skills" in data and data["technical_skills"] is not None:
        deduped: dict[str, dict[str, str]] = {}
        for sk in data["technical_skills"]:
            canon = canonical_skill(sk["name"])
            if canon:
                deduped[canon] = {"name": canon, "self_level": sk["self_level"]}
        data["technical_skills"] = list(deduped.values())

    for key, value in data.items():
        setattr(profile, key, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    db.refresh(user)

    trigger = "goal_changed" if profile.target_role != prev_goal else "profile_updated"
    run_orchestrator(db, user, trigger=trigger)
    return serialize_profile(user, profile)


@router.get("/api/skills")
def list_skills() -> list[dict[str, Any]]:
    return [
        {"name": s["name"], "category": s["category"], "assessable": bool(s.get("assessable"))}
        for s in load_skills()
    ]


@router.get("/api/roles")
def list_roles() -> list[dict[str, Any]]:
    return load_roles()
