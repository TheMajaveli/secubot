# Agent 03 — Test Coverage

You are a senior Python engineer responsible for test coverage on SecuBot before it gets pushed to GitHub.

## Your job

Write and/or complete the test suite in `tests/`. Tests must be runnable with `pytest` with no environment variables required (all network calls must be mocked).

---

## Setup requirements

Add these to `requirements.txt` if not already there (pinned):
```
pytest==8.2.0
pytest-asyncio==0.23.7
pytest-mock==3.14.0
respx==0.21.1
```

Create `pytest.ini` at the project root:
```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

---

## Tests to write

### `tests/test_scanner.py`

Use `respx` to mock all `httpx` calls. Never make real HTTP requests in tests.

```python
import pytest
import respx
import httpx
from secubot.scanner import WebScanner

scanner = WebScanner()
```

**Test 1 — `scan_headers`: all headers present**
Mock a response with all 7 security headers set. Assert every header has `present=True` and the correct value.

**Test 2 — `scan_headers`: missing headers**
Mock a response with no security headers. Assert all 7 have `present=False` and `value=None`.

**Test 3 — `scan_headers`: connection timeout**
Use `respx` to raise `httpx.ConnectTimeout`. Assert the function returns `{"error": True, ...}` instead of raising.

**Test 4 — `scan_exposed_paths`: exposed `.env`**
Mock `GET /.env` to return 200, all others to return 404. Assert exactly one item in result with `exposed=True` and `path=".env"`.

**Test 5 — `scan_exposed_paths`: nothing exposed**
Mock all paths to return 404. Assert no items have `exposed=True`.

**Test 6 — `scan_cookies`: secure flags present**
Mock a response with `Set-Cookie: session=abc; Secure; HttpOnly; SameSite=Strict`. Assert the cookie analysis shows all flags present.

**Test 7 — `scan_cookies`: flags missing**
Mock a response with `Set-Cookie: session=abc` (no flags). Assert `secure=False`, `http_only=False`, `same_site=None`.

**Test 8 — `run_full_scan`: risk score computation**
Mock responses such that: CSP missing (+15), HSTS missing (+15), one exposed path (+15), open redirect (+20). Assert `risk_score == 65`.

**Test 9 — `run_full_scan`: perfect score**
Mock responses with all headers present, no exposed paths, no redirect, cookies with all flags. Assert `risk_score == 0`.

**Test 10 — `run_full_scan`: report structure**
Assert the returned dict contains all required keys: `url`, `timestamp`, `headers`, `exposed_paths`, `redirects`, `cookies`, `risk_score`.

---

### `tests/test_utils.py`

```python
from secubot.utils import validate_url
import pytest
```

**Test 11 — valid public URLs pass**
```python
@pytest.mark.parametrize("url", [
    "https://example.com",
    "http://example.com",
    "https://sub.example.com/path?q=1",
])
def test_valid_urls(url):
    assert validate_url(url) == url
```

**Test 12 — private/local URLs rejected**
```python
@pytest.mark.parametrize("url", [
    "http://localhost",
    "http://127.0.0.1",
    "http://0.0.0.0",
    "http://192.168.1.1",
    "http://10.0.0.1",
    "http://172.16.0.1",
])
def test_private_urls_rejected(url):
    with pytest.raises(ValueError, match="Invalid or private URL"):
        validate_url(url)
```

**Test 13 — non-HTTP schemes rejected**
```python
@pytest.mark.parametrize("url", [
    "ftp://example.com",
    "file:///etc/passwd",
    "javascript:alert(1)",
    "just-a-string",
    "",
])
def test_bad_schemes_rejected(url):
    with pytest.raises(ValueError):
        validate_url(url)
```

---

### `tests/test_api.py`

Use FastAPI's `TestClient` (synchronous) for API tests. Do not mock the scanner here — mock the scanner's methods using `pytest-mock`.

```python
from fastapi.testclient import TestClient
from secubot.api import app

client = TestClient(app)
```

**Test 14 — GET `/` returns ok**
```python
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

**Test 15 — GET `/health` returns healthy**

**Test 16 — POST `/scan` with valid URL calls scanner**
Mock `WebScanner.run_full_scan` to return a fixture report dict. Assert response is 200 and contains `risk_score`.

**Test 17 — POST `/scan` with invalid URL returns 422 or 400**
Send `{"url": "not-a-url"}`. Assert response status is 422 (Pydantic validation) or 400 (custom validator).

**Test 18 — POST `/scan` with private URL returns 400**
Send `{"url": "http://localhost"}`. Assert 400.

**Test 19 — Security headers present on all responses**
After any request, assert these headers are in the response:
```python
assert response.headers["x-content-type-options"] == "nosniff"
assert response.headers["x-frame-options"] == "DENY"
```

---

## How to run

After writing all tests, run:
```bash
pytest tests/ -v --tb=short
```

All 19 tests must pass with exit code 0. If any fail, fix the test OR the source code (whichever is wrong) and re-run.

At the end, output:
```
Tests written: 19
Tests passing: X/19
```
