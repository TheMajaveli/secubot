"""Scanner tests with mocked HTTP (respx)."""

from __future__ import annotations

import httpx
import pytest
import respx

from secubot.scanner import SECURITY_HEADERS, WebScanner


@pytest.fixture
def scanner() -> WebScanner:
    return WebScanner()


@pytest.mark.asyncio
async def test_scan_headers_all_present(scanner: WebScanner) -> None:
    hdrs = {
        "Content-Security-Policy": "default-src 'self'",
        "Strict-Transport-Security": "max-age=31536000",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=()",
        "X-XSS-Protection": "0",
    }
    with respx.mock:
        respx.get("https://example.com/").mock(return_value=httpx.Response(200, headers=hdrs))
        out = await scanner.scan_headers("https://example.com")
    assert "error" not in out
    for name in SECURITY_HEADERS:
        assert out[name]["present"] is True
        assert out[name]["value"] == hdrs[name]


@pytest.mark.asyncio
async def test_scan_headers_missing(scanner: WebScanner) -> None:
    with respx.mock:
        respx.get("https://example.com/").mock(return_value=httpx.Response(200, headers={}))
        out = await scanner.scan_headers("https://example.com")
    assert "error" not in out
    for name in SECURITY_HEADERS:
        assert out[name]["present"] is False
        assert out[name]["value"] is None


@pytest.mark.asyncio
async def test_scan_headers_timeout(scanner: WebScanner) -> None:
    with respx.mock:
        respx.get("https://example.com/").mock(side_effect=httpx.ConnectTimeout("timeout"))
        out = await scanner.scan_headers("https://example.com")
    assert out.get("error") is True
    assert "message" in out


@pytest.mark.asyncio
async def test_scan_exposed_paths_env(scanner: WebScanner) -> None:
    with respx.mock:

        def route(request: httpx.Request) -> httpx.Response:
            u = str(request.url)
            if u.endswith("/.env"):
                return httpx.Response(200)
            return httpx.Response(404)

        respx.route(method="GET", url__startswith="https://example.com/").mock(side_effect=route)
        out = await scanner.scan_exposed_paths("https://example.com")
    exposed = [r for r in out if r["exposed"]]
    assert len(exposed) == 1
    assert exposed[0]["path"] == ".env"


@pytest.mark.asyncio
async def test_scan_exposed_paths_none(scanner: WebScanner) -> None:
    with respx.mock:
        respx.route(method="GET", url__startswith="https://example.com/").mock(
            return_value=httpx.Response(404)
        )
        out = await scanner.scan_exposed_paths("https://example.com")
    assert not any(r["exposed"] for r in out)


@pytest.mark.asyncio
async def test_scan_cookies_flags_present(scanner: WebScanner) -> None:
    with respx.mock:
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(
                200,
                headers={"Set-Cookie": "session=abc; Secure; HttpOnly; SameSite=Strict"},
            )
        )
        out = await scanner.scan_cookies("https://example.com")
    assert out
    c = out[0]
    assert c["secure"] is True
    assert c["http_only"] is True
    assert c.get("same_site")


@pytest.mark.asyncio
async def test_scan_cookies_flags_missing(scanner: WebScanner) -> None:
    with respx.mock:
        respx.get("https://example.com/").mock(
            return_value=httpx.Response(200, headers={"Set-Cookie": "session=abc"})
        )
        out = await scanner.scan_cookies("https://example.com")
    assert out
    c = out[0]
    assert c["secure"] is False
    assert c["http_only"] is False
    assert c.get("same_site") in (None, "")


@pytest.mark.asyncio
async def test_run_full_scan_risk_65(scanner: WebScanner) -> None:
    def response_for(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "?" in u and ("url=https" in u or "redirect=https" in u):
            return httpx.Response(302, headers={"location": "https://evil.com/x"})
        if u == "https://example.com/":
            h = {
                "x-frame-options": "DENY",
                "x-content-type-options": "nosniff",
                "referrer-policy": "no-referrer",
                "permissions-policy": "geolocation=()",
                "x-xss-protection": "0",
                "set-cookie": "session=abc; Secure; HttpOnly; SameSite=Strict",
            }
            return httpx.Response(200, headers=h)
        if u.endswith("/.env"):
            return httpx.Response(200)
        return httpx.Response(404)

    with respx.mock:
        respx.route(method="GET", url__startswith="https://example.com").mock(side_effect=response_for)
        report = await scanner.run_full_scan("https://example.com")
    assert report["risk_score"] == 65


@pytest.mark.asyncio
async def test_run_full_scan_perfect(scanner: WebScanner) -> None:
    full_headers = {
        "Content-Security-Policy": "default-src 'none'",
        "Strict-Transport-Security": "max-age=31536000",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=()",
        "X-XSS-Protection": "0",
        "Set-Cookie": "session=abc; Secure; HttpOnly; SameSite=Strict",
    }

    def response_for(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "?" in u:
            return httpx.Response(200)
        if u == "https://example.com/":
            return httpx.Response(200, headers=full_headers)
        return httpx.Response(404)

    with respx.mock:
        respx.route(method="GET", url__startswith="https://example.com").mock(side_effect=response_for)
        report = await scanner.run_full_scan("https://example.com")
    assert report["risk_score"] == 0


@pytest.mark.asyncio
async def test_run_full_scan_structure(scanner: WebScanner) -> None:
    full_headers = {
        "Content-Security-Policy": "default-src 'none'",
        "Strict-Transport-Security": "max-age=31536000",
        "X-Frame-Options": "DENY",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "geolocation=()",
        "X-XSS-Protection": "0",
    }

    def response_for(request: httpx.Request) -> httpx.Response:
        u = str(request.url)
        if "?" in u:
            return httpx.Response(200)
        if u == "https://example.com/":
            return httpx.Response(200, headers=full_headers)
        return httpx.Response(404)

    with respx.mock:
        respx.route(method="GET", url__startswith="https://example.com").mock(side_effect=response_for)
        report = await scanner.run_full_scan("https://example.com")
    for key in ("url", "timestamp", "headers", "exposed_paths", "redirects", "cookies", "risk_score"):
        assert key in report
