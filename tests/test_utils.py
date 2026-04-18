"""Tests for URL validation and utilities."""

import pytest

from secubot.utils import validate_url


def test_valid_urls_pass() -> None:
    """Valid public URLs pass validation."""

    for url in (
        "https://example.com",
        "http://example.com",
        "https://sub.example.com/path?q=1",
    ):
        assert validate_url(url) == url


def test_private_urls_rejected() -> None:
    """Private and loopback URLs are rejected."""

    for url in (
        "http://localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
        "http://192.168.1.1",
        "http://10.0.0.1",
        "http://172.16.0.1",
    ):
        with pytest.raises(ValueError, match="Invalid or private URL"):
            validate_url(url)


def test_bad_schemes_rejected() -> None:
    """Non-HTTP(S) schemes and garbage strings are rejected."""

    for url in (
        "ftp://example.com",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "just-a-string",
        "",
    ):
        with pytest.raises(ValueError):
            validate_url(url)
