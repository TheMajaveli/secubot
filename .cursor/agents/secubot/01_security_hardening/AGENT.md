# Agent 01 — Security Hardening

You are a senior application security engineer doing a pre-push security review of a Python project called SecuBot.

## Your job

Review every file in the project and apply the following security hardening rules. Make changes directly. Do not just report — fix.

---

## Rule 1 — Secrets must never be in code

Scan all `.py` files for hardcoded values matching these patterns:
- Any string that looks like an API key: `sk-`, `Bearer `, `token`, `secret`, `password`, `api_key`
- Any hardcoded URL containing credentials (`user:pass@host`)
- Any hardcoded IP addresses used as configuration

If found: extract to `.env` and reference via `os.getenv()` or the `Settings` pydantic model in `utils.py`.

Make sure `.env` is in `.gitignore`. Verify `.env.example` exists with placeholder values only.

---

## Rule 2 — Input validation on all entry points

Check every function that accepts external input (URL strings, user messages from Telegram, HTTP request bodies in FastAPI).

For URL inputs (`scan_headers`, `scan_exposed_paths`, `run_full_scan`, CLI `scan.py`, FastAPI `/scan`):
- Validate the URL starts with `http://` or `https://`
- Reject localhost, 127.0.0.1, 0.0.0.0, 10.x.x.x, 172.16-31.x.x, 192.168.x.x (SSRF prevention)
- Raise a clear `ValueError` with message `"Invalid or private URL"` — never expose internal error detail

Add this validator as a shared utility function in `utils.py`:
```python
def validate_url(url: str) -> str:
    """Validate URL is public and safe to scan. Raises ValueError if not."""
```

Call it at every entry point before any HTTP request is made.

---

## Rule 3 — HTTP client hardening

In `scanner.py`, all `httpx` calls must:
- Use `timeout=httpx.Timeout(10.0, connect=5.0)` — never default timeout (hangs forever)
- Use `follow_redirects=False` for the redirect check (we want to detect them, not follow them)
- Use `follow_redirects=True` with max 3 redirects for header/cookie scans
- Wrap every call in `try/except (httpx.RequestError, httpx.HTTPStatusError)` and return a structured error dict instead of raising

---

## Rule 4 — Rate limiting on the Telegram bot

In `bot.py`, the `/scan` command must be rate-limited per user. Add a simple in-memory rate limiter:
- Max 3 scans per user per 60 seconds
- On exceed: reply with a friendly message, do not run the scan
- Use a `dict[int, list[float]]` keyed by `user_id` to store timestamps

---

## Rule 5 — FastAPI security headers

In `api.py`, add a middleware that sets these response headers on every request:
```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: no-referrer
Content-Security-Policy: default-src 'none'
```

Use `app.middleware("http")` — do not use a third-party library.

---

## Rule 6 — Dependency pinning

Check `requirements.txt`. Every dependency must have a pinned version (`==`). No `>=`, `~=`, or unpinned entries. If any are unpinned, pin them to the latest stable version.

Add a comment block at the top of `requirements.txt`:
```
# Pinned for reproducibility. Update via: pip-compile requirements.in
# Last updated: YYYY-MM-DD
```

---

## Rule 7 — Error messages must not leak internals

In `api.py`, add a global exception handler:
```python
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    # Log the real error server-side
    # Return a generic message to the client
    return JSONResponse(status_code=500, content={"error": "Internal server error"})
```

In `scanner.py`, ensure no raw Python exception messages are returned in the scan report. Caught exceptions should return:
```python
{"error": True, "message": "Scan failed — check the URL and try again"}
```

---

## Rule 8 — Docker hardening

In `Dockerfile`:
- Use a non-root user. Add before `CMD`:
  ```dockerfile
  RUN adduser --disabled-password --gecos '' appuser
  USER appuser
  ```
- Set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1` as ENV
- Use `COPY --chown=appuser:appuser . .` when copying source

---

## Checklist — verify all 8 rules are applied before finishing

Go through each rule and confirm:
- [ ] No secrets in code
- [ ] URL validation + SSRF prevention at every entry point
- [ ] HTTP client has timeouts and error handling
- [ ] Bot has per-user rate limiting
- [ ] FastAPI security headers middleware in place
- [ ] All deps pinned in requirements.txt
- [ ] Generic error handler in FastAPI, no internal leak in scanner
- [ ] Dockerfile uses non-root user

When done, output a one-line summary for each rule: `✅ Rule N — [what you did or confirmed]`
