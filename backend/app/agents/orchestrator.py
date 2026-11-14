"""Central LangGraph Orchestrator coordinating all 7 ThiranSetu agents with conditional routing."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.career_matching import career_matching_node
from app.agents.career_mentor import career_mentor_node
from app.agents.course_discovery import course_discovery_node
from app.agents.job_matching import job_matching_node
from app.agents.market_intelligence import market_intelligence_node
from app.agents.skill_assessment import assessment_agent_node
from app.agents.skill_intelligence import skill_intelligence_node
from app.agents.state import OrchestratorState, run_traced
from app.core.config import get_settings
from app.data.catalog import canonical_skill
from app.db.models import AgentRun, Application, AssessmentAttempt, Job, Profile, RoadmapStep, User
from app.services.scoring import aggregate_verified_skills, extract_requirements_from_text


class VacancyRequirements(BaseModel):
    job_id: int | None = None
    company: str = ""
    title: str = ""
    role_id: str | None = None
    mandatory_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    education: str = ""
    experience_min_years: float = 0.0
    location: str = ""
    work_mode: str = "hybrid"


def _targeted_practice_node(state: OrchestratorState) -> dict[str, Any]:
    """Conditional node triggered when any verified skill scores below 60%."""

    def _run(s: OrchestratorState) -> dict[str, Any]:
        intel = dict(s.get("skill_intelligence") or {})
        weak = intel.get("weak") or []
        boost = [f"Priority Retake Prep: {w['skill']} — {w.get('weak_topics') or ['core fundamentals']}" for w in weak]
        existing = intel.get("targeted_practice") or []
        intel["targeted_practice"] = list(dict.fromkeys(boost + existing))
        return {
            "skill_intelligence": intel,
            "_trace_summary": f"Added {len(boost)} targeted practice directives due to <60% assessment score.",
            "_trace_decisions": boost,
        }

    return run_traced("Targeted Practice Escalation", state, _run)


def _vacancy_requirement_sync_node(state: OrchestratorState) -> dict[str, Any]:
    """Conditional node triggered when a new company vacancy is added (`trigger == 'job_added'`)."""

    def _run(s: OrchestratorState) -> dict[str, Any]:
        jobs = s.get("jobs") or []
        custom_jobs = [j for j in jobs if not j.get("is_demo")]
        target_job = custom_jobs[0] if custom_jobs else None
        if not target_job:
            return {
                "vacancy_requirements": {},
                "_trace_task": "Inspect newly added company vacancy requirements",
                "_trace_summary": "No non-synthetic vacancy found; continuing standard pipeline.",
                "_trace_decisions": [],
            }

        extracted = extract_requirements_from_text(str(target_job.get("description") or ""))
        raw_mandatory = target_job.get("mandatory_skills") or extracted.get("mandatory_skills") or []
        raw_preferred = target_job.get("preferred_skills") or extracted.get("preferred_skills") or []
        mandatory = list(dict.fromkeys(canonical_skill(sk) for sk in raw_mandatory if str(sk).strip()))
        preferred = list(
            dict.fromkeys(
                canonical_skill(sk)
                for sk in raw_preferred
                if str(sk).strip() and canonical_skill(sk) not in mandatory
            )
        )
        validated = VacancyRequirements(
            job_id=target_job.get("id"),
            company=str(target_job.get("company") or ""),
            title=str(target_job.get("title") or ""),
            role_id=target_job.get("role_id"),
            mandatory_skills=mandatory,
            preferred_skills=preferred,
            education=str(target_job.get("education") or extracted.get("education") or ""),
            experience_min_years=float(
                target_job.get("experience_min_years")
                if target_job.get("experience_min_years") is not None
                else (extracted.get("experience_years") or 0.0)
            ),
            location=str(target_job.get("location") or extracted.get("location") or ""),
            work_mode=str(target_job.get("work_mode") or extracted.get("work_mode") or "hybrid"),
        )
        req_dict = validated.model_dump()
        return {
            "vacancy_requirements": req_dict,
            "_trace_task": "Extract, validate & store company vacancy requirements in shared state",
            "_trace_input": f"{validated.company} — {validated.title}",
            "_trace_summary": (
                f"Synced {len(mandatory)} mandatory and {len(preferred)} preferred skills "
                f"({validated.location or 'Unspecified'}, {validated.work_mode}) to shared state."
            ),
            "_trace_decisions": [
                f"Mandatory: {', '.join(mandatory) or 'None'}",
                f"Preferred: {', '.join(preferred) or 'None'}",
                f"Education: {validated.education or 'Not specified'} | Min Exp: {validated.experience_min_years}y",
            ],
        }

    return run_traced("Vacancy Requirement Sync", state, _run)


def _route_after_assessment(state: OrchestratorState) -> str:
    if state.get("trigger") == "job_added":
        return "vacancy_requirement_sync"
    return "skill_intelligence"


def _route_after_intelligence(state: OrchestratorState) -> str:
    if state.get("needs_targeted_practice"):
        return "targeted_practice"
    return "market_intelligence"


@lru_cache(maxsize=1)
def build_graph():
    graph = StateGraph(OrchestratorState)
    graph.add_node("skill_assessment", assessment_agent_node)
    graph.add_node("vacancy_requirement_sync", _vacancy_requirement_sync_node)
    graph.add_node("skill_intelligence", skill_intelligence_node)
    graph.add_node("targeted_practice", _targeted_practice_node)
    graph.add_node("market_intelligence", market_intelligence_node)
    graph.add_node("career_matching", career_matching_node)
    graph.add_node("job_matching", job_matching_node)
    graph.add_node("course_discovery", course_discovery_node)
    graph.add_node("career_mentor", career_mentor_node)

    graph.add_edge(START, "skill_assessment")
    graph.add_conditional_edges(
        "skill_assessment",
        _route_after_assessment,
        {"vacancy_requirement_sync": "vacancy_requirement_sync", "skill_intelligence": "skill_intelligence"},
    )
    graph.add_edge("vacancy_requirement_sync", "skill_intelligence")
    graph.add_conditional_edges(
        "skill_intelligence",
        _route_after_intelligence,
        {"targeted_practice": "targeted_practice", "market_intelligence": "market_intelligence"},
    )
    graph.add_edge("targeted_practice", "market_intelligence")
    graph.add_edge("market_intelligence", "career_matching")
    graph.add_edge("career_matching", "job_matching")
    graph.add_edge("job_matching", "course_discovery")
    graph.add_edge("course_discovery", "career_mentor")
    graph.add_edge("career_mentor", END)
    return graph.compile()


def _serialize_profile(user: User, profile: Profile) -> dict[str, Any]:
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
    }


def _sync_roadmap_steps(db: Session, user_id: int, roadmap: dict[str, Any], sync_steps: bool) -> list[dict[str, Any]]:
    existing = list(
        db.scalars(select(RoadmapStep).where(RoadmapStep.user_id == user_id).order_by(RoadmapStep.order)).all()
    )
    if not sync_steps and existing:
        # Return existing persisted steps so user status edits are preserved
        from app.data.catalog import load_verified_courses

        course_by_id = {c["id"]: c for c in load_verified_courses()}
        return [
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
            for st in existing
        ]

    prev_status = {st.skill: (st.status, st.reassessment_required) for st in existing}
    for st in existing:
        db.delete(st)
    db.flush()

    from app.data.catalog import load_verified_courses

    course_by_id = {c["id"]: c for c in load_verified_courses()}
    target_role_id = roadmap.get("target_role", {}).get("id") if roadmap.get("target_role") else None
    out_steps: list[dict[str, Any]] = []
    for raw in roadmap.get("steps") or []:
        status_val, reassess_val = prev_status.get(raw["skill"], (raw["status"], raw["reassessment_required"]))
        if raw.get("current_score") is not None and float(raw["current_score"]) >= 70:
            reassess_val = False
        row = RoadmapStep(
            user_id=user_id,
            order=raw["order"],
            skill=raw["skill"],
            priority=raw["priority"],
            reason=raw["reason"],
            course_id=raw.get("course_id"),
            estimated_hours=raw["estimated_hours"],
            exercise=raw["exercise"],
            project=raw["project"],
            status=status_val,
            reassessment_required=reassess_val,
            current_score=raw.get("current_score"),
            target_score=raw["target_score"],
            target_role=target_role_id,
            roadmap_reason=roadmap.get("reason", ""),
        )
        db.add(row)
        db.flush()
        out_steps.append(
            {
                "id": row.id,
                "order": row.order,
                "skill": row.skill,
                "priority": row.priority,
                "reason": row.reason,
                "course": course_by_id.get(row.course_id) if row.course_id else None,
                "estimated_hours": row.estimated_hours,
                "exercise": row.exercise,
                "project": row.project,
                "status": row.status,
                "reassessment_required": row.reassessment_required,
                "current_score": row.current_score,
                "target_score": row.target_score,
            }
        )
    return out_steps


def run_orchestrator(db: Session, user: User, trigger: str = "manual", sync_roadmap: bool = True) -> dict[str, Any]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if not profile:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.flush()

    attempts = list(
        db.scalars(
            select(AssessmentAttempt)
            .where(AssessmentAttempt.user_id == user.id, AssessmentAttempt.completed_at.is_not(None))
            .order_by(AssessmentAttempt.completed_at.desc())
        ).all()
    )
    verified = aggregate_verified_skills(attempts, profile.technical_skills or [])

    saved_ids = set(db.scalars(select(Application.job_id).where(Application.user_id == user.id)).all())
    jobs = list(
        db.scalars(
            select(Job)
            .where(Job.is_demo.is_(False))
            .order_by(Job.id.desc(), Job.posted_date.desc())
        ).all()
    )
    job_dicts = [
        {
            "id": j.id,
            "company": j.company,
            "title": j.title,
            "role_id": j.role_id,
            "description": j.description,
            "mandatory_skills": j.mandatory_skills,
            "preferred_skills": j.preferred_skills,
            "education": j.education,
            "experience_min_years": j.experience_min_years,
            "location": j.location,
            "work_mode": j.work_mode,
            "salary_min_lpa": j.salary_min_lpa,
            "salary_max_lpa": j.salary_max_lpa,
            "posted_date": j.posted_date,
            "last_verified_date": j.last_verified_date,
            "deadline": j.deadline,
            "apply_url": j.apply_url,
            "source": j.source,
            "verification_status": j.verification_status,
            "is_demo": j.is_demo,
            "saved": j.id in saved_ids,
        }
        for j in jobs
    ]

    initial_state: OrchestratorState = {
        "user_id": user.id,
        "trigger": trigger,
        "llm_mode": "gemini" if get_settings().llm_available else "deterministic",
        "profile": _serialize_profile(user, profile),
        "verified_skills": verified,
        "jobs": job_dicts,
        "trace": [],
    }
    final_state = build_graph().invoke(initial_state)

    raw_roadmap = final_state.get("roadmap") or {}
    synced_steps = _sync_roadmap_steps(db, user.id, raw_roadmap, sync_steps=sync_roadmap)
    completed_count = sum(1 for st in synced_steps if st["status"] == "completed")
    progress_pct = int(round(100 * completed_count / len(synced_steps))) if synced_steps else 0

    full_roadmap = {
        "target_role": raw_roadmap.get("target_role"),
        "generated_at": "",
        "reason": raw_roadmap.get("reason", ""),
        "progress_percent": progress_pct,
        "steps": synced_steps,
    }

    top_career_score = final_state["careers"][0]["score"] if final_state.get("careers") else 0.0
    payload = {
        "trigger": trigger,
        "llm_mode": final_state.get("llm_mode", "deterministic"),
        "trace": final_state.get("trace", []),
        "skill_intelligence": final_state.get("skill_intelligence", {}),
        "market": final_state.get("market", {}),
        "careers": final_state.get("careers", []),
        "top_jobs": final_state.get("top_jobs", []),
        "recommended_courses": final_state.get("recommended_courses", []),
        "roadmap": full_roadmap,
        "mentor_brief": final_state.get("mentor_brief", ""),
    }

    run_row = AgentRun(
        user_id=user.id,
        trigger=trigger,
        llm_mode=payload["llm_mode"],
        readiness=top_career_score,
        result=payload,
    )
    db.add(run_row)
    db.commit()
    db.refresh(run_row)

    full_roadmap["generated_at"] = run_row.created_at.isoformat()
    payload["run_id"] = run_row.id
    payload["created_at"] = run_row.created_at.isoformat()
    return payload


def get_latest_orchestrator_run(db: Session, user: User) -> dict[str, Any]:
    latest = db.scalar(
        select(AgentRun).where(AgentRun.user_id == user.id).order_by(AgentRun.id.desc())
    )
    if not latest:
        return run_orchestrator(db, user, trigger="manual")
    res = dict(latest.result)
    res["run_id"] = latest.id
    res["created_at"] = latest.created_at.isoformat()
    if "roadmap" in res and not res["roadmap"].get("generated_at"):
        res["roadmap"]["generated_at"] = latest.created_at.isoformat()
    return res
