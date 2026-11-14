"""Tests for skill assessments, verified vs self-reported scoring, reassessment, and intelligence."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.data.catalog import load_questions


def test_assessment_scoring_reassessment_and_topic_diagnostics(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    client.put(
        "/api/profile",
        headers=auth_headers,
        json={
            "technical_skills": [
                {"name": "Python", "self_level": "advanced"},
                {"name": "SQL", "self_level": "intermediate"},
            ],
            "target_role": "data_analyst",
        },
    )

    # Before assessment: both skills are unverified
    verified_before = client.get("/api/skills/verified", headers=auth_headers).json()
    assert all(v["status"] == "self_reported" and v["verified_score"] is None for v in verified_before)

    # Start beginner Python assessment and submit only 1 right answer (low score -> triggers targeted practice)
    start1 = client.post("/api/assessments/start", headers=auth_headers, json={"skill": "Python", "level": "beginner"})
    assert start1.status_code == 201
    s1 = start1.json()
    q_answer_map = {q["id"]: q["answer"] for q in load_questions()}

    wrong_answers = {q["id"]: "WRONG" for q in s1["questions"]}
    wrong_answers[s1["questions"][0]["id"]] = q_answer_map[s1["questions"][0]["id"]]

    sub1 = client.post(f"/api/assessments/{s1['attempt_id']}/submit", headers=auth_headers, json={"answers": wrong_answers})
    assert sub1.status_code == 200
    r1 = sub1.json()
    assert r1["score"] < 40
    assert len(r1["weak_topics"]) >= 1

    # Duplicate submit rejected
    assert (
        client.post(f"/api/assessments/{s1['attempt_id']}/submit", headers=auth_headers, json={"answers": wrong_answers}).status_code
        == 409
    )

    # Reassess at intermediate level with all correct answers -> verified score rises significantly
    start2 = client.post("/api/assessments/start", headers=auth_headers, json={"skill": "Python", "level": "intermediate"})
    s2 = start2.json()
    right_answers = {q["id"]: q_answer_map[q["id"]] for q in s2["questions"]}
    sub2 = client.post(f"/api/assessments/{s2['attempt_id']}/submit", headers=auth_headers, json={"answers": right_answers})
    assert sub2.status_code == 200
    r2 = sub2.json()
    assert r2["score"] == 100.0
    assert r2["verified_score"] > r1["score"]

    # History shows both attempts
    hist = client.get("/api/assessments/history", headers=auth_headers).json()
    assert len(hist) == 2

    # SQL remains self_reported while Python is verified
    verified_after = {v["skill"]: v for v in client.get("/api/skills/verified", headers=auth_headers).json()}
    assert verified_after["Python"]["status"] == "verified"
    assert verified_after["SQL"]["status"] == "self_reported"


def test_obsolescence_detection_respects_evidence(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.put(
        "/api/profile",
        headers=auth_headers,
        json={
            "technical_skills": [
                {"name": "SQL", "self_level": "intermediate"},
                {"name": "Python 2", "self_level": "intermediate"},
            ]
        },
    )
    intel = client.get("/api/intelligence", headers=auth_headers).json()
    outdated_names = [o["skill"] for o in intel["outdated"]]
    assert "Python 2" in outdated_names
    assert "SQL" not in outdated_names
