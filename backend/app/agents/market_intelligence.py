"""Agent 3 — Market Intelligence Agent: analyses platform vacancies and industry trends."""

from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
from typing import Any

from app.agents.job_matching import is_verified_real_job
from app.agents.state import OrchestratorState, run_traced
from app.data.catalog import canonical_skill, load_roles, load_skills


def market_intelligence_node(state: OrchestratorState) -> dict[str, Any]:
    def _run(s: OrchestratorState) -> dict[str, Any]:
        raw_jobs = s.get("jobs") or []
        jobs = [j for j in raw_jobs if not j.get("is_demo") and is_verified_real_job(SimpleNamespace(**j))]
        total_jobs = len(jobs)
        mandatory_counts: Counter[str] = Counter()
        preferred_counts: Counter[str] = Counter()
        total_counts: Counter[str] = Counter()
        role_counts: Counter[str] = Counter()

        latest_date = ""
        for job in jobs:
            posted = str(job.get("posted_date") or "")
            if posted > latest_date:
                latest_date = posted
            if job.get("role_id"):
                role_counts[job["role_id"]] += 1

            seen_in_job: set[str] = set()
            for raw in job.get("mandatory_skills") or []:
                sk = canonical_skill(raw)
                mandatory_counts[sk] += 1
                if sk not in seen_in_job:
                    total_counts[sk] += 1
                    seen_in_job.add(sk)
            for raw in job.get("preferred_skills") or []:
                sk = canonical_skill(raw)
                preferred_counts[sk] += 1
                if sk not in seen_in_job:
                    total_counts[sk] += 1
                    seen_in_job.add(sk)

        top_skills = []
        for sk, cnt in total_counts.most_common(12):
            share = round(100.0 * cnt / total_jobs, 1) if total_jobs else 0.0
            top_skills.append(
                {
                    "skill": sk,
                    "demand_count": cnt,
                    "share_percent": share,
                    "mandatory_count": mandatory_counts[sk],
                    "preferred_count": preferred_counts[sk],
                }
            )

        roles_by_id = {r["id"]: r["title"] for r in load_roles()}
        role_demand = [
            {"role_id": rid, "title": roles_by_id.get(rid, rid), "vacancies": cnt}
            for rid, cnt in role_counts.most_common()
        ]

        skills_tax = load_skills()
        emerging = [{"skill": sk["name"], "reason": sk["reason"], "evidence": sk["evidence"]} for sk in skills_tax if sk.get("status") == "emerging"]
        stable = [sk["name"] for sk in skills_tax if sk.get("status") == "stable"]
        declining = [
            {"skill": sk["name"], "reason": sk.get("issue", sk.get("reason", "")), "evidence": sk.get("evidence", "")}
            for sk in skills_tax
            if sk.get("status") in {"declining", "outdated"}
        ]

        market = {
            "data_source": {
                "label": "Verified Platform Vacancies & Skill Taxonomy" if total_jobs > 0 else "Curated Skill Taxonomy (0 Verified Live Vacancies)",
                "is_demo": False,
                "vacancies_analyzed": total_jobs,
                "as_of": latest_date or "2026-11-14",
                "scope": "India (Verified Platform Vacancies & Taxonomy)",
            },
            "top_skills": top_skills,
            "role_demand": role_demand,
            "emerging": emerging,
            "stable": stable,
            "declining": declining,
            "notes": [
                "Synthetic demonstration vacancies are strictly excluded from market statistics.",
                "Counts are computed exclusively from verified, non-synthetic vacancies in ThiranSetu.",
            ],
        }
        top_three = ", ".join(item["skill"] for item in top_skills[:3]) or "none"
        return {
            "market": market,
            "_trace_summary": f"Analysed {total_jobs} vacancies; top demanded skills: {top_three}.",
            "_trace_decisions": [f"Top skill share: {top_skills[0]['skill']} ({top_skills[0]['share_percent']}%)" if top_skills else "No vacancies"],
        }

    return run_traced("Market Intelligence Agent", state, _run)
