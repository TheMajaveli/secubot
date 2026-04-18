"""
Telegram bot interface for SecuBot scans and explanations.

Uses python-telegram-bot v21 async application model.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from secubot.explainer import Explainer
from secubot.scanner import WebScanner
from secubot.utils import get_config, validate_url

logger = logging.getLogger(__name__)

_RATE: dict[int, list[float]] = defaultdict(list)
_MAX_SCANS = 3
_WINDOW_SEC = 60.0


def _rate_limited(user_id: int) -> bool:
    """Return True if the user exceeded the scan rate limit."""

    now = time.monotonic()
    window_start = now - _WINDOW_SEC
    stamps = [t for t in _RATE[user_id] if t >= window_start]
    _RATE[user_id] = stamps
    if len(stamps) >= _MAX_SCANS:
        return True
    stamps.append(now)
    _RATE[user_id] = stamps
    return False


def _mdv2_escape(text: str) -> str:
    """Escape text for Telegram MarkdownV2."""

    specials = r"_*[]()~`>#+-=|{}.!"
    out = []
    for ch in text:
        if ch in specials:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""

    if update.effective_chat is None:
        return
    text = (
        "Welcome to *SecuBot*\\.\n"
        "I scan websites for missing security headers, exposed paths, "
        "cookie issues, and open redirects\\.\n"
        "Use /scan `<url>` to run a scan\\."
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help — list commands."""

    if update.effective_chat is None:
        return
    text = (
        "*Commands*\n"
        "/start \\- intro\n"
        "/scan `<url>` \\- full scan \\+ explanation\n"
        "/help \\- this message"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)


async def scan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan <url> — run scanner and send summary \\+ explainer."""

    if update.message is None or update.effective_user is None:
        return
    user_id = update.effective_user.id
    if _rate_limited(user_id):
        await update.message.reply_text(
            "You are scanning too quickly. Please wait up to a minute and try again."
        )
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /scan <https://example.com>")
        return
    raw_url = args[0].strip()
    try:
        validate_url(raw_url)
    except ValueError:
        await update.message.reply_text("Invalid or private URL.")
        return
    scanner = WebScanner()
    expl = Explainer()
    try:
        report = await scanner.run_full_scan(raw_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scan failed: %s", exc)
        await update.message.reply_text("Scan failed — please try again later.")
        return
    summary = _format_summary(report)
    await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN_V2)
    explanation = expl.explain_report(dict(report))
    safe = _mdv2_escape(explanation[:3500])
    await update.message.reply_text(safe, parse_mode=ParseMode.MARKDOWN_V2)


def _format_summary(report: dict[str, Any]) -> str:
    """Build a MarkdownV2 summary from a scan report."""

    score = int(report.get("risk_score", 0))
    emoji = "🟢" if score < 33 else "🟡" if score < 66 else "🔴"
    lines: list[str] = []
    lines.append(f"*SecuBot scan* for `{_mdv2_escape(str(report.get('url','')))}`")
    lines.append("")
    headers = report.get("headers", {})
    for name, data in headers.items():
        present = data.get("present")
        mark = "✅" if present else "⚠️"
        if name in ("Content-Security-Policy", "Strict-Transport-Security") and not present:
            mark = "🚨"
        short = name.split("-")[0]
        lines.append(f"{mark} `{_mdv2_escape(short)}`")
    lines.append("")
    exposed = [p for p in report.get("exposed_paths", []) if p.get("exposed")]
    if exposed:
        lines.append("🚨 *Exposed paths*")
        for p in exposed:
            lines.append(f"\\- `{_mdv2_escape(p.get('path',''))}`")
    else:
        lines.append("✅ *No exposed probe paths \\(200\\)*")
    lines.append("")
    if report.get("redirects", {}).get("open_redirect"):
        lines.append("🚨 *Open redirect suspected*")
    else:
        lines.append("✅ *No open redirect pattern detected*")
    lines.append("")
    lines.append(f"*Risk score:* {score}/100 {emoji}")
    return "\n".join(lines)


def main() -> None:
    """Start the Telegram bot if credentials are configured."""

    from secubot.utils import setup_logging

    setup_logging()
    cfg = get_config()
    if not cfg.telegram_token.strip():
        logger.error("TELEGRAM_TOKEN missing — cannot start bot.")
        return
    application = Application.builder().token(cfg.telegram_token).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("scan", scan_cmd))
    application.run_polling()


if __name__ == "__main__":
    main()
