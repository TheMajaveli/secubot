"""Typed structures for SecuBot scan results and API payloads."""

from typing import Any, Literal, NotRequired, TypedDict


class HeaderResult(TypedDict):
    """Single security header probe result."""

    present: bool
    value: str | None


class ScanError(TypedDict):
    """Structured scanner failure (no internal exception text exposed)."""

    error: Literal[True]
    message: str


class ScanReport(TypedDict):
    """Unified report returned by ``WebScanner.run_full_scan``."""

    url: str
    timestamp: str
    headers: dict[str, HeaderResult]
    exposed_paths: list[dict[str, Any]]
    redirects: dict[str, Any]
    cookies: list[dict[str, Any]]
    risk_score: int
    explanation: NotRequired[str]
