# Agent 05 — README & Documentation Polish

You are a technical writer reviewing SecuBot's documentation before it goes public on GitHub. This repo will be linked on a CV — it must look professional and intentional.

## Your job

Review and rewrite the following files. Make changes directly.

---

## README.md — full rewrite to this structure

The README must be clean, scannable, and CV-friendly. Use this exact structure:

```markdown
# SecuBot

> Web vulnerability scanner with Telegram alerts and AI-powered explanations.

[![CI](https://github.com/YOUR_USERNAME/secubot/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/secubot/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What it does

SecuBot scans a target URL for common web vulnerabilities and misconfigurations:

- **HTTP security headers** — checks for CSP, HSTS, X-Frame-Options, and 4 others
- **Exposed paths** — probes 12 common sensitive endpoints (`.env`, `.git/config`, admin panels...)
- **Cookie security** — audits Secure, HttpOnly, and SameSite flags
- **Open redirects** — detects redirect parameters pointing outside the origin domain
- **Risk score** — aggregates findings into a 0–100 score
- **Telegram bot** — delivers scan results and LLM-generated explanations directly to your chat
- **REST API** — FastAPI endpoint for programmatic access

## Architecture

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                         Entry points                        │
│   CLI (scripts/scan.py)   Telegram bot   FastAPI REST API   │
└──────────────────┬──────────────┬───────────────┬───────────┘
                   │              │               │
                   └──────────────▼───────────────┘
                          WebScanner (scanner.py)
                     scan_headers · scan_exposed_paths
                     scan_cookies · scan_redirects
                     run_full_scan · risk_score
                                   │
                   ┌───────────────▼───────────────┐
                   │         Explainer (explainer.py)│
                   │   OpenAI GPT-4o-mini · French  │
                   └───────────────────────────────-┘
\`\`\`

## Quick start

\`\`\`bash
git clone https://github.com/YOUR_USERNAME/secubot.git
cd secubot
cp .env.example .env
# Edit .env with your keys
pip install -r requirements.txt
\`\`\`

## Usage

### CLI

\`\`\`bash
# Basic scan
python scripts/scan.py https://example.com

# With AI explanation (French)
python scripts/scan.py https://example.com --explain

# JSON output for piping
python scripts/scan.py https://example.com --json | jq '.risk_score'
\`\`\`

### API

\`\`\`bash
# Start the API
uvicorn secubot.api:app --reload

# Scan a URL
curl -X POST http://localhost:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Scan + AI explanation
curl -X POST http://localhost:8000/scan/explain \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
\`\`\`

### Docker

\`\`\`bash
docker-compose up
\`\`\`

### Telegram bot

1. Create a bot via [@BotFather](https://t.me/BotFather), get your token
2. Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
3. Run: `python -m secubot.bot`
4. Send `/scan https://example.com` to your bot

## Configuration

| Variable | Description | Required |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI API key for explanations | For `--explain` only |
| `OPENAI_MODEL` | Model to use (default: `gpt-4o-mini`) | No |
| `TELEGRAM_TOKEN` | Telegram bot token | For bot only |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID | For bot only |

## Development

\`\`\`bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=secubot --cov-report=term-missing
\`\`\`

## Ce que ce projet démontre

Built as a learning project to put Python into practice:

- **Python async** — `asyncio.gather()` for concurrent scans, `httpx.AsyncClient`
- **Web security** — OWASP headers, SSRF prevention, cookie flags, path enumeration
- **LLM integration** — OpenAI API (v1.x SDK), structured prompting, graceful fallback
- **REST API** — FastAPI, Pydantic validation, middleware, structured error handling
- **Bot development** — `python-telegram-bot` v21, async handlers, rate limiting
- **Docker** — multi-stage build, non-root user, environment isolation
- **CI/CD** — GitHub Actions, automated test runs on push and PR

## License

MIT
```

Replace `YOUR_USERNAME` with the actual GitHub username throughout.

---

## `.env.example` — verify and polish

Must look exactly like this:
```bash
# SecuBot configuration
# Copy this file to .env and fill in your values

# OpenAI (required for --explain and /scan/explain)
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini

# Telegram bot (required for bot mode)
TELEGRAM_TOKEN=your-telegram-bot-token
TELEGRAM_CHAT_ID=your-chat-id

# Scanner defaults
REQUEST_TIMEOUT_SECONDS=10
MAX_CONCURRENT_SCANS=5
```

---

## `LICENSE` — create if missing

Create a `LICENSE` file with the MIT license text. Use the current year and the user's name as the copyright holder (use `[YOUR NAME]` as placeholder).

---

## `secubot/scanner.py` — module docstring

Add a module-level docstring at the very top:
```python
"""
SecuBot web vulnerability scanner.

Provides async scanning for HTTP security headers, exposed paths,
cookie security flags, and open redirect detection.
All network calls use httpx.AsyncClient with enforced timeouts.
"""
```

Do the same for `api.py`, `bot.py`, `explainer.py`, and `utils.py` with appropriate one-paragraph descriptions.

---

## Final check

After making all changes, verify:
- README renders correctly (no broken markdown — check backtick pairs, heading levels)
- The architecture ASCII diagram is aligned properly
- The badge URLs reference the correct GitHub username and repo name
- `.env.example` has no real keys in it (only placeholders)
- LICENSE file exists

Output: `✅ Documentation ready for public GitHub`
