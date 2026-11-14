"""Agent 7 — AI Career Mentor Agent: provides grounded, profile-aware guidance in 8 languages."""

from __future__ import annotations

import json
from typing import Any

from app.agents.state import OrchestratorState, run_traced
from app.services.gemini_client import generate_text, language_name

_INTENT_LABELS = {
    "career": ("career", "Which career suits me"),
    "missing": ("missing", "Missing & weak skills"),
    "course": ("course", "Recommended courses"),
    "job": ("job", "Company job compatibility"),
    "salary": ("salary", "Salary expectations"),
    "roadmap": ("roadmap", "Learning roadmap"),
}


def detect_intent(message: str) -> str:
    low = message.lower()
    if any(k in low for k in ["salary", "lpa", "pay", "ctc", "package"]):
        return "salary"
    if any(k in low for k in ["course", "learn first", "study", "tutorial", "nptel", "coursera"]):
        return "course"
    if any(k in low for k in ["company", "job", "opening", "vacancy", "zoho", "freshworks", "tcs", "apply"]):
        return "job"
    if any(k in low for k in ["missing", "weak", "gap", "lack", "improve"]):
        return "missing"
    if any(k in low for k in ["roadmap", "plan", "step", "next"]):
        return "roadmap"
    return "career"


def _deterministic_reply(
    message: str,
    language: str,
    profile: dict[str, Any],
    verified: list[dict[str, Any]],
    intel: dict[str, Any],
    careers: list[dict[str, Any]],
    top_jobs: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    roadmap: dict[str, Any],
) -> tuple[str, str, list[str]]:
    intent = detect_intent(message)
    top_career = careers[0] if careers else None
    weak = [w["skill"] for w in (intel.get("weak") or [])]
    missing = [m["skill"] for m in (intel.get("missing") or [])]
    strong = [f"{s['skill']} ({s['score']}%)" for s in (intel.get("strong") or [])]

    parts: list[str] = []
    if intent == "career" and top_career:
        parts.append(
            f"Based on your profile, your strongest career alignment is {top_career['title']} "
            f"({top_career['score']}% — {top_career['label']}). "
            f"{top_career['explanation']}"
        )
        if len(careers) > 1:
            parts.append(f"Runner-up: {careers[1]['title']} ({careers[1]['score']}%).")
    elif intent == "missing":
        parts.append(
            f"Verified strengths: {', '.join(strong) if strong else 'none verified yet'}. "
            f"Weak skills (<70%): {', '.join(weak) if weak else 'none'}. "
            f"Missing skills for your target/interested roles: {', '.join(missing[:5]) if missing else 'none'}."
        )
    elif intent == "course":
        if courses:
            first_group = courses[0]
            first_course = first_group["courses"][0]
            parts.append(
                f"Start with {first_group['skill']} ({first_group['reason']}): "
                f"'{first_course['title']}' on {first_course['platform']} ({first_course['price']['label']})."
            )
        else:
            parts.append("Take an assessment first so ThiranSetu can pinpoint exact course gaps.")
    elif intent == "job":
        if top_jobs:
            j = top_jobs[0]
            parts.append(
                f"Top company match: {j['company']} — {j['title']} ({j['score']}% compatibility, {j['salary']['label']}). "
                f"Matching: {', '.join(j['matching_skills']) or 'none'}. "
                f"Missing to improve compatibility: {', '.join(j['missing_skills']) or 'none'}."
            )
        else:
            parts.append("No matching vacancies loaded yet.")
    elif intent == "salary":
        exp = profile.get("expected_salary_lpa")
        min_s = profile.get("min_salary_lpa")
        sal_jobs = [j for j in top_jobs if j["salary"]["disclosed"]]
        if exp is None and min_s is None:
            parts.append("Add your expected and minimum acceptable salary (LPA) in Profile to compare against vacancies.")
        elif sal_jobs:
            summary = "; ".join(f"{j['company']} {j['title']} ({j['salary']['label']}, {j['score']}% fit)" for j in sal_jobs[:3])
            parts.append(f"Comparing against your ₹{exp or min_s:g} LPA target: {summary}.")
        else:
            parts.append("Current top openings list salary as Not Disclosed.")
    else:
        steps = roadmap.get("steps") or []
        if steps:
            s1 = steps[0]
            parts.append(
                f"Next roadmap step (#{s1['order']}, {s1['priority']} priority): learn {s1['skill']} "
                f"(~{s1['estimated_hours']}h) and complete: {s1['exercise']}"
            )
        else:
            parts.append("Your roadmap is clear! Complete an assessment or select a target career to generate steps.")

    if language != "en":
        parts.append(f"[Deterministic fallback note: detailed translation unavailable without Gemini API key; requested {language_name(language)}.]")

    sources = ["Student Profile", "Verified Assessments", "Skill Intelligence", "Career Rankings", "Company Vacancies", "Adaptive Roadmap"]
    return " ".join(parts), intent, sources


def answer_mentor_question(
    message: str,
    language: str,
    profile: dict[str, Any],
    verified: list[dict[str, Any]],
    intel: dict[str, Any],
    careers: list[dict[str, Any]],
    top_jobs: list[dict[str, Any]],
    courses: list[dict[str, Any]],
    roadmap: dict[str, Any],
) -> dict[str, Any]:
    intent = detect_intent(message)
    context = {
        "verified_skills": verified,
        "strong": intel.get("strong", []),
        "weak": intel.get("weak", []),
        "missing": intel.get("missing", []),
        "top_careers": [{"title": c["title"], "score": c["score"], "label": c["label"], "missing": c["missing_skills"]} for c in careers[:3]],
        "top_jobs": [{"company": j["company"], "title": j["title"], "score": j["score"], "salary": j["salary"]["label"], "missing": j["missing_skills"]} for j in top_jobs[:3]],
        "salary_expectation_lpa": profile.get("expected_salary_lpa"),
        "min_salary_lpa": profile.get("min_salary_lpa"),
        "preferred_locations": profile.get("preferred_locations", []),
        "roadmap_steps": [{"order": s["order"], "skill": s["skill"], "priority": s["priority"], "status": s.get("status")} for s in (roadmap.get("steps") or [])[:4]],
    }
    sys_prompt = (
        "You are the ThiranSetu AI Career Mentor. Answer concisely, accurately, and practically using ONLY the "
        "student context JSON provided. Never invent salaries, jobs, or employment guarantees. "
        f"Respond in {language_name(language)}. Keep the brand name strictly as 'ThiranSetu' in English."
    )
    user_prompt = f"Student context:\n{json.dumps(context, default=str)}\n\nStudent question: {message}"

    text, mode = generate_text(user_prompt, system_instruction=sys_prompt)
    sources = ["Student Profile", "Verified Assessments", "Career Rankings", "Company Vacancies", "Adaptive Roadmap"]
    if text:
        return {"reply": text, "mode": mode, "intent": intent, "sources": sources}

    fallback_text, intent, sources = _deterministic_reply(
        message, language, profile, verified, intel, careers, top_jobs, courses, roadmap
    )
    return {"reply": fallback_text, "mode": "deterministic", "intent": intent, "sources": sources}


def career_mentor_node(state: OrchestratorState) -> dict[str, Any]:
    def _run(s: OrchestratorState) -> dict[str, Any]:
        profile = s.get("profile") or {}
        verified = s.get("verified_skills") or []
        intel = s.get("skill_intelligence") or {}
        careers = s.get("careers") or []
        top_jobs = s.get("top_jobs") or []
        courses = s.get("recommended_courses") or []
        roadmap = s.get("roadmap") or {}
        lang = profile.get("app_language") or "en"

        brief_res = answer_mentor_question(
            "Summarize my top career fit, biggest skill gap, and next step.",
            lang,
            profile,
            verified,
            intel,
            careers,
            top_jobs,
            courses,
            roadmap,
        )
        return {
            "mentor_brief": brief_res["reply"],
            "llm_mode": brief_res["mode"],
            "_trace_summary": f"Generated mentor brief in {brief_res['mode']} mode.",
            "_trace_decisions": [f"Mode: {brief_res['mode']}"],
        }

    return run_traced("AI Career Mentor Agent", state, _run)
