"""Cached loaders for curated taxonomy, roles, question bank, courses, and demo vacancies."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def load_skills() -> list[dict[str, Any]]:
    return json.loads((_DATA_DIR / "skills.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def skill_map() -> dict[str, dict[str, Any]]:
    return {s["name"].lower(): s for s in load_skills()}


def canonical_skill(name: str) -> str:
    hit = skill_map().get(name.strip().lower())
    return hit["name"] if hit else name.strip()


@lru_cache(maxsize=1)
def load_roles() -> list[dict[str, Any]]:
    return json.loads((_DATA_DIR / "roles.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def role_map() -> dict[str, dict[str, Any]]:
    return {r["id"]: r for r in load_roles()}


@lru_cache(maxsize=1)
def load_questions() -> list[dict[str, Any]]:
    return json.loads((_DATA_DIR / "questions_bank.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_courses() -> list[dict[str, Any]]:
    return json.loads((_DATA_DIR / "courses_demo.json").read_text(encoding="utf-8"))


def is_verified_course(course: dict[str, Any]) -> bool:
    """Return True only when a course has a direct verified URL and complete language/provider metadata."""
    url = str(course.get("url") or "").strip()
    if not url.startswith("https://"):
        return False
    lowered_url = url.lower()
    if "youtube.com/results" in lowered_url or "google.com/search" in lowered_url:
        return False
    verification = str(course.get("verification") or "")
    if "pending verification" in verification.lower():
        return False
    has_meta = bool(
        str(course.get("title") or "").strip()
        and str(course.get("provider") or "").strip()
        and str(course.get("language") or "").strip()
        and isinstance(course.get("audio_languages"), list)
        and len(course.get("audio_languages") or []) > 0
        and isinstance(course.get("subtitle_languages"), list)
        and len(course.get("subtitle_languages") or []) > 0
    )
    return has_meta


def load_verified_courses() -> list[dict[str, Any]]:
    return [c for c in load_courses() if is_verified_course(c)]


@lru_cache(maxsize=1)
def load_demo_jobs() -> list[dict[str, Any]]:
    return json.loads((_DATA_DIR / "jobs_demo.json").read_text(encoding="utf-8"))
