"""Tests for careers, company job matching, salary fit, courses, roadmap, mentor, and E2E workflow."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.data.catalog import load_questions


def test_end_to_end_student_to_career_job_course_roadmap_reassessment(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # 1. Profile setup
    client.put(
        "/api/profile",
        headers=auth_headers,
        json={
            "education": "B.Tech IT",
            "technical_skills": [
                {"name": "Python", "self_level": "intermediate"},
                {"name": "SQL", "self_level": "intermediate"},
                {"name": "Excel", "self_level": "intermediate"},
            ],
            "career_interests": ["data_analyst"],
            "target_role": "data_analyst",
            "preferred_locations": ["Chennai"],
            "expected_salary_lpa": 5.0,
            "min_salary_lpa": 4.0,
            "learning_language": "ta",
        },
    )

    # 2. Assess Python & SQL
    q_ans = {q["id"]: q["answer"] for q in load_questions()}
    for sk in ["Python", "SQL"]:
        s = client.post("/api/assessments/start", headers=auth_headers, json={"skill": sk, "level": "intermediate"}).json()
        ans = {q["id"]: q_ans[q["id"]] for q in s["questions"]}
        res = client.post(f"/api/assessments/{s['attempt_id']}/submit", headers=auth_headers, json={"answers": ans})
        assert res.status_code == 200

    # 3. Market & Career rankings (synthetic vacancies must be excluded)
    market = client.get("/api/market", headers=auth_headers).json()
    assert market["data_source"]["is_demo"] is False
    assert market["data_source"]["vacancies_analyzed"] == 0

    careers = client.get("/api/careers", headers=auth_headers).json()
    assert careers[0]["role_id"] == "data_analyst"
    assert "skill_match" in careers[0]["components"]

    # 4. Job list excludes synthetic vacancies; genuine manual submission is Pending Verification
    jobs_page = client.get("/api/jobs?location=Chennai", headers=auth_headers).json()
    assert jobs_page["total"] == 0

    created = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "Acme Analytics",
            "title": "Junior Data Analyst",
            "description": (
                "Location: Chennai. Hybrid role. Mandatory: Python, SQL, Power BI. "
                "Salary: 4 - 6 LPA. 0+ years experience."
            ),
            "location": "Chennai",
            "work_mode": "hybrid",
            "salary_min_lpa": 4.0,
            "salary_max_lpa": 6.0,
            "experience_min_years": 0.0,
            "education": "B.Tech",
            "posted_date": "2026-11-10",
            "apply_url": "https://acme.example.com/careers/1",
            "source": "Company Career Page",
        },
    ).json()
    assert created["verification_status"] == "Pending Verification"

    detail = client.get(f"/api/jobs/{created['id']}", headers=auth_headers).json()
    assert "Power BI" in detail["match"]["missing_mandatory"]
    assert detail["match"]["salary_fit"]["status"] == "meets"
    assert detail["recommended_courses"]

    # 5. Course filtering & multilingual equivalence
    courses = client.get("/api/courses?skill=Python&language=ta", headers=auth_headers).json()
    assert courses["total"] >= 1
    equiv = client.get("/api/courses/nptel-py-ds/equivalents?language=ta", headers=auth_headers).json()
    assert len(equiv["equivalents"]) >= 1
    assert equiv["equivalents"][0]["overlap_percent"] > 0

    # 6. Roadmap step completion + reassessment flag
    roadmap = client.get("/api/roadmap", headers=auth_headers).json()
    assert len(roadmap["steps"]) >= 1
    first_step = roadmap["steps"][0]
    updated_rm = client.patch(
        f"/api/roadmap/steps/{first_step['id']}",
        headers=auth_headers,
        json={"status": "completed"},
    ).json()
    assert updated_rm["progress_percent"] > 0
    assert updated_rm["steps"][0]["reassessment_required"] is True

    # 7. Target career change recalculates roadmap
    new_rm = client.put("/api/careers/target", headers=auth_headers, json={"role_id": "full_stack_developer"}).json()
    assert new_rm["target_role"]["id"] == "full_stack_developer"

    # 8. Contextual AI Mentor in deterministic mode
    mentor = client.post(
        "/api/mentor/chat",
        headers=auth_headers,
        json={"message": "What skills am I missing and which course should I take first?", "language": "en"},
    )
    assert mentor.status_code == 200
    assert mentor.json()["mode"] == "deterministic"
    assert len(mentor.json()["reply"]) > 20


def test_job_requirement_extraction_creation_and_application_tracker(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    desc = (
        "Mandatory: Python, SQL, FastAPI. Preferred: Docker, Cloud Computing. "
        "Bachelor's in CS. 1+ years experience building REST APIs."
    )
    extracted = client.post("/api/jobs/extract", headers=auth_headers, json={"description": desc}).json()
    assert set(extracted["mandatory_skills"]) >= {"Python", "SQL", "FastAPI"}
    assert "Docker" in extracted["preferred_skills"]

    # Reject non-https apply_url
    bad_job = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "Acme Tech",
            "title": "Python Engineer",
            "description": desc,
            "location": "Chennai",
            "work_mode": "hybrid",
            "posted_date": "2026-11-14",
            "apply_url": "http://insecure.example.com/apply",
            "source": "Manual entry",
        },
    )
    assert bad_job.status_code == 422

    created = client.post(
        "/api/jobs",
        headers=auth_headers,
        json={
            "company": "Acme Tech",
            "title": "Python Engineer",
            "description": desc,
            "location": "Chennai",
            "work_mode": "hybrid",
            "salary_min_lpa": 5.0,
            "salary_max_lpa": 8.0,
            "experience_min_years": 1,
            "education": "B.Tech CS",
            "posted_date": "2026-11-14",
            "apply_url": "https://acme.example.com/careers",
            "source": "Employer career page",
        },
    )
    assert created.status_code == 201
    job_id = created.json()["id"]

    # Application tracker save -> patch -> delete
    app_saved = client.post("/api/applications", headers=auth_headers, json={"job_id": job_id, "status": "saved"})
    assert app_saved.status_code == 201
    app_id = app_saved.json()["id"]

    app_upd = client.patch(
        f"/api/applications/{app_id}",
        headers=auth_headers,
        json={"status": "applied", "notes": "Submitted via official portal"},
    )
    assert app_upd.status_code == 200
    assert app_upd.json()["status"] == "applied"

    assert client.delete(f"/api/applications/{app_id}", headers=auth_headers).status_code == 204


def test_dashboard_reference_and_orchestrator_endpoints(client: TestClient, auth_headers: dict[str, str]) -> None:
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert len(client.get("/api/skills").json()) >= 15
    assert len(client.get("/api/roles").json()) >= 9
    assert len(client.get("/api/assessments/available").json()) >= 5
    assert len(client.get("/api/mentor/suggestions", headers=auth_headers).json()) >= 4

    run = client.post("/api/agents/run", headers=auth_headers, json={"trigger": "manual"}).json()
    assert len(run["trace"]) >= 7
    dash = client.get("/api/dashboard", headers=auth_headers).json()
    assert "verified_skills" in dash
    assert len(dash["top_careers"]) == 3
    assert len(dash["readiness_trend"]) >= 1
    assert isinstance(client.get("/api/applications", headers=auth_headers).json(), list)


def test_gemini_failure_falls_back_gracefully(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    from app.core.config import get_settings

    get_settings.cache_clear()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("Network unreachable")

    import httpx

    monkeypatch.setattr(httpx.Client, "post", _boom)

    resp = client.post(
        "/api/mentor/chat",
        headers=auth_headers,
        json={"message": "Which career suits me?", "language": "en"},
    )
    assert resp.status_code == 200
    assert resp.json()["mode"] == "deterministic"
    get_settings.cache_clear()
