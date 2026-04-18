# SecuBot — Claude Code instructions

SecuBot is a Python web security scanner with a Telegram bot, FastAPI API, and OpenAI-powered French explanations.

## On every resume (read first)

1. Open [SECUBOT_PROGRESS.md](SECUBOT_PROGRESS.md). If it lists partial progress, **do not restart from scratch** — execute only the **Next step** line, then update the file.
2. Follow the pipeline order below.

## Pipeline order

1. **Build / extend code** per [SECUBOT_CURSOR_PROMPT.md](SECUBOT_CURSOR_PROMPT.md) if the app is incomplete.
2. **Agents** (in order; full playbooks under `.cursor/agents/secubot/`):
   - `01_security_hardening/AGENT.md`
   - `02_code_quality/AGENT.md`
   - `03_test_coverage/AGENT.md`
   - `04_git_hygiene/AGENT.md` (requires local git)
   - `05_docs_polish/AGENT.md`

## Verification

```bash
pip install -r requirements.txt
python -m pytest tests/ -v --tb=short
python scripts/scan.py https://example.com --json
```

API (optional): `uvicorn secubot.api:app --reload` then `curl -s http://127.0.0.1:8000/health`.

## Fixed resume prompt (paste into Claude Code)

You are continuing SecuBot work. Read `SECUBOT_PROGRESS.md` and do only the **Next step** listed there. Follow `CLAUDE.md` for pipeline order and paths. After each logical chunk, update `SECUBOT_PROGRESS.md` and run the verification command for the current phase.
