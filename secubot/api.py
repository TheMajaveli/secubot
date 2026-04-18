"""
FastAPI application exposing SecuBot scan and health endpoints.

Includes security headers middleware and structured validation.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from secubot.explainer import Explainer
from secubot.scanner import WebScanner
from secubot.types import ScanReport
from secubot.utils import validate_url

logger = logging.getLogger(__name__)

app = FastAPI(title="SecuBot", version="0.1.0")
web_scanner = WebScanner()
explainer = Explainer()


@app.middleware("http")
async def add_security_headers(request: Request, call_next: Any) -> Any:
    """Attach baseline security headers to every response."""

    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return a generic JSON error without leaking internals."""

    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


class URLRequest(BaseModel):
    """Validated scan request body."""

    url: str

    @field_validator("url")
    @classmethod
    def must_be_http(cls, value: str) -> str:
        """Reject obviously invalid schemes before SSRF checks."""

        if not (value.startswith("http://") or value.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


@app.get("/")
async def root() -> dict[str, str]:
    """Service metadata."""

    return {"status": "ok", "service": "SecuBot"}


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness probe for orchestrators."""

    return {"status": "healthy"}


@app.post("/scan")
async def scan(body: URLRequest) -> ScanReport:
    """Run a full scan for the given public URL."""

    try:
        validate_url(body.url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or private URL") from None
    return await web_scanner.run_full_scan(body.url)


@app.post("/scan/explain")
async def scan_explain(body: URLRequest) -> ScanReport:
    """Run a scan and attach a French LLM explanation."""

    try:
        validate_url(body.url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid or private URL") from None
    report = await web_scanner.run_full_scan(body.url)
    explanation = explainer.explain_report(dict(report))
    out = dict(report)
    out["explanation"] = explanation
    return out  # type: ignore[return-value]
