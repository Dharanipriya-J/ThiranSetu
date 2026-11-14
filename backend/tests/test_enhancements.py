"""Tests for refresh rotation, CSRF, enhanced JD extraction, job feed sync, and multilingual courses."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.services.job_ingestion import PermittedJsonFeedProvider


def test_refresh_token_rotation_csrf_and_reuse_detection(client: TestClient) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": "refresh@example.com", "password": "Password1", "full_name": "Refresh User"},
    )
    assert reg.status_code == 201
    csrf = reg.cookies.get("ts_csrf")
    refresh_1 = reg.cookies.get("ts_refresh")
    assert csrf and refresh_1

    # Missing CSRF header must be rejected when CSRF cookie is present
    bad_csrf = client.post("/api/auth/refresh")
    assert bad_csrf.status_code == 403

    # Valid refresh rotates the refresh token
    ok = client.post("/api/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert ok.status_code == 200
    assert ok.json()["access_token"]
    refresh_2 = ok.cookies.get("ts_refresh")
    assert refresh_2 and refresh_2 != refresh_1

    # Replaying old refresh token triggers reuse detection & revokes session
    client.cookies.set("ts_refresh", refresh_1)
    replay = client.post("/api/auth/refresh", headers={"X-CSRF-Token": ok.cookies.get("ts_csrf", csrf)})
    assert replay.status_code == 401


def test_enhanced_jd_extraction_edited_skills_and_job_added_trace(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    jd = (
        "Location: Bengaluru. Hybrid role requiring 2+ years experience and B.Tech CSE. "
        "Salary: 6 - 9 LPA. Mandatory: Python, SQL. Preferred: Docker."
    )
    ext = client.post("/api/jobs/extract", headers=auth_headers, json={"description": jd})
    assert ext.status_code == 200
    ext_data = ext.json()
    assert ext_data["location"] == "Bengaluru"
    assert ext_data["work_mode"] == "hybrid"
    assert ext_data["salary_min_lpa"] == 6.0
    assert ext_data["salary_max_lpa"] == 9.0
    assert "Python" in ext_data["mandatory_skills"]

    # JD without salary must NOT invent salary
    no_sal = client.post(
        "/api/jobs/extract",
        headers=auth_headers,
        json={"description": "Remote Python developer role with FastAPI and SQL experience."},
    )
    assert no_sal.status_code == 200
    assert no_sal.json()["salary_min_lpa"] is None
    assert no_sal.json()["salary_max_lpa"] is None
    assert no_sal.json()["work_mode"] == "remote"

    # User edits extracted mandatory skills before saving
    created = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "Zoho Corp",
            "title": "Backend Engineer",
            "description": jd,
            "mandatory_skills": ["Python", "FastAPI"],
            "preferred_skills": ["Docker"],
            "location": "Chennai",
            "work_mode": "hybrid",
            "salary_min_lpa": 6.0,
            "salary_max_lpa": 9.0,
            "experience_min_years": 2.0,
            "education": "B.Tech CSE",
            "posted_date": "2026-11-10",
            "apply_url": "https://careers.zohocorp.com/apply/1",
            "source": "Employer Official Career Page",
        },
    )
    assert created.status_code == 201
    job_detail = created.json()
    assert job_detail["mandatory_skills"] == ["Python", "FastAPI"]
    assert job_detail["verification_status"] == "Pending Verification"
    assert job_detail["last_verified_date"] is None

    # Verify job_added orchestrator run executed Vacancy Requirement Sync
    latest = client.get("/api/agents/latest", headers=auth_headers).json()
    assert latest["trigger"] == "job_added"
    agent_names = [t["agent"] for t in latest["trace"]]
    assert "Vacancy Requirement Sync" in agent_names
    assert all("order" in t and "input_summary" in t and "output_summary" in t for t in latest["trace"])


def test_job_feed_sync_unconfigured_and_https_guard(client: TestClient, auth_headers: dict[str, str]) -> None:
    sync_res = client.post("/api/jobs/sync", headers=auth_headers)
    assert sync_res.status_code == 200
    assert sync_res.json()["status"] == "unconfigured"
    assert sync_res.json()["added"] == 0

    import asyncio

    bad_provider = PermittedJsonFeedProvider("http://insecure.example.com/jobs.json")
    try:
        asyncio.run(bad_provider.fetch())
        raise AssertionError("Expected ValueError for non-HTTPS feed URL")
    except ValueError as exc:
        assert "https://" in str(exc)


def test_multilingual_courses_and_availability_note(client: TestClient, auth_headers: dict[str, str]) -> None:
    for lang in ("en", "ta", "hi", "te", "kn", "ml", "bn", "mr"):
        res = client.get(f"/api/courses?language={lang}", headers=auth_headers)
        assert res.status_code == 200
        assert res.json()["total"] >= 1

    # Query a language + unrelated skill that has no primary teaching match
    empty = client.get("/api/courses?language=ta&skill=Cybersecurity", headers=auth_headers)
    assert empty.status_code == 200
    assert empty.json()["total"] == 0
    assert empty.json()["availability_note"] is not None


def test_strict_csrf_on_missing_cookie_and_no_youtube_search_urls(client: TestClient) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": "csrf2@example.com", "password": "Password1", "full_name": "CSRF User"},
    )
    assert reg.status_code == 201
    # Remove ts_csrf cookie while keeping ts_refresh cookie — refresh must reject with 403
    client.cookies.delete("ts_csrf")
    res = client.post("/api/auth/refresh", headers={"X-CSRF-Token": "forged"})
    assert res.status_code == 403

    from app.data.catalog import load_courses

    for c in load_courses():
        if c.get("url"):
            assert "youtube.com/results" not in c["url"]


def test_manual_job_is_pending_verification_and_excluded_from_verified_top_jobs(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    created = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "Pending Corp",
            "title": "QA Analyst",
            "description": "Location: Chennai. Hybrid role. Mandatory: Python, SQL. Preferred: Excel.",
            "location": "Chennai",
            "work_mode": "hybrid",
            "experience_min_years": 0.0,
            "education": "B.Tech",
            "posted_date": "2026-11-10",
            "apply_url": "https://pending.example.com/apply",
            "source": "Manual Submission",
        },
    )
    assert created.status_code == 201
    assert created.json()["verification_status"] == "Pending Verification"

    latest = client.get("/api/agents/latest", headers=auth_headers).json()
    assert all(j["company"] != "Pending Corp" for j in latest["top_jobs"])
    assert all(j["verification_status"] == "Verified" for j in latest["top_jobs"])


def test_complete_user_journey_with_mentor_language_and_refresh_logout(client: TestClient) -> None:
    # 1. Registration & Login
    reg = client.post(
        "/api/auth/register",
        json={"email": "journey@example.com", "password": "Password1", "full_name": "Journey Student"},
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": "journey@example.com", "password": "Password1"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    csrf = login.cookies.get("ts_csrf", "")
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Profile creation + Language switching (app_language=ta, learning_language=ta)
    prof = client.put(
        "/api/profile",
        headers=headers,
        json={
            "education": "B.Tech CSE",
            "technical_skills": [{"name": "Python", "self_level": "intermediate"}],
            "career_interests": ["data_analyst"],
            "target_role": "data_analyst",
            "preferred_locations": ["Chennai"],
            "work_mode": "hybrid",
            "expected_salary_lpa": 7.0,
            "min_salary_lpa": 4.5,
            "learning_language": "ta",
            "app_language": "ta",
        },
    )
    assert prof.status_code == 200
    assert prof.json()["app_language"] == "ta"
    assert prof.json()["learning_language"] == "ta"

    # 3. Skill assessment
    start = client.post("/api/assessments/start", headers=headers, json={"skill": "Python", "level": "beginner"})
    assert start.status_code == 201
    session = start.json()
    answers = {q["id"]: "A" for q in session["questions"]}
    sub = client.post(f"/api/assessments/{session['attempt_id']}/submit", headers=headers, json={"answers": answers})
    assert sub.status_code == 200
    assert sub.json()["verified_score"] is not None

    # 4. Career recommendations & 5. Job matching (no synthetic vacancies leaked)
    careers = client.get("/api/careers", headers=headers)
    assert careers.status_code == 200
    assert len(careers.json()) >= 1
    jobs = client.get("/api/jobs", headers=headers)
    assert jobs.status_code == 200
    assert jobs.json()["total"] == 0
    assert all(not j.get("is_demo") for j in jobs.json()["items"])

    # 6. Course discovery & 7. Learning roadmap
    courses = client.get("/api/courses?language=ta", headers=headers)
    assert courses.status_code == 200
    assert courses.json()["total"] >= 1
    roadmap = client.get("/api/roadmap", headers=headers)
    assert roadmap.status_code == 200
    assert len(roadmap.json()["steps"]) >= 1

    # 8. AI Career Mentor
    mentor = client.post(
        "/api/mentor/chat",
        headers=headers,
        json={"message": "Which career and next skill should I focus on?", "language": "en"},
    )
    assert mentor.status_code == 200
    assert len(mentor.json()["reply"]) > 10

    # 9. Token refresh + 10. Logout
    refreshed = client.post("/api/auth/refresh", headers={"X-CSRF-Token": csrf})
    assert refreshed.status_code == 200
    new_token = refreshed.json()["access_token"]
    new_csrf = refreshed.cookies.get("ts_csrf", csrf)
    out = client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {new_token}", "X-CSRF-Token": new_csrf},
    )
    assert out.status_code == 204
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_token}"}).status_code == 401


def test_redis_rate_limit_production_fail_closed_and_dev_fallback(
    client: TestClient,
    monkeypatch,
) -> None:
    from app.core import config

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    monkeypatch.setenv("ENVIRONMENT", "development")
    config.get_settings.cache_clear()
    # Dev mode falls back to in-memory limiter (returns 401 for bad creds, not 503)
    dev_res = client.post("/api/auth/login", json={"email": "x@example.com", "password": "Password1"})
    assert dev_res.status_code == 401

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("JWT_SECRET", "a" * 40)
    config.get_settings.cache_clear()
    # Production mode fails closed (503) when Redis is unreachable on sensitive auth endpoints
    prod_res = client.post("/api/auth/login", json={"email": "x@example.com", "password": "Password1"})
    assert prod_res.status_code == 503
    config.get_settings.cache_clear()


def test_synthetic_vacancies_excluded_everywhere(client: TestClient, auth_headers: dict[str, str]) -> None:
    from sqlalchemy import select

    from app.db.models import Job
    from app.db.session import SessionLocal

    with SessionLocal() as db:
        demo_jobs = list(db.scalars(select(Job).where(Job.is_demo.is_(True))).all())
        assert len(demo_jobs) == 10
        assert all(j.verification_status != "Verified" for j in demo_jobs)
        demo_id = demo_jobs[0].id

    assert client.get("/api/jobs", headers=auth_headers).json()["total"] == 0
    assert client.get(f"/api/jobs/{demo_id}", headers=auth_headers).status_code == 404
    market = client.get("/api/market", headers=auth_headers).json()
    assert market["data_source"]["is_demo"] is False
    assert market["data_source"]["vacancies_analyzed"] == 0
    dash = client.get("/api/dashboard", headers=auth_headers).json()
    assert dash["top_jobs"] == []


def test_unverified_courses_excluded_from_recommendations_and_equivalents(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Verified-only filter excludes the 9 unverified YouTube syllabus references without direct URLs
    all_courses = client.get("/api/courses?page_size=50", headers=auth_headers).json()
    verified_courses = client.get("/api/courses?verified_only=true&page_size=50", headers=auth_headers).json()
    assert all_courses["total"] == 23
    assert verified_courses["total"] == 14
    for c in verified_courses["items"]:
        assert c["is_verified"] is True
        assert c["url"] and c["url"].startswith("https://")
        assert "Pending Verification" not in c.get("verification", "")

    # Verified recommendations and roadmap steps must never include unverified courses
    rec = client.get("/api/courses/recommended", headers=auth_headers).json()
    for grp in rec:
        for c in grp["courses"]:
            assert c["url"] and c["url"].startswith("https://")
    roadmap = client.get("/api/roadmap", headers=auth_headers).json()
    for st in roadmap["steps"]:
        if st["course"]:
            assert st["course"]["url"] and st["course"]["url"].startswith("https://")

    # Multilingual equivalents exclude unverified courses and distinguish potential skill overlap
    equiv = client.get("/api/courses/nptel-py-ds/equivalents?language=ta", headers=auth_headers).json()
    for item in equiv["equivalents"]:
        assert item["course"]["url"] and item["course"]["url"].startswith("https://")
        assert item["equivalence_status"] in {"syllabus_verified", "potential_skill_overlap"}


def test_changing_company_mandatory_skills_updates_gaps_and_courses(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # 1. Company A requires Docker
    res1 = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "CloudScale Systems",
            "title": "DevOps Intern",
            "description": "Location: Bengaluru. Hybrid. Mandatory: Docker. Preferred: Linux.",
            "mandatory_skills": ["Docker"],
            "preferred_skills": ["Linux"],
            "location": "Bengaluru",
            "work_mode": "hybrid",
            "experience_min_years": 0.0,
            "education": "B.Tech",
            "posted_date": "2026-11-11",
            "apply_url": "https://cloudscale.example.com/jobs/1",
            "source": "Company Career Page",
        },
    )
    assert res1.status_code == 201
    intel1 = client.get("/api/intelligence", headers=auth_headers).json()
    assert "Docker" in intel1["vacancy_gaps"]["mandatory_missing"]
    rec1 = client.get("/api/courses/recommended", headers=auth_headers).json()
    assert any(grp["skill"] == "Docker" for grp in rec1)

    # 2. Company B changes mandatory skill to FastAPI
    res2 = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "APIWorks India",
            "title": "Backend Intern",
            "description": "Location: Chennai. Remote. Mandatory: FastAPI. Preferred: SQL.",
            "mandatory_skills": ["FastAPI"],
            "preferred_skills": ["SQL"],
            "location": "Chennai",
            "work_mode": "remote",
            "experience_min_years": 0.0,
            "education": "B.Tech",
            "posted_date": "2026-11-12",
            "apply_url": "https://apiworks.example.com/jobs/2",
            "source": "Company Career Page",
        },
    )
    assert res2.status_code == 201
    intel2 = client.get("/api/intelligence", headers=auth_headers).json()
    assert "FastAPI" in intel2["vacancy_gaps"]["mandatory_missing"]
    rec2 = client.get("/api/courses/recommended", headers=auth_headers).json()
    assert any(grp["skill"] == "FastAPI" for grp in rec2)
