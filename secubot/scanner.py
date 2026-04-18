"""
SecuBot web vulnerability scanner.

Provides async scanning for HTTP security headers, exposed paths,
cookie security flags, and open redirect detection.
All network calls use httpx.AsyncClient with enforced timeouts.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from secubot.types import HeaderResult, ScanReport
from secubot.utils import validate_url

logger = logging.getLogger(__name__)

SECURITY_HEADERS = [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
    "Permissions-Policy",
    "X-XSS-Protection",
]

EXPOSED_PATHS = [
    ".env",
    ".git/config",
    "admin",
    "wp-admin",
    "phpinfo.php",
    ".DS_Store",
    "backup.zip",
    "config.json",
    "api/v1/users",
    "actuator/health",
    "debug",
    "console",
]

RISK_WEIGHTS = {
    "missing_csp": 15,
    "missing_hsts": 15,
    "missing_header": 5,
    "exposed_path": 15,
    "open_redirect": 20,
    "missing_cookie_flag": 5,
}

REQUEST_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
MAX_REDIRECTS = 3

_OTHER_SECURITY_HEADERS = [h for h in SECURITY_HEADERS if h not in ("Content-Security-Policy", "Strict-Transport-Security")]


def _scan_failed() -> dict[str, Any]:
    return {"error": True, "message": "Scan failed — check the URL and try again"}


def _join_origin_path(origin: str, path: str) -> str:
    """Build absolute URL for a path relative to origin."""

    if path.startswith("/"):
        p = urlparse(origin)
        return urlunparse((p.scheme, p.netloc, path, "", "", ""))
    return f"{origin.rstrip('/')}/{path}"


def _canonical_request_url(url: str) -> str:
    """Normalize URL so httpx requests match a stable form (path ``/`` if empty)."""

    parsed = urlparse(url)
    path = parsed.path if parsed.path else "/"
    return urlunparse((parsed.scheme, parsed.netloc, path, parsed.query, "", ""))


def _append_query(url: str, param: str, value: str) -> str:
    """Append a query parameter, using ``?`` or ``&`` as appropriate."""

    return f"{url}&{param}={value}" if "?" in url else f"{url}?{param}={value}"


class WebScanner:
    """Async HTTP scanner for common web security checks."""

    async def scan_headers(self, url: str) -> dict[str, HeaderResult] | dict[str, Any]:
        """Scan HTTP security headers for a given URL.

        Args:
            url: The target URL to scan. Must be a valid public HTTP/HTTPS URL.

        Returns:
            Mapping of header name to presence/value, or a structured error dict.
        """

        validate_url(url)
        target = _canonical_request_url(url)
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                limits=httpx.Limits(),
                max_redirects=MAX_REDIRECTS,
            ) as client:
                response = await client.get(target, follow_redirects=True)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("Request failed for %s: %s", url, str(exc))
            return _scan_failed()
        result: dict[str, HeaderResult] = {}
        for name in SECURITY_HEADERS:
            val = response.headers.get(name)
            result[name] = {"present": val is not None, "value": val}
        return result

    async def scan_exposed_paths(self, url: str) -> list[dict[str, Any]]:
        """Probe common sensitive paths and report HTTP status."""

        validate_url(url)
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        rows: list[dict[str, Any]] = []
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            limits=httpx.Limits(),
            max_redirects=MAX_REDIRECTS,
        ) as client:
            for path in EXPOSED_PATHS:
                full = _join_origin_path(origin, path)
                try:
                    response = await client.get(full, follow_redirects=True)
                    exposed = response.status_code == 200
                    rows.append({"path": path, "status": response.status_code, "exposed": exposed})
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    logger.warning("Request failed for %s: %s", full, str(exc))
                    rows.append({"path": path, "status": 0, "exposed": False})
        return rows

    async def scan_redirects(self, url: str) -> dict[str, Any]:
        """Detect potential open redirects via common query parameters."""

        validate_url(url)
        parsed = urlparse(url)
        host = parsed.netloc
        open_redirect = False
        checks: list[dict[str, Any]] = []
        async with httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            limits=httpx.Limits(),
            max_redirects=0,
        ) as client:
            base = _canonical_request_url(url)
            for param, evil in (("url", "https://evil.com"), ("redirect", "https://evil.com")):
                test_url = _append_query(base, param, evil)
                try:
                    response = await client.get(test_url, follow_redirects=False)
                except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                    logger.warning("Request failed for %s: %s", test_url, str(exc))
                    checks.append({"param": param, "status": None, "open_redirect": False})
                    continue
                location = response.headers.get("location") or response.headers.get("Location")
                redirected_out = False
                if response.status_code in (301, 302, 303, 307, 308) and location:
                    loc_p = urlparse(location)
                    if loc_p.netloc and loc_p.netloc != host:
                        redirected_out = True
                        open_redirect = True
                checks.append(
                    {
                        "param": param,
                        "status": response.status_code,
                        "location": location,
                        "open_redirect": redirected_out,
                    }
                )
        return {"open_redirect": open_redirect, "checks": checks}

    def _parse_set_cookie(self, header_value: str) -> dict[str, Any]:
        """Parse a single Set-Cookie header into structured fields."""

        parts = [p.strip() for p in header_value.split(";")]
        if not parts:
            return {"name": "", "value": "", "secure": False, "http_only": False, "same_site": None}
        first = parts[0]
        if "=" in first:
            name, value = first.split("=", 1)
        else:
            name, value = first, ""
        flags = {p.split("=", 1)[0].lower(): p for p in parts[1:]}
        same_site: str | None = None
        for key, raw in flags.items():
            if key.startswith("samesite"):
                same_site = raw.split("=", 1)[-1].strip() if "=" in raw else None
        return {
            "name": name.strip(),
            "value": value.strip(),
            "secure": "secure" in flags,
            "http_only": "httponly" in flags,
            "same_site": same_site,
        }

    async def scan_cookies(self, url: str) -> list[dict[str, Any]]:
        """Inspect Set-Cookie flags on the primary response."""

        validate_url(url)
        target = _canonical_request_url(url)
        try:
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT,
                limits=httpx.Limits(),
                max_redirects=MAX_REDIRECTS,
            ) as client:
                response = await client.get(target, follow_redirects=True)
        except (httpx.RequestError, httpx.HTTPStatusError) as exc:
            logger.warning("Request failed for %s: %s", url, str(exc))
            return []
        cookies: list[dict[str, Any]] = []
        for key, value in response.headers.multi_items():
            if key.lower() == "set-cookie":
                parsed = self._parse_set_cookie(value)
                # Fallback name from SimpleCookie if needed
                if not parsed["name"]:
                    sc = SimpleCookie()
                    try:
                        sc.load(value)
                    except Exception:
                        logger.debug("Could not parse cookie line")
                    else:
                        for n, morsel in sc.items():
                            parsed["name"] = n
                            parsed["value"] = morsel.value
                cookies.append(parsed)
        return cookies

    def _risk_score(
        self,
        headers: dict[str, HeaderResult] | dict[str, Any],
        paths: list[dict[str, Any]],
        redirects: dict[str, Any],
        cookies: list[dict[str, Any]],
    ) -> int:
        """Aggregate numeric risk from findings (0–100, capped)."""

        score = 0
        if not isinstance(headers, dict) or headers.get("error"):
            return score
        csp = headers.get("Content-Security-Policy", {"present": False})
        if not csp.get("present"):
            score += RISK_WEIGHTS["missing_csp"]
        hsts = headers.get("Strict-Transport-Security", {"present": False})
        if not hsts.get("present"):
            score += RISK_WEIGHTS["missing_hsts"]
        for name in _OTHER_SECURITY_HEADERS:
            entry = headers.get(name, {"present": False})
            if not entry.get("present"):
                score += RISK_WEIGHTS["missing_header"]
        for row in paths:
            if row.get("exposed"):
                score += RISK_WEIGHTS["exposed_path"]
        if redirects.get("open_redirect"):
            score += RISK_WEIGHTS["open_redirect"]
        for c in cookies:
            if not c.get("secure"):
                score += RISK_WEIGHTS["missing_cookie_flag"]
            if not c.get("http_only"):
                score += RISK_WEIGHTS["missing_cookie_flag"]
            if not c.get("same_site"):
                score += RISK_WEIGHTS["missing_cookie_flag"]
        return min(score, 100)

    async def run_full_scan(self, url: str) -> ScanReport:
        """Run all checks concurrently and return a unified report."""

        validate_url(url)
        headers_raw, paths, redirects, cookies = await asyncio.gather(
            self.scan_headers(url),
            self.scan_exposed_paths(url),
            self.scan_redirects(url),
            self.scan_cookies(url),
        )
        headers: dict[str, HeaderResult]
        if isinstance(headers_raw, dict) and headers_raw.get("error"):
            headers = {h: {"present": False, "value": None} for h in SECURITY_HEADERS}
        else:
            headers = headers_raw  # type: ignore[assignment]
        risk = self._risk_score(headers, paths, redirects, cookies)
        timestamp = datetime.now(timezone.utc).isoformat()
        return {
            "url": url,
            "timestamp": timestamp,
            "headers": headers,
            "exposed_paths": paths,
            "redirects": redirects,
            "cookies": cookies,
            "risk_score": risk,
        }
