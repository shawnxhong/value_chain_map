"""API tests for the pipeline ingest routes (no DB — validation paths only)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from vcm.main import create_app

client = TestClient(create_app())


def test_pipeline_routes_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    assert "/api/pipeline/ingest" in paths
    assert "/api/pipeline/ingest/edgar" in paths
    assert "/api/pipeline/run" in paths


def test_run_missing_body_returns_422() -> None:
    assert client.post("/api/pipeline/run", json={}).status_code == 422


def test_upload_invalid_source_type_returns_422_without_db() -> None:
    resp = client.post(
        "/api/pipeline/ingest",
        files={"file": ("t.txt", b"some text", "text/plain")},
        data={"source_type": "not_a_real_type", "title": "T"},
    )
    assert resp.status_code == 422
    assert "source_type" in resp.json()["detail"]


def test_upload_empty_file_returns_422() -> None:
    resp = client.post(
        "/api/pipeline/ingest",
        files={"file": ("t.txt", b"", "text/plain")},
        data={"source_type": "transcript", "title": "T"},
    )
    assert resp.status_code == 422


def test_edgar_missing_body_returns_422() -> None:
    assert client.post("/api/pipeline/ingest/edgar", json={}).status_code == 422
