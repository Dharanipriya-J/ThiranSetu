"""Tests for authentication, authorization, profile management, validation, and rate limiting."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_register_login_logout_and_revocation(client: TestClient) -> None:
    reg = client.post(
        "/api/auth/register",
        json={"email": "priya@example.com", "password": "Password1", "full_name": "Priya Devi"},
    )
    assert reg.status_code == 201
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200

    # Duplicate email rejected
    dup = client.post(
        "/api/auth/register",
        json={"email": "priya@example.com", "password": "Password1", "full_name": "Priya Devi"},
    )
    assert dup.status_code == 409

    # Logout revokes existing token immediately (with CSRF header matching ts_csrf cookie)
    logout_headers = {**headers, "X-CSRF-Token": reg.cookies.get("ts_csrf", "")}
    assert client.post("/api/auth/logout", headers=logout_headers).status_code == 204
    assert client.get("/api/auth/me", headers=headers).status_code == 401

    # Wrong password rejected
    bad_login = client.post("/api/auth/login", json={"email": "priya@example.com", "password": "Wrong123"})
    assert bad_login.status_code == 401

    # Valid login issues fresh working token
    good_login = client.post("/api/auth/login", json={"email": "priya@example.com", "password": "Password1"})
    assert good_login.status_code == 200
    new_headers = {"Authorization": f"Bearer {good_login.json()['access_token']}"}
    assert client.get("/api/auth/me", headers=new_headers).status_code == 200


def test_unauthorized_access_blocked(client: TestClient) -> None:
    for path in ["/api/profile", "/api/dashboard", "/api/careers", "/api/jobs", "/api/roadmap"]:
        assert client.get(path).status_code == 401


def test_profile_update_and_validation(client: TestClient, auth_headers: dict[str, str]) -> None:
    update = client.put(
        "/api/profile",
        headers=auth_headers,
        json={
            "education": "B.Tech CSE",
            "college": "Anna University",
            "graduation_year": 2026,
            "technical_skills": [
                {"name": "python", "self_level": "intermediate"},
                {"name": "SQL", "self_level": "beginner"},
            ],
            "soft_skills": ["Communication", "Teamwork"],
            "projects": [{"title": "Sales Dashboard", "description": "Built KPIs", "skills": ["SQL", "Excel"]}],
            "career_interests": ["data_analyst"],
            "target_role": "data_analyst",
            "current_location": "Coimbatore",
            "preferred_locations": ["Chennai", "Bengaluru"],
            "willing_to_relocate": True,
            "work_mode": "hybrid",
            "expected_salary_lpa": 6.0,
            "min_salary_lpa": 4.0,
            "learning_language": "ta",
            "app_language": "en",
        },
    )
    assert update.status_code == 200
    data = update.json()
    assert data["technical_skills"][0]["name"] == "Python"
    assert data["current_location"] == "Coimbatore"
    assert data["preferred_locations"] == ["Chennai", "Bengaluru"]
    assert data["completeness"] > 70

    # min_salary_lpa > expected_salary_lpa must fail validation
    bad_sal = client.put(
        "/api/profile",
        headers=auth_headers,
        json={"expected_salary_lpa": 4.0, "min_salary_lpa": 7.0},
    )
    assert bad_sal.status_code == 422


def test_rate_limit_cannot_be_bypassed_by_spoofed_xff(client: TestClient) -> None:
    for i in range(20):
        r = client.post(
            "/api/auth/login",
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
            json={"email": "nobody@example.com", "password": "Password1"},
        )
        assert r.status_code == 401
    blocked = client.post(
        "/api/auth/login",
        headers={"X-Forwarded-For": "10.0.0.99"},
        json={"email": "nobody@example.com", "password": "Password1"},
    )
    assert blocked.status_code == 429
