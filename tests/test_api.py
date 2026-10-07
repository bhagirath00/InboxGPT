"""Tests for FastAPI endpoints."""

from fastapi.testclient import TestClient
from inboxgpt.api.app import app

client = TestClient(app)


def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_emails_list():
    response = client.get("/api/v1/emails?max_results=5")
    assert response.status_code == 200
    emails = response.json()
    assert isinstance(emails, list)
    assert len(emails) <= 5


def test_api_analyze():
    response = client.post("/api/v1/analyze?dry_run=true")
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data
    assert "proposed_actions" in data
    assert len(data["proposed_actions"]) > 0


def test_api_action_approve():
    # First get a proposed action
    analyze_resp = client.post("/api/v1/analyze?dry_run=true")
    proposals = analyze_resp.json()["proposed_actions"]
    assert len(proposals) > 0

    target_action = proposals[0]
    approve_resp = client.post(
        "/api/v1/actions/approve",
        json={"action": target_action, "dry_run": True},
    )
    assert approve_resp.status_code == 200
    result = approve_resp.json()
    assert result["success"] is True
