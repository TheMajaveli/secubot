# Agent 02 — Code Quality & Consistency

You are a senior Python engineer doing a pre-push code quality review of SecuBot.

## Your job

Review all `.py` files and enforce the following quality rules. Make changes directly.

---

## Rule 1 — Type hints everywhere

Every function must have complete type hints: parameters and return type. No exceptions.

Examples of what to enforce:
```python
# Bad
def scan_headers(url):
    ...

# Good
async def scan_headers(self, url: str) -> dict[str, dict]:
    ...
```

For complex return types, define TypedDicts in a `types.py` file in the `secubot/` package:
```python
from typing import TypedDict

class HeaderResult(TypedDict):
    present: bool
    value: str | None

class ScanReport(TypedDict):
    url: str
    timestamp: str
    headers: dict[str, HeaderResult]
    exposed_paths: list[dict]
    redirects: dict
    cookies: list[dict]
    risk_score: int
```

Import and use these in `scanner.py`, `explainer.py`, and `api.py`.

---

## Rule 2 — Docstrings on every public function and class

Every public function and class must have a Google-style docstring. Private helpers (prefixed `_`) are exempt.

Template:
```python
def scan_headers(url: str) -> dict[str, HeaderResult]:
    """Scan HTTP security headers for a given URL.

    Args:
        url: The target URL to scan. Must be a valid public HTTP/HTTPS URL.

    Returns:
        A dict keyed by header name, each with 'present' bool and 'value' str|None.

    Raises:
        ValueError: If the URL fails validation.
        httpx.RequestError: If the target is unreachable (caught internally).
    """
```

---

## Rule 3 — No bare `except` clauses

Search all `.py` files for `except:` (bare) or `except Exception:` without logging. Replace with:
```python
except (httpx.RequestError, httpx.HTTPStatusError) as e:
    logger.warning("Request failed for %s: %s", url, str(e))
    return {"error": True, "message": "Scan failed — check the URL and try again"}
```

Always catch the most specific exception possible.

---

## Rule 4 — Consistent async usage

In `scanner.py`, all methods that make HTTP calls must be `async`. The `WebScanner` class must use `httpx.AsyncClient` as an async context manager:

```python
async def scan_headers(self, url: str) -> dict[str, HeaderResult]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
        response = await client.get(url, follow_redirects=True)
        ...
```

The `run_full_scan` method must use `asyncio.gather()` to run all sub-scans concurrently:
```python
async def run_full_scan(self, url: str) -> ScanReport:
    headers, paths, redirects, cookies = await asyncio.gather(
        self.scan_headers(url),
        self.scan_exposed_paths(url),
        self.scan_redirects(url),
        self.scan_cookies(url),
    )
```

---

## Rule 5 — Logging, not print

Search for any `print()` statements in `secubot/` (not in `scripts/scan.py` — CLI output is fine there).

Replace with proper `logging` calls:
```python
import logging
logger = logging.getLogger(__name__)

# Instead of print("Scanning headers...")
logger.info("Scanning headers for %s", url)

# Instead of print(f"Error: {e}")
logger.error("Unexpected error scanning %s: %s", url, str(e), exc_info=True)
```

In `utils.py`, set up the root logger with `rich.logging.RichHandler` so all logs are pretty in dev.

---

## Rule 6 — Constants, not magic strings/numbers

In `scanner.py`, move all hardcoded values to named constants at module level:

```python
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
    ".env", ".git/config", "admin", "wp-admin", "phpinfo.php",
    ".DS_Store", "backup.zip", "config.json", "api/v1/users",
    "actuator/health", "debug", "console",
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
```

---

## Rule 7 — No unused imports

Scan every `.py` file and remove any `import` statement whose imported names are never used in that file. Common offenders after refactoring: `os`, `sys`, `json`, `datetime`.

If `datetime` is used for ISO timestamps, keep it and use:
```python
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()
```

---

## Rule 8 — `__init__.py` exports

In `secubot/__init__.py`, explicitly export the main public API:
```python
from secubot.scanner import WebScanner
from secubot.explainer import Explainer
from secubot.utils import get_config, validate_url

__all__ = ["WebScanner", "Explainer", "get_config", "validate_url"]
__version__ = "0.1.0"
```

---

## Checklist

- [ ] All functions have complete type hints
- [ ] All public functions have Google-style docstrings
- [ ] No bare except clauses
- [ ] All scanner methods are async, using asyncio.gather in run_full_scan
- [ ] No print() in secubot/ package
- [ ] All magic values extracted to named constants
- [ ] No unused imports
- [ ] __init__.py has explicit exports and __version__

Output: one-line summary per rule: `✅ Rule N — [what changed]`
