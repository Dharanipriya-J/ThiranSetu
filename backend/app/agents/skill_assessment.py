"""Agent 1 — Skill Assessment Agent: selects questions, evaluates answers, and diagnoses topics."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.agents.state import OrchestratorState, run_traced
from app.data.catalog import canonical_skill, load_questions

_LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
_DIFFICULTY_FACTOR = {"beginner": 0.90, "intermediate": 1.00, "advanced": 1.05}


def available_assessments() -> list[dict[str, Any]]:
    by_skill: dict[str, dict[str, Any]] = {}
    for q in load_questions():
        sk = q["skill"]
        entry = by_skill.setdefault(sk, {"skill": sk, "levels": set(), "question_count": 0})
        entry["levels"].add(q["level"])
        entry["question_count"] += 1
    out: list[dict[str, Any]] = []
    for entry in sorted(by_skill.values(), key=lambda x: x["skill"]):
        levels = sorted(entry["levels"], key=lambda lv: _LEVEL_ORDER.get(lv, 9))
        out.append({"skill": entry["skill"], "levels": levels, "question_count": entry["question_count"]})
    return out


def select_questions(skill: str, level: str) -> list[dict[str, Any]]:
    canon = canonical_skill(skill)
    all_for_skill = [q for q in load_questions() if q["skill"].lower() == canon.lower()]
    if not all_for_skill:
        return []
    exact = [q for q in all_for_skill if q["level"] == level]
    if len(exact) >= 3:
        return exact[:5]
    # Include adjacent level questions if a level has fewer than 3 items
    extras = [q for q in all_for_skill if q["level"] != level]
    return (exact + extras)[:4]


def _normalize_answer(val: str | None) -> str:
    if val is None:
        return ""
    return " ".join(val.strip().replace('"', "'").split()).lower()


def evaluate_attempt(question_ids: list[str], answers: dict[str, str], level: str) -> dict[str, Any]:
    q_by_id = {q["id"]: q for q in load_questions()}
    selected = [q_by_id[qid] for qid in question_ids if qid in q_by_id]

    topic_totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    review: list[dict[str, Any]] = []
    correct_count = 0

    for q in selected:
        user_ans = answers.get(q["id"], "")
        is_correct = _normalize_answer(user_ans) == _normalize_answer(q["answer"])
        topic = q["topic"]
        topic_totals[topic][1] += 1
        if is_correct:
            correct_count += 1
            topic_totals[topic][0] += 1
        review.append(
            {
                "question_id": q["id"],
                "prompt": q["prompt"],
                "correct": is_correct,
                "your_answer": user_ans,
                "correct_answer": q["answer"],
                "explanation": q["explanation"],
            }
        )

    total = len(selected)
    raw_percent = round(100.0 * correct_count / total, 1) if total else 0.0
    factor = _DIFFICULTY_FACTOR.get(level, 1.0)
    adjusted_score = min(100.0, round(raw_percent * factor, 1))

    topic_breakdown: list[dict[str, Any]] = []
    strong_topics: list[str] = []
    weak_topics: list[str] = []
    for topic, (ok, tot) in topic_totals.items():
        pct = round(100.0 * ok / tot, 1) if tot else 0.0
        topic_breakdown.append({"topic": topic, "correct": ok, "total": tot, "percent": pct})
        if pct >= 70:
            strong_topics.append(topic)
        else:
            weak_topics.append(topic)

    recommendations: list[str] = []
    if weak_topics:
        recommendations.append(f"Review and practice: {', '.join(weak_topics)}.")
    if adjusted_score < 60:
        recommendations.append("Complete targeted foundational exercises and retake the assessment to update your score.")
    elif adjusted_score < 80:
        recommendations.append("Try the next difficulty tier or build a small project to push verified proficiency above 80%.")
    else:
        recommendations.append("Strong verified command; keep applying this skill in portfolio projects.")

    return {
        "raw_percent": raw_percent,
        "score": adjusted_score,
        "correct": correct_count,
        "total": total,
        "topic_breakdown": topic_breakdown,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "recommendations": recommendations,
        "review": review,
    }


def assessment_agent_node(state: OrchestratorState) -> dict[str, Any]:
    """Summarize verified vs unverified skills and flag whether targeted practice is needed."""

    def _run(s: OrchestratorState) -> dict[str, Any]:
        verified = s.get("verified_skills") or []
        assessed = [v for v in verified if v.get("verified_score") is not None]
        low = [v["skill"] for v in assessed if float(v["verified_score"]) < 60]
        unverified = [v["skill"] for v in verified if v.get("verified_score") is None]
        decisions = []
        if low:
            decisions.append(f"Low verified score (<60%) detected in: {', '.join(low)} -> flag targeted practice.")
        if unverified:
            decisions.append(f"Unverified self-reported skills: {', '.join(unverified)}.")
        return {
            "needs_targeted_practice": bool(low),
            "_trace_summary": f"Evaluated {len(assessed)} verified skills and {len(unverified)} unverified skills.",
            "_trace_decisions": decisions,
        }

    return run_traced("Skill Assessment Agent", state, _run)
