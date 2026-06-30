"""Scaffold test for the health endpoint and the API /api prefix."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vcm.main import create_app


def test_health() -> None:
    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["extract_model"] == "claude-sonnet-4-6"
    assert body["verify_model"] == "claude-opus-4-8"
