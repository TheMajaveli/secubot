# Agent 04 — Git Hygiene

You are a DevOps engineer preparing SecuBot for a clean, professional GitHub push.

## Your job

Run all the following steps in order. Do not skip any. This runs AFTER agents 01, 02, and 03 have completed.

---

## Step 1 — Verify `.gitignore` is complete

The `.gitignore` file must contain at minimum:

```gitignore
# Environment
.env
.env.local
.env.*.local

# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
.eggs/
*.egg

# Virtual envs
.venv/
venv/
env/

# Testing
.pytest_cache/
.coverage
htmlcov/
coverage.xml
*.coveragerc

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Docker
.dockerignore

# Distribution
*.tar.gz
*.zip
```

If any of these are missing, add them. Never commit `.env`.

---

## Step 2 — Verify no secrets are staged

Run this check and report the output:
```bash
git diff --cached --name-only
grep -rn "sk-\|api_key\s*=\s*['\"][^'\"]\|password\s*=\s*['\"][^'\"]" --include="*.py" --include="*.env" --include="*.json" . \
  --exclude-dir=".git" --exclude-dir=".venv" --exclude-dir="venv"
```

If any matches are found outside of `.env.example`, stop and report them. Do not proceed with the commit until they are removed.

---

## Step 3 — Run all quality checks

Run these commands in order. All must exit with code 0.

```bash
# 1. Syntax check all Python files
python -m py_compile secubot/utils.py secubot/scanner.py secubot/explainer.py secubot/bot.py secubot/api.py scripts/scan.py
echo "Syntax OK"

# 2. Run tests (mocked, no network required)
pytest tests/ -v --tb=short
echo "Tests OK"

# 3. Check for any remaining print() in the package
grep -rn "^\s*print(" secubot/ && echo "WARNING: print() found" || echo "No print() in package"

# 4. Check .env is not tracked
git ls-files .env && echo "ERROR: .env is tracked by git!" || echo ".env not tracked — OK"
```

If step 2 (tests) fails, diagnose the failure and fix it before continuing.

---

## Step 4 — Stage only the right files

Run:
```bash
git status
```

Then stage only the following files (do not use `git add .`):
```bash
git add \
  .gitignore \
  .env.example \
  requirements.txt \
  pytest.ini \
  Dockerfile \
  docker-compose.yml \
  README.md \
  secubot/__init__.py \
  secubot/utils.py \
  secubot/scanner.py \
  secubot/explainer.py \
  secubot/bot.py \
  secubot/api.py \
  secubot/types.py \
  scripts/scan.py \
  tests/__init__.py \
  tests/test_scanner.py \
  tests/test_utils.py \
  tests/test_api.py \
  .github/workflows/ci.yml
```

If any of these files don't exist yet, report them as missing and do not stage them.

Then verify nothing sensitive is staged:
```bash
git diff --cached --stat
```

---

## Step 5 — Verify branch state

Run:
```bash
git log --oneline --graph --all | head -30
git branch -a
```

Confirm:
- `main` branch exists and has the merge commits
- `dev` branch exists with feature commits
- No other branches exist (clean history)
- The most recent commit on `main` is the post-merge cleanup

If the commit graph looks wrong (all in one branch, squashed, wrong order), report it but do not attempt to rewrite history — flag it for manual review.

---

## Step 6 — Pre-push checklist output

Output a formatted checklist:

```
SecuBot — Pre-Push Checklist
──────────────────────────────────────────
[ ] .gitignore is complete
[ ] No secrets in tracked files
[ ] All Python files compile without errors
[ ] All 19 tests pass
[ ] No print() statements in secubot/ package
[ ] .env is NOT tracked by git
[ ] Only expected files are staged
[ ] main branch has merge commits
[ ] dev branch exists with feature history
──────────────────────────────────────────
Result: READY TO PUSH  /  BLOCKED — see issues above
```

Mark each item with ✅ or ❌ based on actual results.

---

## Step 7 — Push instructions (output only — do not run)

If the checklist is all ✅, output these exact commands for the user to run manually:

```bash
# Push both branches to GitHub
git push -u origin main
git push origin dev

# Verify on GitHub:
# 1. Go to github.com/[YOUR USERNAME]/secubot
# 2. Check both branches appear under the branch selector
# 3. Check the commit graph looks clean under Insights > Network
# 4. Confirm .env does NOT appear in any commit
```
