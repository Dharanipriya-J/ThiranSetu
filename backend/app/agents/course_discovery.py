"""Agent 6 — Course Discovery & Adaptive Learning Path Agent."""

from __future__ import annotations

from typing import Any

from app.agents.state import OrchestratorState, run_traced
from app.data.catalog import canonical_skill, is_verified_course, load_courses, load_roles, load_verified_courses

_EXERCISES = {
    "Python": "Build a CLI CSV telemetry cleaner using type hints, pathlib, and pytest unit tests.",
    "SQL": "Write 5 queries using INNER/LEFT JOIN, CTEs, and DENSE_RANK() on a multi-table sales schema.",
    "Excel": "Create a dynamic KPI dashboard using XLOOKUP, SUMIFS, and a PivotTable with slicers.",
    "Power BI": "Model a 3-table star schema in Power BI and author 4 DAX measures using CALCULATE().",
    "Machine Learning": "Train a scikit-learn Pipeline (StandardScaler + LogisticRegression) and report PR-AUC.",
    "JavaScript": "Build an async fetch client with error handling, debounced search, and DOM textContent updates.",
    "React": "Create a filterable data table component with TypeScript interfaces and keyboard-accessible controls.",
    "Node.js": "Build a validated Express/REST endpoint with parameterized SQLite queries and error middleware.",
    "TypeScript": "Convert a JS API client to strict TypeScript with discriminated union error states.",
    "FastAPI": "Build a Pydantic-validated FastAPI router with dependency injection and pytest TestClient coverage.",
    "Generative AI": "Implement a prompt evaluation script comparing structured JSON outputs against ground truth.",
    "LangGraph": "Build a 3-node StateGraph with a conditional edge and deterministic fallback.",
    "Docker": "Write a multi-stage Dockerfile running as a non-root user and verify image size.",
    "Cloud Computing": "Containerize a REST API and configure environment-driven secret injection.",
    "Cybersecurity": "Audit an API for OWASP Top 10 risks (SQLi, XSS, broken auth, header spoofing).",
}


def find_courses_for_skills(
    skills: list[str],
    preferred_language: str = "en",
    limit_per_skill: int = 3,
) -> list[dict[str, Any]]:
    courses = load_verified_courses()
    groups: list[dict[str, Any]] = []
    for raw in skills:
        sk = canonical_skill(raw)
        matches = [c for c in courses if sk in c.get("skills", [])]

        def _lang_rank(c: dict[str, Any]) -> tuple[int, int, int]:
            exact = 0 if c["language"] == preferred_language else 1
            sub = 0 if preferred_language in (c.get("subtitle_languages") or []) else 1
            free = 0 if c["price"]["is_free"] else 1
            return (exact, sub, free)

        matches.sort(key=_lang_rank)
        if matches:
            groups.append(
                {
                    "skill": sk,
                    "reason": f"Targeted to close your skill gap in {sk}",
                    "courses": matches[:limit_per_skill],
                }
            )
    return groups


def find_multilingual_equivalents(course_id: str, target_language: str) -> dict[str, Any] | None:
    courses = load_courses()
    verified_courses = load_verified_courses()
    source = next((c for c in courses if c["id"] == course_id), None)
    if not source:
        return None
    src_skills = set(source.get("skills") or [])
    src_outcomes = set(source.get("outcomes") or [])

    equivalents: list[dict[str, Any]] = []
    for cand in verified_courses:
        if cand["id"] == course_id:
            continue
        lang_match = (
            cand["language"] == target_language
            or target_language in (cand.get("audio_languages") or [])
            or target_language in (cand.get("subtitle_languages") or [])
        )
        if not lang_match:
            continue
        c_skills = set(cand.get("skills") or [])
        c_outcomes = set(cand.get("outcomes") or [])
        shared_skills = sorted(src_skills & c_skills)
        shared_outcomes = sorted(src_outcomes & c_outcomes)
        if not shared_skills:
            continue
        union_count = len(src_skills | c_skills) + len(src_outcomes | c_outcomes)
        overlap_count = len(shared_skills) + len(shared_outcomes)
        overlap_pct = round(100.0 * overlap_count / max(1, union_count), 1)
        if shared_outcomes:
            eq_status = "syllabus_verified"
            verdict = (
                f"Syllabus-verified equivalent ({overlap_pct}% overlap across skills and learning outcomes) "
                f"with {target_language.upper()} audio/subtitles."
            )
        else:
            eq_status = "potential_skill_overlap"
            verdict = (
                f"Potential skill overlap ({overlap_pct}% skill-tag overlap; "
                f"syllabus equivalence not verified) with {target_language.upper()} audio/subtitles."
            )
        equivalents.append(
            {
                "course": cand,
                "overlap_percent": overlap_pct,
                "shared_skills": shared_skills,
                "shared_outcomes": shared_outcomes,
                "equivalence_status": eq_status,
                "verdict": verdict,
            }
        )
    equivalents.sort(key=lambda e: (-int(e["equivalence_status"] == "syllabus_verified"), -e["overlap_percent"]))
    return {"course": source, "language": target_language, "equivalents": equivalents}


def build_roadmap_steps(
    profile: dict[str, Any],
    verified_skills: list[dict[str, Any]],
    intel: dict[str, Any],
    careers: list[dict[str, Any]],
    trigger: str,
) -> tuple[dict[str, Any] | None, str, list[dict[str, Any]]]:
    roles = {r["id"]: r for r in load_roles()}
    target_id = profile.get("target_role")
    if not target_id and careers:
        target_id = careers[0]["role_id"]
    target_role = roles.get(target_id) if target_id else None
    target_meta = {"id": target_role["id"], "title": target_role["title"]} if target_role else None

    verified_map = {v["skill"]: v for v in verified_skills}
    lang = profile.get("learning_language") or "en"

    # Prioritize: 1) weak verified skills (<70), 2) missing skills for target role, 3) unverified skills
    candidates: list[tuple[str, str, str]] = []  # (skill, priority, reason)
    seen: set[str] = set()

    for wk in intel.get("weak") or []:
        sk = wk["skill"]
        if sk not in seen:
            seen.add(sk)
            candidates.append((sk, "high", wk["reason"]))

    vac_gaps = intel.get("vacancy_gaps") or {}
    for sk in vac_gaps.get("mandatory_missing") or []:
        if sk not in seen:
            seen.add(sk)
            candidates.append(
                (sk, "high", f"Mandatory requirement for {vac_gaps.get('company', 'synced company')} ({vac_gaps.get('title', 'vacancy')}).")
            )

    if target_role:
        for req in target_role["skills"]:
            sk = req["skill"]
            if sk in seen:
                continue
            entry = verified_map.get(sk)
            if not entry:
                seen.add(sk)
                prio = "high" if req["importance"] == "core" else "medium"
                candidates.append((sk, prio, f"Missing {req['importance']} skill required for {target_role['title']}."))
            elif entry.get("verified_score") is None:
                seen.add(sk)
                candidates.append((sk, "medium", f"Self-reported only; verify {sk} through assessment."))
            elif float(entry["verified_score"]) < 70:
                seen.add(sk)
                candidates.append((sk, "high", f"Verified score {entry['verified_score']}% is below 70% target."))

    for miss in (intel.get("missing") or [])[:4]:
        sk = miss["skill"]
        if sk not in seen:
            seen.add(sk)
            candidates.append((sk, "low", f"In-demand skill across {', '.join(miss['required_by'][:2])}."))

    steps: list[dict[str, Any]] = []
    for idx, (sk, prio, reason) in enumerate(candidates[:6], start=1):
        matched_groups = find_courses_for_skills([sk], preferred_language=lang, limit_per_skill=1)
        course = matched_groups[0]["courses"][0] if matched_groups else None
        if course is not None and not is_verified_course(course):
            course = None
        entry = verified_map.get(sk)
        curr_score = entry.get("verified_score") if entry else None
        steps.append(
            {
                "order": idx,
                "skill": sk,
                "priority": prio,
                "reason": reason,
                "course_id": course["id"] if course else None,
                "estimated_hours": int(course.get("duration_hours") or 12) if course else 12,
                "exercise": _EXERCISES.get(sk, f"Complete 3 practical exercises focusing on {sk} core concepts."),
                "project": (
                    f"Build a portfolio mini-project applying {sk} to a {target_role['title']} problem."
                    if target_role
                    else f"Build a documented mini-project demonstrating {sk}."
                ),
                "status": "not_started",
                "reassessment_required": False,
                "current_score": curr_score,
                "target_score": 70,
            }
        )

    reason_text = f"Adaptive roadmap updated on trigger '{trigger}'" + (
        f" for target career {target_role['title']}." if target_role else "."
    )
    return target_meta, reason_text, steps


def course_discovery_node(state: OrchestratorState) -> dict[str, Any]:
    def _run(s: OrchestratorState) -> dict[str, Any]:
        profile = s.get("profile") or {}
        verified = s.get("verified_skills") or []
        intel = s.get("skill_intelligence") or {}
        careers = s.get("careers") or []
        trigger = s.get("trigger") or "manual"
        lang = profile.get("learning_language") or "en"

        vac_gaps = intel.get("vacancy_gaps") or {}
        gap_skills = (
            list(vac_gaps.get("mandatory_missing") or [])
            + [w["skill"] for w in (intel.get("weak") or [])]
            + [m["skill"] for m in (intel.get("missing") or [])]
        )
        if not gap_skills and careers:
            gap_skills = careers[0].get("learning_path") or []
        recommended_courses = find_courses_for_skills(list(dict.fromkeys(gap_skills))[:5], preferred_language=lang)

        target_meta, roadmap_reason, steps = build_roadmap_steps(profile, verified, intel, careers, trigger)
        roadmap = {
            "target_role": target_meta,
            "reason": roadmap_reason,
            "steps": steps,
        }
        return {
            "recommended_courses": recommended_courses,
            "roadmap": roadmap,
            "_trace_summary": f"Curated {len(recommended_courses)} course groups and {len(steps)} adaptive roadmap steps.",
            "_trace_decisions": [f"Step {st['order']}: {st['skill']} ({st['priority']})" for st in steps[:3]],
        }

    return run_traced("Course Discovery & Learning Path Agent", state, _run)
