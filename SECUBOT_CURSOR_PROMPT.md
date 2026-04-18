# SecuBot — Cursor / Claude Code Build Prompt

Paste this entire prompt into Cursor (Agent mode) or Claude Code.
It will scaffold the full project, write all code, and set up the git history with realistic timestamps across two branches.

---

## Your mission

Build a Python project called **SecuBot** — a web security scanner with a Telegram alert bot and an LLM explanation layer.

The project must be production-quality, understandable line by line, and showcase Python, web security concepts, and AI integration in a single codebase.

---

## Step 0 — Project structure to create

```
secubot/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .github/
│   └── workflows/
│       └── ci.yml
├── secubot/
│   ├── __init__.py
│   ├── scanner.py        # core vulnerability scanner
│   ├── bot.py            # Telegram bot
│   ├── explainer.py      # LLM explanation layer
│   ├── api.py            # FastAPI REST endpoint
│   └── utils.py          # helpers (logging, config)
├── tests/
│   ├── __init__.py
│   ├── test_scanner.py
│   └── test_utils.py
└── scripts/
    └── scan.py           # CLI entrypoint
```

---

## Step 1 — Write all the code

### `requirements.txt`
```
httpx==0.27.0
beautifulsoup4==4.12.3
fastapi==0.111.0
uvicorn==0.29.0
python-telegram-bot==21.3
openai==1.30.0
python-dotenv==1.0.1
pydantic==2.7.1
rich==13.7.1
pytest==8.2.0
pytest-asyncio==0.23.7
```

### `secubot/utils.py`
Load config from `.env`, set up structured logging with `rich`. Expose a `get_config()` function that returns a Pydantic `Settings` object with:
- `TARGET_URL: str`
- `TELEGRAM_TOKEN: str`
- `TELEGRAM_CHAT_ID: str`
- `OPENAI_API_KEY: str`
- `OPENAI_MODEL: str = "gpt-4o-mini"`

### `secubot/scanner.py`
Write a `WebScanner` class with these methods. Use `httpx` for all HTTP calls. Use `async` where it makes sense.

**`scan_headers(url: str) -> dict`**
Check for these security headers and return a dict with `present: bool` and `value: str | None` for each:
- `Content-Security-Policy`
- `Strict-Transport-Security`
- `X-Frame-Options`
- `X-Content-Type-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `X-XSS-Protection`

**`scan_exposed_paths(url: str) -> list[dict]`**
Check a list of common exposed paths and return which ones return a 200:
```python
PATHS = [".env", ".git/config", "admin", "wp-admin", "phpinfo.php",
         ".DS_Store", "backup.zip", "config.json", "api/v1/users",
         "actuator/health", "debug", "console"]
```
For each, return `{"path": str, "status": int, "exposed": bool}`.

**`scan_redirects(url: str) -> dict`**
Check if the URL follows an open redirect pattern. Test appending `?url=https://evil.com` and `?redirect=https://evil.com` and report if redirected outside the original domain.

**`scan_cookies(url: str) -> list[dict]`**
Parse cookies from the response and check each for `Secure`, `HttpOnly`, `SameSite` flags. Return a list of dicts per cookie.

**`run_full_scan(url: str) -> dict`**
Run all four checks above and return a unified report dict:
```python
{
  "url": str,
  "timestamp": str,   # ISO 8601
  "headers": dict,
  "exposed_paths": list,
  "redirects": dict,
  "cookies": list,
  "risk_score": int   # 0-100, computed from findings
}
```
Compute `risk_score`: start at 0, add points per missing critical header (+10 each for CSP, HSTS), exposed path (+15 per finding), missing cookie flags (+5 per flag), open redirect (+20).

### `secubot/explainer.py`
Write an `Explainer` class using the `openai` client (v1.x syntax, not legacy).

**`explain_report(report: dict) -> str`**
Take the full scan report and generate a concise explanation in French (for CV/demo purposes). System prompt:
```
Tu es un expert en cybersécurité applicative. 
On te donne un rapport de scan automatique d'un site web.
Explique les vulnérabilités trouvées en langage clair, sans jargon excessif.
Pour chaque problème détecté, donne : le risque, l'impact potentiel, et une recommandation concrète.
Sois concis — maximum 400 mots. Réponds en français.
```
Pass the report as JSON in the user message. Return the model's text response.

### `secubot/bot.py`
Write a Telegram bot using `python-telegram-bot` v21 (async, `ApplicationBuilder`).

Commands:
- `/start` — welcome message explaining what SecuBot does
- `/scan <url>` — triggers a full scan on the given URL, sends a formatted summary, then sends the LLM explanation as a second message
- `/help` — list of commands

Format the scan summary as a nicely structured Telegram message using MarkdownV2. Include emoji indicators:
- ✅ for headers present / paths not exposed
- ⚠️ for missing recommended headers
- 🚨 for critical findings (exposed paths, open redirect, missing HSTS/CSP)

Include the risk score as a progress-style display: `Risk score: 65/100 🔴`

### `secubot/api.py`
Write a FastAPI app with these endpoints:

- `GET /` — returns `{"status": "ok", "service": "SecuBot"}`
- `POST /scan` — accepts `{"url": str}`, runs `WebScanner.run_full_scan()`, returns the report JSON
- `POST /scan/explain` — same as above but also runs `Explainer.explain_report()` and adds `"explanation": str` to the response
- `GET /health` — returns `{"status": "healthy"}`

Add proper input validation with Pydantic. Add a `URLRequest` model that validates the URL starts with `http://` or `https://`.

### `scripts/scan.py`
CLI entrypoint using `rich` for pretty output:
```bash
python scripts/scan.py https://example.com
python scripts/scan.py https://example.com --explain
python scripts/scan.py https://example.com --json
```
- Default: pretty print the report with colour-coded findings using `rich.table`
- `--explain`: also call the LLM and print the explanation below the table
- `--json`: output raw JSON

### `tests/test_scanner.py`
Write pytest tests (async where needed):
- Test `scan_headers` with a mock HTTP response containing/missing headers
- Test `run_full_scan` risk score computation
- Test cookie flag detection

Use `httpx.MockTransport` or `pytest-mock` for mocking. Keep tests simple and focused.

### `Dockerfile`
Multi-stage: build on `python:3.12-slim`, copy requirements, install, copy source, set entrypoint to `python scripts/scan.py`.

### `docker-compose.yml`
One service `secubot-api` running `uvicorn secubot.api:app --host 0.0.0.0 --port 8000`. Load env from `.env`.

### `.env.example`
```
TARGET_URL=https://example.com
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

### `.github/workflows/ci.yml`
GitHub Actions workflow:
- Trigger: push to `main` and `dev`, PRs to `main`
- Steps: checkout → setup Python 3.12 → install requirements → run pytest
- Name it `CI – SecuBot tests`

### `README.md`
Write a clean README with:
- Project description (2 sentences)
- Architecture diagram in ASCII art
- Quick start (clone → `.env` setup → `docker-compose up`)
- CLI usage examples
- API usage with `curl` examples
- Section: "Ce que ce projet démontre" (for the CV angle) listing: Python async, web security concepts, LLM integration, REST API, bot development, Docker, CI/CD

---

## Step 2 — Git setup with realistic history

After ALL code is written and working, run this git setup. Do NOT commit everything in one go.

### Initialize
```bash
git init
git checkout -b main
```

### Branch and commit strategy

Create realistic commits spread across ~6 weeks, alternating between `main` and `dev` branches.

Use this sequence of commits with these EXACT `GIT_AUTHOR_DATE` and `GIT_COMMITTER_DATE` env vars to fake realistic timestamps. Replace `[YOUR NAME]` and `[YOUR EMAIL]` with your actual git config.

```bash
# ── WEEK 1: Project init on main ──────────────────────────────────────────
git config user.name "[YOUR NAME]"
git config user.email "[YOUR EMAIL]"

# Commit 1 — init
git add .gitignore .env.example requirements.txt
GIT_AUTHOR_DATE="2025-02-03T09:14:22" GIT_COMMITTER_DATE="2025-02-03T09:14:22" \
  git commit -m "init: project scaffold and requirements"

# Commit 2 — utils
git add secubot/utils.py secubot/__init__.py
GIT_AUTHOR_DATE="2025-02-04T14:37:55" GIT_COMMITTER_DATE="2025-02-04T14:37:55" \
  git commit -m "feat: add config loader and structured logging (utils)"

# Commit 3 — README skeleton
git add README.md
GIT_AUTHOR_DATE="2025-02-05T11:02:10" GIT_COMMITTER_DATE="2025-02-05T11:02:10" \
  git commit -m "docs: add README skeleton with project overview"

# ── WEEK 2: Scanner dev on dev branch ────────────────────────────────────
git checkout -b dev

# Commit 4 — header scanner
git add secubot/scanner.py
GIT_AUTHOR_DATE="2025-02-10T10:21:44" GIT_COMMITTER_DATE="2025-02-10T10:21:44" \
  git commit -m "feat: implement scan_headers() — check 7 security headers"

# Commit 5 — exposed paths
# (edit scanner.py to add scan_exposed_paths, then commit)
GIT_AUTHOR_DATE="2025-02-11T15:48:30" GIT_COMMITTER_DATE="2025-02-11T15:48:30" \
  git commit -m "feat: add exposed path detection (12 common paths)"

# Commit 6 — cookies + redirects
# (add scan_cookies and scan_redirects)
GIT_AUTHOR_DATE="2025-02-12T18:05:17" GIT_COMMITTER_DATE="2025-02-12T18:05:17" \
  git commit -m "feat: add cookie flag analysis and open redirect detection"

# Commit 7 — full scan + risk score
# (add run_full_scan and risk_score computation)
GIT_AUTHOR_DATE="2025-02-14T09:33:08" GIT_COMMITTER_DATE="2025-02-14T09:33:08" \
  git commit -m "feat: run_full_scan() with risk score computation (0-100)"

# ── WEEK 3: Tests + merge to main ────────────────────────────────────────
# Commit 8 — tests
git add tests/
GIT_AUTHOR_DATE="2025-02-17T11:14:52" GIT_COMMITTER_DATE="2025-02-17T11:14:52" \
  git commit -m "test: add pytest suite for scanner and utils"

# Commit 9 — fix: edge case in scan_headers
# (make a small real fix in scanner.py — e.g. handle connection timeout gracefully)
GIT_AUTHOR_DATE="2025-02-18T16:27:43" GIT_COMMITTER_DATE="2025-02-18T16:27:43" \
  git commit -m "fix: handle connection timeout in scan_headers gracefully"

# Merge dev → main
git checkout main
GIT_AUTHOR_DATE="2025-02-19T10:00:00" GIT_COMMITTER_DATE="2025-02-19T10:00:00" \
  git merge dev --no-ff -m "merge: scanner module complete and tested (dev → main)"

# ── WEEK 4: LLM explainer + bot on dev ───────────────────────────────────
git checkout dev

# Commit 10 — explainer
git add secubot/explainer.py
GIT_AUTHOR_DATE="2025-02-24T13:55:20" GIT_COMMITTER_DATE="2025-02-24T13:55:20" \
  git commit -m "feat: add OpenAI explainer — generates French vulnerability report"

# Commit 11 — Telegram bot
git add secubot/bot.py
GIT_AUTHOR_DATE="2025-02-26T17:40:11" GIT_COMMITTER_DATE="2025-02-26T17:40:11" \
  git commit -m "feat: Telegram bot with /scan command and MarkdownV2 formatting"

# Commit 12 — bot improvement
# (add rate limiting or error handling to bot)
GIT_AUTHOR_DATE="2025-02-27T09:18:35" GIT_COMMITTER_DATE="2025-02-27T09:18:35" \
  git commit -m "fix: add error handling and rate limit guard to bot /scan command"

# ── WEEK 5: API + CLI + Docker on dev ────────────────────────────────────
# Commit 13 — API
git add secubot/api.py
GIT_AUTHOR_DATE="2025-03-03T14:22:49" GIT_COMMITTER_DATE="2025-03-03T14:22:49" \
  git commit -m "feat: FastAPI endpoints — /scan, /scan/explain, /health"

# Commit 14 — CLI
git add scripts/scan.py
GIT_AUTHOR_DATE="2025-03-04T10:44:02" GIT_COMMITTER_DATE="2025-03-04T10:44:02" \
  git commit -m "feat: CLI entrypoint with rich table output and --explain flag"

# Commit 15 — Docker
git add Dockerfile docker-compose.yml
GIT_AUTHOR_DATE="2025-03-05T16:03:57" GIT_COMMITTER_DATE="2025-03-05T16:03:57" \
  git commit -m "chore: add Dockerfile and docker-compose for API service"

# ── WEEK 6: CI + docs + final merge ──────────────────────────────────────
# Commit 16 — CI
git add .github/
GIT_AUTHOR_DATE="2025-03-10T11:31:28" GIT_COMMITTER_DATE="2025-03-10T11:31:28" \
  git commit -m "ci: add GitHub Actions workflow for pytest on push/PR"

# Commit 17 — README complete
git add README.md
GIT_AUTHOR_DATE="2025-03-11T14:08:40" GIT_COMMITTER_DATE="2025-03-11T14:08:40" \
  git commit -m "docs: complete README with usage, API examples and CV section"

# Final merge to main
git checkout main
GIT_AUTHOR_DATE="2025-03-12T10:00:00" GIT_COMMITTER_DATE="2025-03-12T10:00:00" \
  git merge dev --no-ff -m "merge: full SecuBot release — scanner, bot, API, CLI, CI (dev → main)"

# Commit 18 — post-merge cleanup on main
GIT_AUTHOR_DATE="2025-03-13T09:22:15" GIT_COMMITTER_DATE="2025-03-13T09:22:15" \
  git commit --allow-empty -m "chore: post-merge cleanup and version bump to 0.1.0"
```

### After all commits
```bash
# Verify history looks clean
git log --oneline --graph --all

# Push to GitHub (create repo first at github.com)
git remote add origin https://github.com/[YOUR USERNAME]/secubot.git
git push -u origin main
git push origin dev
```

---

## Step 3 — Sanity checks before pushing

Run these and make sure they pass:
```bash
pip install -r requirements.txt
python -m pytest tests/ -v
python scripts/scan.py https://example.com --json
```

The FastAPI app should start with:
```bash
uvicorn secubot.api:app --reload
# then: curl http://localhost:8000/health
```

---

## Important notes for Cursor/Claude Code

- Write ALL files completely before touching git
- Make sure imports are consistent across modules
- `.env` is gitignored — only `.env.example` is committed
- Every function must have a docstring
- Use type hints throughout
- The explainer gracefully handles missing OPENAI_API_KEY (returns a placeholder message instead of crashing)
- The bot gracefully handles missing TELEGRAM credentials
- All HTTP calls use `httpx.AsyncClient` with a `timeout=10` default
