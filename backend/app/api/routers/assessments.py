"""Verified skill assessment endpoints (Agent 1)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_orchestrator
from app.agents.skill_assessment import available_assessments, evaluate_attempt, select_questions
from app.api.deps import get_current_user
from app.data.catalog import canonical_skill
from app.db.models import AssessmentAttempt, Profile, User
from app.db.session import get_db
from app.schemas.all import AssessmentStartRequest, AssessmentSubmitRequest
from app.services.scoring import aggregate_verified_skills, proficiency_from_score

router = APIRouter(tags=["Assessments"])


@router.get("/api/assessments/available")
def get_available_assessments() -> list[dict[str, Any]]:
    return available_assessments()


@router.post("/api/assessments/start", status_code=status.HTTP_201_CREATED)
def start_assessment(
    payload: AssessmentStartRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    skill = canonical_skill(payload.skill)
    questions = select_questions(skill, payload.level)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No assessment bank available yet for skill '{payload.skill}'.",
        )

    attempt = AssessmentAttempt(
        user_id=user.id,
        skill=skill,
        level=payload.level,
        question_ids=[q["id"] for q in questions],
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    safe_questions = [
        {
            "id": q["id"],
            "type": q["type"],
            "topic": q["topic"],
            "prompt": q["prompt"],
            "code": q.get("code"),
            "options": q.get("options"),
        }
        for q in questions
    ]
    return {
        "attempt_id": attempt.id,
        "skill": skill,
        "level": payload.level,
        "questions": safe_questions,
    }


@router.post("/api/assessments/{attempt_id}/submit")
def submit_assessment(
    attempt_id: int,
    payload: AssessmentSubmitRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    attempt = db.get(AssessmentAttempt, attempt_id)
    if not attempt or attempt.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment attempt not found.")
    if attempt.completed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment attempt already submitted.")

    evaluation = evaluate_attempt(attempt.question_ids, payload.answers, attempt.level)
    attempt.answers = payload.answers
    attempt.raw_percent = evaluation["raw_percent"]
    attempt.score = evaluation["score"]
    attempt.topic_breakdown = evaluation["topic_breakdown"]
    attempt.completed_at = datetime.now(UTC)
    db.add(attempt)
    db.commit()

    # Recalculate verified score + rerun multi-agent orchestrator
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.completed_at.is_not(None))
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    verified = aggregate_verified_skills(attempts, (profile.technical_skills if profile else []) or [])
    skill_entry = next((v for v in verified if v["skill"] == attempt.skill), None)
    verified_score = skill_entry["verified_score"] if skill_entry else evaluation["score"]

    run_orchestrator(db, user, trigger="assessment_completed")

    return {
        "attempt_id": attempt.id,
        "skill": attempt.skill,
        "level": attempt.level,
        "score": evaluation["score"],
        "correct": evaluation["correct"],
        "total": evaluation["total"],
        "topic_breakdown": evaluation["topic_breakdown"],
        "strong_topics": evaluation["strong_topics"],
        "weak_topics": evaluation["weak_topics"],
        "recommendations": evaluation["recommendations"],
        "verified_score": verified_score,
        "proficiency": proficiency_from_score(verified_score),
        "review": evaluation["review"],
    }


@router.get("/api/assessments/history")
def assessment_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.completed_at.is_not(None))
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    return [
        {
            "attempt_id": r.id,
            "skill": r.skill,
            "level": r.level,
            "score": r.score,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]


@router.get("/api/skills/verified")
def get_verified_skills(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.completed_at.is_not(None))
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    return aggregate_verified_skills(attempts, (profile.technical_skills if profile else []) or [])
