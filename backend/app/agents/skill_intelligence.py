"""Agent 2 — Skill Intelligence Agent: identifies strong, weak, missing, emerging, declining, and outdated skills."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.agents.state import OrchestratorState, run_traced
from app.data.catalog import canonical_skill, load_roles, load_skills


def skill_intelligence_node(state: OrchestratorState) -> dict[str, Any]:
    def _run(s: OrchestratorState) -> dict[str, Any]:
        profile = s.get("profile") or {}
        verified = s.get("verified_skills") or []
        jobs = [j for j in (s.get("jobs") or []) if not j.get("is_demo")]
        vacancy_reqs = s.get("vacancy_requirements") or {}
        skill_catalog = {sk["name"].lower(): sk for sk in load_skills()}
        roles = load_roles()

        strong: list[dict[str, Any]] = []
        weak: list[dict[str, Any]] = []
        unverified: list[dict[str, Any]] = []
        outdated: list[dict[str, Any]] = []
        targeted_practice: list[str] = []

        known_names: set[str] = set()
        for item in verified:
            name = item["skill"]
            known_names.add(name)
            score = item.get("verified_score")
            meta = skill_catalog.get(name.lower())
            if meta and meta.get("status") == "outdated":
                outdated.append(
                    {
                        "skill": name,
                        "issue": meta.get("issue", "Outdated technology version."),
                        "recommendation": meta.get("recommendation", "Upgrade to modern equivalent."),
                        "evidence": meta.get("evidence", "Vendor EOL / market data."),
                        "source": meta.get("source", "Curated taxonomy"),
                    }
                )
            elif meta and meta.get("status") == "declining":
                outdated.append(
                    {
                        "skill": name,
                        "issue": meta.get("issue", "Declining demand in new projects."),
                        "recommendation": meta.get("recommendation", "Pair with modern alternatives."),
                        "evidence": meta.get("evidence", "Market vacancy trends."),
                        "source": meta.get("source", "Curated market analysis"),
                    }
                )

            if score is None:
                unverified.append({"skill": name, "self_reported_level": item.get("self_reported_level") or "beginner"})
            elif float(score) >= 70:
                strong.append({"skill": name, "score": score, "reason": f"Verified score {score}% across recent assessments."})
            else:
                weak_topics = item.get("weak_topics") or []
                reason = f"Verified score {score}% (<70% target)."
                if weak_topics:
                    reason += f" Weak topics: {', '.join(weak_topics)}."
                weak.append({"skill": name, "score": score, "reason": reason, "weak_topics": weak_topics})
                targeted_practice.append(f"Practice {name}" + (f" ({', '.join(weak_topics)})" if weak_topics else ""))

        # Missing skills weighted by target/interested roles and active job demand
        target_role_id = profile.get("target_role")
        interests = set(profile.get("career_interests") or [])
        relevant_roles = [r for r in roles if r["id"] == target_role_id or r["id"] in interests] or roles[:3]

        demand_counter: Counter[str] = Counter()
        for job in jobs:
            for sk in (job.get("mandatory_skills") or []) + (job.get("preferred_skills") or []):
                demand_counter[canonical_skill(sk)] += 1

        role_map_missing: dict[str, list[str]] = {}
        for role in relevant_roles:
            for req in role["skills"]:
                sk = req["skill"]
                if sk not in known_names:
                    role_map_missing.setdefault(sk, []).append(role["title"])

        mandatory_vacancy_missing: list[str] = []
        preferred_vacancy_missing: list[str] = []
        if vacancy_reqs:
            vac_label = f"{vacancy_reqs.get('company', 'Target Company')} — {vacancy_reqs.get('title', 'Vacancy')}"
            for raw_sk in vacancy_reqs.get("mandatory_skills") or []:
                sk = canonical_skill(raw_sk)
                demand_counter[sk] += 2
                if sk not in known_names:
                    mandatory_vacancy_missing.append(sk)
                    role_map_missing.setdefault(sk, []).append(f"{vac_label} [Mandatory]")
            for raw_sk in vacancy_reqs.get("preferred_skills") or []:
                sk = canonical_skill(raw_sk)
                demand_counter[sk] += 1
                if sk not in known_names:
                    preferred_vacancy_missing.append(sk)
                    role_map_missing.setdefault(sk, []).append(f"{vac_label} [Preferred]")

        mandatory_set = set(mandatory_vacancy_missing)
        missing = [
            {
                "skill": sk,
                "required_by": list(dict.fromkeys(titles)),
                "demand_count": demand_counter.get(sk, 0),
                "from_synced_vacancy": sk in mandatory_set or sk in preferred_vacancy_missing,
            }
            for sk, titles in sorted(
                role_map_missing.items(),
                key=lambda kv: (-int(kv[0] in mandatory_set), -demand_counter.get(kv[0], 0), -len(kv[1]), kv[0]),
            )
        ]

        emerging = [
            {"skill": sk["name"], "reason": sk["reason"], "evidence": sk["evidence"]}
            for sk in load_skills()
            if sk.get("status") == "emerging"
        ]
        declining = [
            {"skill": sk["name"], "reason": sk.get("issue", sk.get("reason", "")), "evidence": sk.get("evidence", "")}
            for sk in load_skills()
            if sk.get("status") in {"declining", "outdated"}
        ]

        intel = {
            "strong": strong,
            "weak": weak,
            "missing": missing,
            "emerging": emerging,
            "declining": declining,
            "outdated": outdated,
            "unverified": unverified,
            "targeted_practice": targeted_practice,
            "vacancy_gaps": {
                "company": vacancy_reqs.get("company"),
                "title": vacancy_reqs.get("title"),
                "mandatory_missing": mandatory_vacancy_missing,
                "preferred_missing": preferred_vacancy_missing,
            }
            if vacancy_reqs
            else None,
            "notice": (
                "Skills are evaluated against current industry requirements and technology versions — "
                "established foundational skills like SQL, Statistics, and Linux remain high-value."
            ),
        }
        decisions = [
            f"Strong: {len(strong)}, Weak: {len(weak)}, Missing for target/interests: {len(missing)}, Outdated alerts: {len(outdated)}."
        ]
        return {
            "skill_intelligence": intel,
            "_trace_summary": f"Classified {len(verified)} profile skills and identified {len(missing)} missing skills.",
            "_trace_decisions": decisions,
        }

    return run_traced("Skill Intelligence Agent", state, _run)
