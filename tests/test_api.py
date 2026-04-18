"""FastAPI route tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from secubot.api import app, web_scanner

client = TestClient(app)

_FIXTURE_REPORT = {
    "url": "https://example.com",
    "timestamp": "2026-01-01T00:00:00+00:00",
    "headers": {},
    "exposed_paths": [],
    "redirects": {},
    "cookies": [],
    "risk_score": 12,
}


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_scan_valid(mocker) -> None:
    mocker.patch.object(web_scanner, "run_full_scan", new_callable=AsyncMock, return_value=_FIXTURE_REPORT)
    response = client.post("/scan", json={"url": "https://example.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["risk_score"] == 12


def test_scan_invalid_url() -> None:
    response = client.post("/scan", json={"url": "not-a-url"})
    assert response.status_code in (400, 422)


def test_scan_private_url() -> None:
    response = client.post("/scan", json={"url": "http://localhost"})
    assert response.status_code == 400


def test_security_headers_on_response() -> None:
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
