"""Agent 4 — Career Matching Agent: ranks career paths with transparent 6-component scoring."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.agents.job_matching import is_verified_real_job
from app.agents.state import OrchestratorState, run_traced
from app.data.catalog import load_roles
from app.services.scoring import (
    CAREER_WEIGHTS,
    effective_skill_score,
    evaluate_location_fit,
    evaluate_salary_fit,
)


def _label_for_score(score: float) -> str:
    if score >= 78:
        return "Highly Recommended"
    if score >= 60:
        return "Recommended"
    if score >= 42:
        return "Potential Career"
    return "Requires Skill Development"


def career_matching_node(state: OrchestratorState) -> dict[str, Any]:
    def _run(s: OrchestratorState) -> dict[str, Any]:
        profile = s.get("profile") or {}
        verified = s.get("verified_skills") or []
        verified_map = {item["skill"]: item for item in verified}
        jobs = [j for j in (s.get("jobs") or []) if not j.get("is_demo") and is_verified_real_job(SimpleNamespace(**j))]
        vacancy_reqs = s.get("vacancy_requirements") or {}
        synced_skills = set((vacancy_reqs.get("mandatory_skills") or []) + (vacancy_reqs.get("preferred_skills") or []))

        interests = set(profile.get("career_interests") or [])
        target_role = profile.get("target_role")
        pref_locs = profile.get("preferred_locations") or []
        willing_reloc = bool(profile.get("willing_to_relocate"))
        work_mode = profile.get("work_mode") or "any"
        exp_salary = profile.get("expected_salary_lpa")
        min_salary = profile.get("min_salary_lpa")
        exp_years = float(profile.get("experience_years") or 0.0)
        projects_count = len(profile.get("projects") or [])

        role_vacancies_map: dict[str, list[dict[str, Any]]] = {}
        for job in jobs:
            rid = job.get("role_id")
            if rid:
                role_vacancies_map.setdefault(rid, []).append(job)

        max_vacancies = max((len(v) for v in role_vacancies_map.values()), default=1)
        recommendations: list[dict[str, Any]] = []

        for role in load_roles():
            rid = role["id"]
            weighted_skill_sum = 0.0
            total_w = 0.0
            matching_skills: list[dict[str, Any]] = []
            improve_skills: list[dict[str, Any]] = []
            missing_skills: list[str] = []

            for req in role["skills"]:
                sk = req["skill"]
                w = float(req["weight"])
                total_w += w
                sc, is_ver = effective_skill_score(sk, verified_map)
                weighted_skill_sum += sc * w
                if sk not in verified_map:
                    missing_skills.append(sk)
                elif is_ver and sc >= 70:
                    matching_skills.append({"skill": sk, "score": sc})
                else:
                    improve_skills.append({"skill": sk, "score": sc, "target": 70})

            skill_match = round(weighted_skill_sum / total_w, 1) if total_w else 0.0
            if rid == target_role or rid in interests:
                interest_score = 100.0
            elif not interests and not target_role:
                interest_score = 50.0
            else:
                interest_score = 30.0

            role_jobs = role_vacancies_map.get(rid, [])
            vac_count = len(role_jobs)
            demand_score = round(40.0 + 60.0 * (vac_count / max_vacancies), 1) if vac_count else 35.0
            if synced_skills:
                role_skill_names = {req["skill"] for req in role["skills"]}
                overlap = len(role_skill_names & synced_skills)
                if overlap:
                    demand_score = min(100.0, round(demand_score + overlap * 8.0, 1))
            demand_level = "high" if vac_count >= 2 else ("medium" if vac_count == 1 else "low")

            # Salary range derived strictly from disclosed platform vacancies for this role
            disclosed_mins = [j["salary_min_lpa"] for j in role_jobs if j.get("salary_min_lpa") is not None]
            disclosed_maxs = [j["salary_max_lpa"] for j in role_jobs if j.get("salary_max_lpa") is not None]
            if disclosed_mins or disclosed_maxs:
                sal_min = min(disclosed_mins) if disclosed_mins else min(disclosed_maxs)
                sal_max = max(disclosed_maxs) if disclosed_maxs else max(disclosed_mins)
                salary_range = {
                    "min_lpa": sal_min,
                    "max_lpa": sal_max,
                    "source": f"Derived from {len(disclosed_mins or disclosed_maxs)} platform vacancy(ies)",
                }
                salary_score = float(evaluate_salary_fit(sal_min, sal_max, exp_salary, min_salary)["score"])
            else:
                salary_range = None
                salary_score = 55.0

            if role_jobs:
                loc_evals = [
                    evaluate_location_fit(j["location"], j["work_mode"], pref_locs, willing_reloc, work_mode)
                    for j in role_jobs
                ]
                best_loc = max(loc_evals, key=lambda x: x["score"])
                location_score = float(best_loc["score"])
                location_fit = best_loc["message"]
            else:
                location_score = 60.0
                location_fit = "No active vacancies for this role in the current feed."

            exp_score = min(100.0, round(55.0 + exp_years * 15.0 + min(projects_count, 3) * 10.0, 1))

            components = {
                "skill_match": skill_match,
                "interest": interest_score,
                "market_demand": demand_score,
                "location": round(location_score, 1),
                "salary": round(salary_score, 1),
                "experience": exp_score,
            }
            overall = round(sum(components[k] * CAREER_WEIGHTS[k] for k in CAREER_WEIGHTS), 1)
            learning_path = [s["skill"] for s in improve_skills] + missing_skills
            explanation = (
                f"Weighted score {overall}% (Skills {skill_match}%, Interest {interest_score}%, "
                f"Demand {demand_score}%, Location {components['location']}%, Salary {components['salary']}%). "
                "Compatibility measures alignment with role requirements, not employment probability."
            )

            recommendations.append(
                {
                    "role_id": rid,
                    "title": role["title"],
                    "score": overall,
                    "label": _label_for_score(overall),
                    "components": components,
                    "weights": CAREER_WEIGHTS,
                    "matching_skills": matching_skills,
                    "improve_skills": improve_skills,
                    "missing_skills": missing_skills,
                    "demand_level": demand_level,
                    "vacancies": vac_count,
                    "salary_range": salary_range,
                    "location_fit": location_fit,
                    "explanation": explanation,
                    "learning_path": learning_path,
                    "is_target": rid == target_role,
                }
            )

        recommendations.sort(key=lambda r: (-int(r["is_target"]), -r["score"], r["title"]))
        top = recommendations[0] if recommendations else None
        return {
            "careers": recommendations,
            "_trace_summary": (
                f"Ranked {len(recommendations)} careers; top match: {top['title']} ({top['score']}%)."
                if top
                else "No roles available."
            ),
            "_trace_decisions": [f"{r['title']}: {r['score']}% ({r['label']})" for r in recommendations[:3]],
        }

    return run_traced("Career Matching Agent", state, _run)
