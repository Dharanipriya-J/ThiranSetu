"""Shared LangGraph state contract passed across the 7 specialized ThiranSetu agents."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypedDict


class OrchestratorState(TypedDict, total=False):
    user_id: int
    trigger: str
    llm_mode: str
    profile: dict[str, Any]
    verified_skills: list[dict[str, Any]]
    assessment_history: list[dict[str, Any]]
    jobs: list[dict[str, Any]]
    vacancy_requirements: dict[str, Any]
    skill_intelligence: dict[str, Any]
    market: dict[str, Any]
    careers: list[dict[str, Any]]
    top_jobs: list[dict[str, Any]]
    recommended_courses: list[dict[str, Any]]
    roadmap: dict[str, Any]
    mentor_brief: str
    needs_targeted_practice: bool
    trace: list[dict[str, Any]]


def run_traced(
    agent_name: str,
    state: OrchestratorState,
    fn: Callable[[OrchestratorState], dict[str, Any]],
) -> dict[str, Any]:
    """Execute an agent node, capturing order, inputs, decisions, and outputs into the shared trace."""
    t0 = time.perf_counter()
    trace = list(state.get("trace") or [])
    order = len(trace) + 1
    default_input = (
        f"trigger={state.get('trigger', 'manual')}, "
        f"skills={len(state.get('verified_skills') or [])}, "
        f"jobs={len(state.get('jobs') or [])}"
    )
    try:
        update = fn(state)
        ms = round((time.perf_counter() - t0) * 1000, 2)
        summary = update.pop("_trace_summary", f"{agent_name} completed")
        decisions = update.pop("_trace_decisions", [])
        task_performed = update.pop("_trace_task", summary)
        input_summary = update.pop("_trace_input", default_input)
        trace.append(
            {
                "order": order,
                "agent": agent_name,
                "status": "ok",
                "duration_ms": ms,
                "task_performed": task_performed,
                "input_summary": input_summary,
                "output_summary": summary,
                "summary": summary,
                "decisions": decisions,
            }
        )
        update["trace"] = trace
        return update
    except Exception as exc:  # pragma: no cover - defensive guard
        ms = round((time.perf_counter() - t0) * 1000, 2)
        trace.append(
            {
                "order": order,
                "agent": agent_name,
                "status": "error",
                "duration_ms": ms,
                "task_performed": f"{agent_name} execution",
                "input_summary": default_input,
                "output_summary": str(exc),
                "summary": str(exc),
                "decisions": [],
            }
        )
        return {"trace": trace}
