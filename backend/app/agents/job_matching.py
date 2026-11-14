"""Agent 5 — Job Requirement and Opportunity Agent: matches student skills to actual company vacancies."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

from app.agents.state import OrchestratorState, run_traced
from app.services.scoring import score_job_match


def _ns(d: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(**d)


def _effective_verification_status(job: Any) -> str:
    if bool(getattr(job, "is_demo", False)):
        return "Synthetic Demo"
    raw = getattr(job, "verification_status", None) or "Pending Verification"
    deadline = getattr(job, "deadline", None)
    if deadline is not None:
        dl = date.fromisoformat(deadline) if isinstance(deadline, str) else deadline
        if dl < date.today() and raw == "Verified":
            return "Expired"
    return raw


def is_verified_real_job(job: Any) -> bool:
    """Return True only for non-synthetic jobs with Verified status and source evidence."""
    if bool(getattr(job, "is_demo", False)):
        return False
    if _effective_verification_status(job) != "Verified":
        return False
    apply_url = str(getattr(job, "apply_url", "") or "").strip()
    source = str(getattr(job, "source", "") or "").strip()
    last_verified = getattr(job, "last_verified_date", None)
    return apply_url.startswith("https://") and bool(source) and last_verified is not None


def format_job_summary(job: Any, match: dict[str, Any], saved: bool = False) -> dict[str, Any]:
    s_min = getattr(job, "salary_min_lpa", None)
    s_max = getattr(job, "salary_max_lpa", None)
    disclosed = s_min is not None or s_max is not None
    if disclosed:
        lo = s_min if s_min is not None else s_max
        hi = s_max if s_max is not None else s_min
        sal_label = f"₹{lo:g}–{hi:g} LPA" if lo != hi else f"₹{lo:g} LPA"
    else:
        sal_label = "Not Disclosed"

    matching = [m["skill"] for m in match["strong_matches"]] + [m["skill"] for m in match["partial_matches"]]
    missing = match["missing_mandatory"] + match["missing_preferred"]
    posted = getattr(job, "posted_date", "")
    last_verified = getattr(job, "last_verified_date", None)
    deadline = getattr(job, "deadline", None)
    is_demo = bool(getattr(job, "is_demo", False))
    ver_status = _effective_verification_status(job)
    return {
        "id": getattr(job, "id", None),
        "company": getattr(job, "company", ""),
        "title": getattr(job, "title", ""),
        "location": getattr(job, "location", ""),
        "work_mode": getattr(job, "work_mode", ""),
        "salary": {"min_lpa": s_min, "max_lpa": s_max, "disclosed": disclosed, "label": sal_label},
        "experience_min_years": getattr(job, "experience_min_years", 0.0),
        "posted_date": posted.isoformat() if hasattr(posted, "isoformat") else str(posted),
        "last_verified_date": last_verified.isoformat() if hasattr(last_verified, "isoformat") else (str(last_verified) if last_verified else None),
        "deadline": deadline.isoformat() if hasattr(deadline, "isoformat") else (str(deadline) if deadline else None),
        "apply_url": getattr(job, "apply_url", ""),
        "source": getattr(job, "source", ""),
        "is_demo": is_demo,
        "verification_status": ver_status,
        "mandatory_skills": list(getattr(job, "mandatory_skills", []) or []),
        "preferred_skills": list(getattr(job, "preferred_skills", []) or []),
        "matching_skills": list(dict.fromkeys(matching)),
        "missing_skills": list(dict.fromkeys(missing)),
        "score": match["score"],
        "saved": saved,
    }


def job_matching_node(state: OrchestratorState) -> dict[str, Any]:
    def _run(s: OrchestratorState) -> dict[str, Any]:
        profile_ns = _ns(s.get("profile") or {})
        verified = s.get("verified_skills") or []
        jobs = s.get("jobs") or []

        scored: list[dict[str, Any]] = []
        excluded = 0
        for job_dict in jobs:
            job_ns = _ns(job_dict)
            if not is_verified_real_job(job_ns):
                excluded += 1
                continue
            match = score_job_match(job_ns, profile_ns, verified)
            scored.append(format_job_summary(job_ns, match, saved=bool(job_dict.get("saved", False))))

        scored.sort(key=lambda j: (-j["score"], j["company"]))
        top_jobs = scored[:5]
        return {
            "top_jobs": top_jobs,
            "_trace_summary": f"Matched profile against {len(scored)} verified vacancies ({excluded} unverified/expired excluded).",
            "_trace_decisions": [f"{j['company']} — {j['title']}: {j['score']}%" for j in top_jobs[:3]],
        }

    return run_traced("Job Requirement & Opportunity Agent", state, _run)
