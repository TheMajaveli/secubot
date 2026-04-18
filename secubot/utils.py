"""
Configuration loading, URL validation, and logging setup for SecuBot.

Uses Pydantic settings with ``.env`` and structured logging via Rich.
"""

from __future__ import annotations

import ipaddress
import logging
import re
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.logging import RichHandler

load_dotenv()

_LOGGER_CONFIGURED = False


class Settings(BaseSettings):
    """Application configuration loaded from environment / ``.env``."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    target_url: str = Field(default="https://example.com", alias="TARGET_URL")
    telegram_token: str = Field(default="", alias="TELEGRAM_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    request_timeout_seconds: int = Field(default=10, alias="REQUEST_TIMEOUT_SECONDS")
    max_concurrent_scans: int = Field(default=5, alias="MAX_CONCURRENT_SCANS")


def setup_logging() -> None:
    """Configure root logging once with RichHandler for readable dev output."""

    global _LOGGER_CONFIGURED
    if _LOGGER_CONFIGURED:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )
    _LOGGER_CONFIGURED = True


def get_config() -> Settings:
    """Return cached application settings (loads from env each call for tests)."""

    setup_logging()
    return Settings()


def validate_url(url: str) -> str:
    """Validate URL is public and safe to scan. Raises ValueError if not.

    Args:
        url: Candidate HTTP or HTTPS URL.

    Returns:
        The same URL if valid.

    Raises:
        ValueError: If scheme, host, or network range is not allowed (SSRF guard).
    """

    if not url or not isinstance(url, str):
        raise ValueError("Invalid or private URL")
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Invalid or private URL")
    host = parsed.hostname
    if host is None:
        raise ValueError("Invalid or private URL")
    lowered = host.lower()
    if lowered in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
        raise ValueError("Invalid or private URL")
    if re.match(r"^10\.", host) or re.match(r"^192\.168\.", host):
        raise ValueError("Invalid or private URL")
    if re.match(r"^172\.(1[6-9]|2[0-9]|3[0-1])\.", host):
        raise ValueError("Invalid or private URL")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise ValueError("Invalid or private URL")
    return url.strip()
