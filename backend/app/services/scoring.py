"""Deterministic, explainable scoring algorithms for skills, careers, jobs, and salaries."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from app.data.catalog import canonical_skill, load_skills

_LEVEL_WEIGHT = {"beginner": 0.90, "intermediate": 1.00, "advanced": 1.08}
_SELF_BASELINE = {"beginner": 35.0, "intermediate": 55.0, "advanced": 75.0}

CAREER_WEIGHTS = {
    "skill_match": 0.45,
    "interest": 0.15,
    "market_demand": 0.15,
    "location": 0.10,
    "salary": 0.10,
    "experience": 0.05,
}

JOB_WEIGHTS = {
    "mandatory": 0.50,
    "preferred": 0.15,
    "experience": 0.10,
    "education": 0.05,
    "location": 0.10,
    "salary": 0.10,
}


def proficiency_from_score(score: float | None) -> str:
    if score is None:
        return "not_verified"
    if score >= 80:
        return "advanced"
    if score >= 60:
        return "intermediate"
    return "beginner"


def aggregate_verified_skills(
    attempts: list[Any],
    self_reported: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine assessment attempts and self-reported skills without conflating them.

    Uses recency-weighted average of the latest 3 completed attempts for each skill so
    one bad or good test never permanently locks a student's classification.
    """
    self_map: dict[str, str] = {}
    for item in self_reported or []:
        name = canonical_skill(str(item.get("name", "")))
        if name:
            self_map[name] = str(item.get("self_level", "beginner"))

    grouped: dict[str, list[Any]] = defaultdict(list)
    for att in attempts:
        if att.completed_at is not None and att.score is not None:
            grouped[canonical_skill(att.skill)].append(att)

    all_skills = sorted(set(self_map.keys()) | set(grouped.keys()))
    results: list[dict[str, Any]] = []
    recency_weights = [0.5, 0.3, 0.2]

    for skill in all_skills:
        skill_attempts = sorted(
            grouped.get(skill, []),
            key=lambda a: a.completed_at.replace(tzinfo=None) if a.completed_at else a.id,
            reverse=True,
        )
        self_level = self_map.get(skill)
        if skill_attempts:
            recent = skill_attempts[:3]
            weights = recency_weights[: len(recent)]
            total_w = sum(weights)
            weighted_score = sum(float(a.score) * w for a, w in zip(recent, weights, strict=True)) / total_w
            latest = recent[0]
            strong_topics: list[str] = []
            weak_topics: list[str] = []
            for tb in latest.topic_breakdown or []:
                if tb.get("percent", 0) >= 70:
                    strong_topics.append(tb["topic"])
                else:
                    weak_topics.append(tb["topic"])
            results.append(
                {
                    "skill": skill,
                    "self_reported_level": self_level,
                    "verified_score": round(weighted_score, 1),
                    "proficiency": proficiency_from_score(weighted_score),
                    "attempts": len(skill_attempts),
                    "last_assessed": latest.completed_at.isoformat(),
                    "strong_topics": strong_topics,
                    "weak_topics": weak_topics,
                    "status": "verified" if self_level else "assessed_only",
                }
            )
        else:
            results.append(
                {
                    "skill": skill,
                    "self_reported_level": self_level,
                    "verified_score": None,
                    "proficiency": "not_verified",
                    "attempts": 0,
                    "last_assessed": None,
                    "strong_topics": [],
                    "weak_topics": [],
                    "status": "self_reported",
                }
            )
    return results


def effective_skill_score(skill: str, verified_map: dict[str, dict[str, Any]]) -> tuple[float, bool]:
    """Return (score 0-100, is_verified). Unverified self-reported skills get conservative credit."""
    entry = verified_map.get(skill)
    if not entry:
        return 0.0, False
    if entry["verified_score"] is not None:
        return float(entry["verified_score"]), True
    # Unverified self-reported skills receive 40% of baseline so assessments meaningfully matter
    baseline = _SELF_BASELINE.get(entry.get("self_reported_level") or "beginner", 35.0)
    return round(baseline * 0.4, 1), False


def evaluate_salary_fit(
    job_min: float | None,
    job_max: float | None,
    expected: float | None,
    minimum: float | None,
) -> dict[str, Any]:
    if job_min is None and job_max is None:
        return {
            "status": "not_disclosed",
            "score": 55.0,
            "message": "Salary is Not Disclosed by the employer.",
        }
    j_min = float(job_min if job_min is not None else job_max)
    j_max = float(job_max if job_max is not None else job_min)
    if expected is None and minimum is None:
        return {
            "status": "no_preference",
            "score": 80.0,
            "message": f"Published range ₹{j_min:g}–{j_max:g} LPA (add your salary preferences to compare).",
        }
    exp = float(expected if expected is not None else minimum)
    min_acc = float(minimum if minimum is not None else exp * 0.85)

    if j_max >= exp and j_min <= exp:
        return {
            "status": "meets",
            "score": 100.0,
            "message": f"Published ₹{j_min:g}–{j_max:g} LPA meets your ₹{exp:g} LPA expectation.",
        }
    if j_min > exp:
        return {
            "status": "meets",
            "score": 100.0,
            "message": f"Published ₹{j_min:g}–{j_max:g} LPA exceeds your ₹{exp:g} LPA expectation.",
        }
    if j_max >= min_acc:
        return {
            "status": "overlap",
            "score": 75.0,
            "message": (
                f"Published ₹{j_min:g}–{j_max:g} LPA overlaps your minimum ₹{min_acc:g} LPA "
                f"(below ₹{exp:g} LPA target)."
            ),
        }
    return {
        "status": "below_minimum",
        "score": 25.0,
        "message": (
            f"Published ₹{j_min:g}–{j_max:g} LPA is below your minimum ₹{min_acc:g} LPA; "
            "building verified skills in high-demand areas can unlock higher brackets."
        ),
    }


def evaluate_location_fit(
    job_location: str,
    job_mode: str,
    preferred_locations: list[str],
    willing_to_relocate: bool,
    preferred_mode: str,
) -> dict[str, Any]:
    loc_lower = job_location.lower()
    pref_lower = [p.strip().lower() for p in preferred_locations if p.strip()]
    mode_ok = preferred_mode == "any" or not preferred_mode or preferred_mode == job_mode

    if job_mode == "remote" or "remote" in loc_lower:
        return {"status": "remote", "score": 100.0 if mode_ok else 85.0, "message": f"Remote role ({job_location})."}
    if not pref_lower:
        return {"status": "no_preference", "score": 80.0, "message": f"Location: {job_location} ({job_mode})."}
    if any(p in loc_lower or loc_lower in p for p in pref_lower):
        score = 100.0 if mode_ok else 85.0
        return {"status": "match", "score": score, "message": f"Matches preferred location ({job_location}, {job_mode})."}
    if willing_to_relocate:
        return {
            "status": "relocation",
            "score": 70.0 if mode_ok else 60.0,
            "message": f"{job_location} requires relocation (marked willing to relocate).",
        }
    return {
        "status": "mismatch",
        "score": 25.0,
        "message": f"{job_location} is outside your preferred locations ({', '.join(preferred_locations)}).",
    }


def score_job_match(job: Any, profile: Any, verified_skills: list[dict[str, Any]]) -> dict[str, Any]:
    verified_map = {s["skill"]: s for s in verified_skills}

    strong_matches: list[dict[str, Any]] = []
    partial_matches: list[dict[str, Any]] = []
    missing_mandatory: list[str] = []
    missing_preferred: list[str] = []
    not_assessed: list[str] = []

    mandatory_scores: list[float] = []
    for raw_skill in job.mandatory_skills or []:
        skill = canonical_skill(raw_skill)
        entry = verified_map.get(skill)
        if not entry:
            missing_mandatory.append(skill)
            mandatory_scores.append(0.0)
        elif entry["verified_score"] is None:
            not_assessed.append(skill)
            sc, _ = effective_skill_score(skill, verified_map)
            partial_matches.append({"skill": skill, "score": sc, "target": 65})
            mandatory_scores.append(sc)
        else:
            sc = float(entry["verified_score"])
            mandatory_scores.append(sc)
            if sc >= 70:
                strong_matches.append({"skill": skill, "score": sc})
            else:
                partial_matches.append({"skill": skill, "score": sc, "target": 70})

    preferred_scores: list[float] = []
    for raw_skill in job.preferred_skills or []:
        skill = canonical_skill(raw_skill)
        entry = verified_map.get(skill)
        if not entry:
            missing_preferred.append(skill)
            preferred_scores.append(0.0)
        elif entry["verified_score"] is None:
            not_assessed.append(skill)
            sc, _ = effective_skill_score(skill, verified_map)
            preferred_scores.append(sc)
        else:
            sc = float(entry["verified_score"])
            preferred_scores.append(sc)
            if sc >= 70:
                strong_matches.append({"skill": skill, "score": sc})
            else:
                partial_matches.append({"skill": skill, "score": sc, "target": 70})

    mandatory_component = sum(mandatory_scores) / len(mandatory_scores) if mandatory_scores else 100.0
    preferred_component = sum(preferred_scores) / len(preferred_scores) if preferred_scores else 100.0

    exp_req = float(job.experience_min_years or 0.0)
    exp_user = float(profile.experience_years or 0.0)
    if exp_req <= 0 or exp_user >= exp_req:
        exp_component = 100.0
        qual_gaps: list[str] = []
    else:
        exp_component = max(30.0, round(100.0 * (exp_user / exp_req), 1))
        qual_gaps = [f"Requires {exp_req:g}+ yrs experience (profile has {exp_user:g} yrs)."]

    edu_component = 100.0 if (profile.education or "").strip() else 65.0
    if not (profile.education or "").strip() and job.education:
        qual_gaps.append(f"Education not specified (job lists: {job.education}).")

    loc_fit = evaluate_location_fit(
        job.location,
        job.work_mode,
        profile.preferred_locations or [],
        bool(profile.willing_to_relocate),
        profile.work_mode or "any",
    )
    sal_fit = evaluate_salary_fit(
        job.salary_min_lpa,
        job.salary_max_lpa,
        profile.expected_salary_lpa,
        profile.min_salary_lpa,
    )

    components = {
        "mandatory": round(mandatory_component, 1),
        "preferred": round(preferred_component, 1),
        "experience": round(exp_component, 1),
        "education": round(edu_component, 1),
        "location": round(loc_fit["score"], 1),
        "salary": round(sal_fit["score"], 1),
    }
    total_score = round(sum(components[k] * JOB_WEIGHTS[k] for k in JOB_WEIGHTS), 1)

    explanation = (
        f"Compatibility {total_score}% (Mandatory skills {components['mandatory']}%, "
        f"Preferred {components['preferred']}%, Location {components['location']}%, Salary {components['salary']}%). "
        "This reflects skill & preference alignment, not hiring probability."
    )
    return {
        "score": total_score,
        "components": components,
        "weights": JOB_WEIGHTS,
        "strong_matches": strong_matches,
        "partial_matches": partial_matches,
        "missing_mandatory": missing_mandatory,
        "missing_preferred": missing_preferred,
        "not_assessed": sorted(set(not_assessed)),
        "qualification_gaps": qual_gaps,
        "salary_fit": {"status": sal_fit["status"], "message": sal_fit["message"]},
        "location_fit": {"status": loc_fit["status"], "message": loc_fit["message"]},
        "explanation": explanation,
    }


_KNOWN_LOCATIONS = [
    "Bengaluru",
    "Bangalore",
    "Chennai",
    "Hyderabad",
    "Pune",
    "Mumbai",
    "Delhi",
    "Noida",
    "Gurugram",
    "Coimbatore",
    "Kolkata",
    "Remote",
]


def extract_requirements_from_text(description: str) -> dict[str, Any]:
    """Deterministically extract skills, experience, education, location, work mode, and explicit salary."""
    text = description.strip()
    lower = text.lower()
    known_skills = [s["name"] for s in load_skills() if s.get("status") != "outdated"]

    mandatory_section = ""
    preferred_section = ""
    m_mand = re.search(r"mandatory\s*:([^.\n]+)", text, flags=re.IGNORECASE)
    if m_mand:
        mandatory_section = m_mand.group(1)
    m_pref = re.search(r"(?:preferred|good to have|nice to have)\s*:([^.\n]+)", text, flags=re.IGNORECASE)
    if m_pref:
        preferred_section = m_pref.group(1)

    def _find_skills(chunk: str) -> list[str]:
        found: list[str] = []
        c_low = chunk.lower()
        for sk in known_skills:
            if re.search(rf"(?<!\w){re.escape(sk.lower())}(?!\w)", c_low):
                found.append(sk)
        return found

    mandatory = _find_skills(mandatory_section) if mandatory_section else []
    preferred = _find_skills(preferred_section) if preferred_section else []

    if not mandatory and not preferred:
        all_found = _find_skills(lower)
        split_at = max(1, (len(all_found) + 1) // 2) if all_found else 0
        mandatory = all_found[:split_at]
        preferred = all_found[split_at:]
    else:
        preferred = [s for s in preferred if s not in mandatory]

    exp_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)", lower)
    exp_years = float(exp_match.group(1)) if exp_match else 0.0

    edu_match = re.search(
        r"(b\.?tech|b\.?e\.?|m\.?tech|mca|b\.?sc|m\.?sc|bachelor'?s|master'?s|any graduate)[^.\n]*",
        text,
        flags=re.IGNORECASE,
    )
    education = edu_match.group(0).strip() if edu_match else ""

    work_mode: str | None = None
    for mode in ("hybrid", "remote", "onsite", "on-site"):
        if re.search(rf"\b{mode}\b", lower):
            work_mode = "onsite" if mode == "on-site" else mode
            break

    location = ""
    loc_label = re.search(r"location\s*:\s*([A-Za-z ,/]+)", text, flags=re.IGNORECASE)
    if loc_label:
        location = loc_label.group(1).strip().rstrip(".")[:100]
    else:
        for city in _KNOWN_LOCATIONS:
            if re.search(rf"\b{re.escape(city.lower())}\b", lower):
                location = city
                break

    salary_min_lpa: float | None = None
    salary_max_lpa: float | None = None
    sal_range = re.search(
        r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*(?:-|to|–)\s*(\d+(?:\.\d+)?)\s*lpa\b",
        lower,
    )
    if sal_range:
        lo, hi = float(sal_range.group(1)), float(sal_range.group(2))
        salary_min_lpa, salary_max_lpa = min(lo, hi), max(lo, hi)
    else:
        sal_single = re.search(r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d+)?)\s*lpa\b", lower)
        if sal_single:
            val = float(sal_single.group(1))
            salary_min_lpa = val
            salary_max_lpa = val

    return {
        "mandatory_skills": mandatory,
        "preferred_skills": preferred,
        "experience_years": exp_years,
        "education": education,
        "location": location,
        "work_mode": work_mode,
        "salary_min_lpa": salary_min_lpa,
        "salary_max_lpa": salary_max_lpa,
    }


def compute_profile_completeness(user: Any, profile: Any) -> int:
    checks = [
        bool((user.full_name or "").strip()),
        bool((profile.education or "").strip()),
        bool((profile.college or "").strip()),
        profile.graduation_year is not None,
        bool(profile.technical_skills),
        bool(profile.soft_skills),
        bool(profile.projects),
        bool(profile.career_interests),
        bool((profile.current_location or "").strip()),
        bool(profile.preferred_locations),
        profile.expected_salary_lpa is not None,
    ]
    return int(round(100 * sum(1 for c in checks if c) / len(checks)))
