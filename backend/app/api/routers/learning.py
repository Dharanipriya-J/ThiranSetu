"""Course discovery, multilingual equivalence, adaptive roadmap, and AI career mentor routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.career_mentor import answer_mentor_question
from app.agents.course_discovery import find_multilingual_equivalents
from app.agents.orchestrator import get_latest_orchestrator_run, run_orchestrator
from app.api.deps import get_current_user
from app.core.rate_limit import rate_limit
from app.data.catalog import is_verified_course, load_courses, load_verified_courses, role_map
from app.db.models import AssessmentAttempt, Profile, RoadmapStep, User
from app.db.session import get_db
from app.schemas.all import LangCode, MentorChatRequest, RoadmapStepUpdateRequest
from app.services.scoring import aggregate_verified_skills

router = APIRouter(tags=["Courses, Roadmap & Mentor"])


@router.get("/api/courses")
def list_courses(
    skill: str = Query(default="", max_length=60),
    platform: str = Query(default="", max_length=40),
    language: str = Query(default="", max_length=10),
    audio_language: str = Query(default="", max_length=10),
    subtitle_language: str = Query(default="", max_length=10),
    price: str = Query(default="", max_length=10),
    difficulty: str = Query(default="", max_length=20),
    max_hours: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    verified_only: bool = Query(default=False),
    q: str = Query(default="", max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    courses = load_courses()
    sk_low = skill.strip().lower()
    plat_low = platform.strip().lower()
    lang_low = language.strip().lower()
    aud_low = audio_language.strip().lower()
    sub_low = subtitle_language.strip().lower()
    price_low = price.strip().lower()
    diff_low = difficulty.strip().lower()
    q_low = q.strip().lower()

    filtered: list[dict[str, Any]] = []
    for c in courses:
        verified_flag = is_verified_course(c)
        if verified_only and not verified_flag:
            continue
        if sk_low and not any(s.lower() == sk_low for s in c.get("skills") or []):
            continue
        if plat_low and c["platform"].lower() != plat_low:
            continue
        if lang_low and c["language"].lower() != lang_low:
            continue
        if aud_low and aud_low not in [a.lower() for a in (c.get("audio_languages") or [])]:
            continue
        if sub_low and sub_low not in [s.lower() for s in (c.get("subtitle_languages") or [])]:
            continue
        if price_low == "free" and not c["price"]["is_free"]:
            continue
        if price_low == "paid" and c["price"]["is_free"]:
            continue
        if diff_low and c["difficulty"].lower() != diff_low:
            continue
        if max_hours is not None and (c.get("duration_hours") is None or c["duration_hours"] > max_hours):
            continue
        if min_rating is not None:
            r_val = c["rating"]["value"] if c.get("rating") else None
            if r_val is None or r_val < min_rating:
                continue
        if q_low and q_low not in c["title"].lower() and q_low not in " ".join(c.get("skills") or []).lower():
            continue
        filtered.append({**c, "is_verified": verified_flag})

    total = len(filtered)
    start = (page - 1) * page_size
    availability_note: str | None = None
    if total == 0 and lang_low:
        sub_count = sum(1 for c in courses if lang_low in [s.lower() for s in (c.get("subtitle_languages") or [])])
        if sub_count > 0:
            availability_note = (
                f"No courses with primary teaching language '{lang_low.upper()}' matched your other filters, "
                f"but {sub_count} catalogue course(s) provide {lang_low.upper()} subtitles."
            )
        else:
            availability_note = (
                f"No verified courses are currently available in '{lang_low.upper()}' for these filters."
            )
    return {
        "items": filtered[start : start + page_size],
        "total": total,
        "page": page,
        "page_size": page_size,
        "availability_note": availability_note,
    }


@router.get("/api/courses/recommended")
def recommended_courses(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    return get_latest_orchestrator_run(db, user)["recommended_courses"]


@router.get("/api/courses/{course_id}/equivalents")
def course_equivalents(
    course_id: str,
    language: LangCode = Query(...),
    _user: User = Depends(get_current_user),
) -> dict[str, Any]:
    res = find_multilingual_equivalents(course_id, language)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    return res


def _build_roadmap_response(db: Session, user: User) -> dict[str, Any]:
    steps = list(
        db.scalars(select(RoadmapStep).where(RoadmapStep.user_id == user.id).order_by(RoadmapStep.order)).all()
    )
    if not steps:
        return get_latest_orchestrator_run(db, user)["roadmap"]

    course_by_id = {c["id"]: c for c in load_verified_courses()}
    completed = sum(1 for s in steps if s.status == "completed")
    progress_pct = int(round(100 * completed / len(steps))) if steps else 0
    first = steps[0]
    target_role = None
    if first.target_role and first.target_role in role_map():
        r = role_map()[first.target_role]
        target_role = {"id": r["id"], "title": r["title"]}

    return {
        "target_role": target_role,
        "generated_at": first.generated_at.isoformat(),
        "reason": first.roadmap_reason,
        "progress_percent": progress_pct,
        "steps": [
            {
                "id": st.id,
                "order": st.order,
                "skill": st.skill,
                "priority": st.priority,
                "reason": st.reason,
                "course": course_by_id.get(st.course_id) if st.course_id else None,
                "estimated_hours": st.estimated_hours,
                "exercise": st.exercise,
                "project": st.project,
                "status": st.status,
                "reassessment_required": st.reassessment_required,
                "current_score": st.current_score,
                "target_score": st.target_score,
            }
            for st in steps
        ],
    }


@router.get("/api/roadmap")
def get_roadmap(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return _build_roadmap_response(db, user)


@router.post("/api/roadmap/regenerate")
def regenerate_roadmap(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    return run_orchestrator(db, user, trigger="manual", sync_roadmap=True)["roadmap"]


@router.patch("/api/roadmap/steps/{step_id}")
def update_roadmap_step(
    step_id: int,
    payload: RoadmapStepUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    step = db.get(RoadmapStep, step_id)
    if not step or step.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap step not found.")
    step.status = payload.status
    if payload.status == "completed":
        step.reassessment_required = True
    db.add(step)
    db.commit()
    return _build_roadmap_response(db, user)


@router.get("/api/mentor/suggestions")
def mentor_suggestions(_user: User = Depends(get_current_user)) -> list[str]:
    return [
        "Which career suits me?",
        "Why was this career recommended?",
        "What skills am I missing?",
        "Which course should I take first?",
        "How can I improve my job compatibility?",
        "Which jobs match my salary expectations?",
    ]


@router.post(
    "/api/mentor/chat",
    dependencies=[Depends(rate_limit("mentor_chat", limit=20, window_seconds=60))],
)
def mentor_chat(
    payload: MentorChatRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    latest = get_latest_orchestrator_run(db, user)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id)) or Profile(user_id=user.id)
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.completed_at.is_not(None))
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    verified = aggregate_verified_skills(attempts, profile.technical_skills or [])

    prof_dict = {
        "expected_salary_lpa": profile.expected_salary_lpa,
        "min_salary_lpa": profile.min_salary_lpa,
        "preferred_locations": profile.preferred_locations or [],
    }
    return answer_mentor_question(
        message=payload.message,
        language=payload.language,
        profile=prof_dict,
        verified=verified,
        intel=latest.get("skill_intelligence") or {},
        careers=latest.get("careers") or [],
        top_jobs=latest.get("top_jobs") or [],
        courses=latest.get("recommended_courses") or [],
        roadmap=_build_roadmap_response(db, user),
    )
