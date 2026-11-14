"""Orchestrator insights, market intelligence, career ranking, and student dashboard routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import get_latest_orchestrator_run, run_orchestrator
from app.api.deps import get_current_user
from app.data.catalog import role_map
from app.db.models import AgentRun, AssessmentAttempt, Profile, User
from app.db.session import get_db
from app.schemas.all import OrchestratorRunRequest, TargetCareerRequest
from app.services.scoring import aggregate_verified_skills, compute_profile_completeness

router = APIRouter(tags=["Intelligence & Careers"])


@router.post("/api/agents/run")
def trigger_orchestrator(
    payload: OrchestratorRunRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return run_orchestrator(db, user, trigger=payload.trigger)


@router.get("/api/agents/latest")
def latest_orchestrator(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_latest_orchestrator_run(db, user)


@router.get("/api/intelligence")
def get_intelligence(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_latest_orchestrator_run(db, user)["skill_intelligence"]


@router.get("/api/market")
def get_market(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return get_latest_orchestrator_run(db, user)["market"]


@router.get("/api/careers")
def get_careers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return get_latest_orchestrator_run(db, user)["careers"]


@router.put("/api/careers/target")
def set_target_career(
    payload: TargetCareerRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    if payload.role_id not in role_map():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown role_id.")
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
    profile.target_role = payload.role_id
    db.add(profile)
    db.commit()
    result = run_orchestrator(db, user, trigger="goal_changed")
    return result["roadmap"]


@router.get("/api/dashboard")
def get_dashboard(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    latest = get_latest_orchestrator_run(db, user)
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

    intel = latest.get("skill_intelligence") or {}
    careers = latest.get("careers") or []
    top_jobs = latest.get("top_jobs") or []
    rec_groups = latest.get("recommended_courses") or []
    flat_courses = [c for grp in rec_groups for c in (grp.get("courses") or [])][:3]
    roadmap = latest.get("roadmap") or {}

    runs = list(
        db.scalars(select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.id.asc())).all()
    )
    readiness_trend = [
        {"date": r.created_at.isoformat(), "readiness": round(float(r.readiness or 0.0), 1)}
        for r in runs[-12:]
    ]

    disclosed_jobs = [j for j in top_jobs if j["salary"]["disclosed"]]
    min_sal = profile.min_salary_lpa
    jobs_meeting_min = 0
    if min_sal is not None:
        jobs_meeting_min = sum(
            1
            for j in disclosed_jobs
            if (j["salary"]["max_lpa"] or j["salary"]["min_lpa"] or 0) >= min_sal
        )
    else:
        jobs_meeting_min = len(disclosed_jobs)

    target_role_obj = None
    if profile.target_role and profile.target_role in role_map():
        r = role_map()[profile.target_role]
        target_role_obj = {"id": r["id"], "title": r["title"]}

    return {
        "profile_completeness": compute_profile_completeness(user, profile),
        "llm_mode": latest.get("llm_mode", "deterministic"),
        "verified_skills": verified,
        "strongest": intel.get("strong", [])[:5],
        "weakest": intel.get("weak", [])[:5],
        "missing_skills": [m["skill"] for m in intel.get("missing", [])][:8],
        "outdated_alerts": intel.get("outdated", []),
        "emerging_skills": intel.get("emerging", [])[:5],
        "top_careers": careers[:3],
        "top_jobs": top_jobs[:3],
        "salary_summary": {
            "expected_lpa": profile.expected_salary_lpa,
            "min_lpa": profile.min_salary_lpa,
            "jobs_meeting_minimum": jobs_meeting_min,
            "jobs_with_disclosed_salary": len(disclosed_jobs),
        },
        "recommended_courses": flat_courses,
        "roadmap_progress": roadmap.get("progress_percent", 0),
        "assessment_history": [
            {
                "attempt_id": a.id,
                "skill": a.skill,
                "level": a.level,
                "score": a.score,
                "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            }
            for a in attempts[:10]
        ],
        "readiness_trend": readiness_trend,
        "target_role": target_role_obj,
        "agent_trace": latest.get("trace", []),
    }
