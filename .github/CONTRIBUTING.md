# Contributing to shhecrets

Thanks for taking a look. shhecrets is a small, single-maintainer project, but PRs and issues are welcome — this doc just makes it clear how the pieces fit together.

## Project layout

- `backend/` — FastAPI app (Python). Redis holds the actual secret (TTL'd, deleted on read); MongoDB holds audit metadata only (never the secret or the key).
- `frontend/` — React + TypeScript (Vite). All encryption/decryption happens here, client-side, via the Web Crypto API.
- `infra/` — Docker Compose files (dev and prod) and the Caddy reverse proxy config.
- `scripts/` — operational scripts that run on the VPS via cron (backups, health checks), not part of the app itself.
- `cli/` — scaffolded, not yet implemented.

## Local development

```bash
cd infra
docker compose up -d --build
```

This runs the full stack (Redis, MongoDB, backend, frontend) against `http://localhost:8080`.

## Running tests

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Frontend:
```bash
cd frontend
npm install
npx tsc -b
npx vitest run
```

Shell scripts:
```bash
shellcheck scripts/*.sh
```

All four of these run automatically in CI on every pull request — a PR won't merge cleanly unless they pass.

## Making a change

1. Branch off `main`.
2. Keep PRs scoped to one logical change — the project's git history is intentionally granular (one concern per PR) rather than batched.
3. Write or update tests for anything behavior-affecting. `backend/tests/` and `frontend/src/**/*.test.ts` are the two suites.
4. Open a PR against `main`. CI must be green before merge.

## A few conventions worth knowing

- Comments explain *why*, not *what* — if a comment just restates the code, it probably shouldn't be there. Look at existing files for the tone.
- No dependency gets added without a reason tied to an actual requirement — this project deliberately avoids frameworks/libraries it doesn't need.
- Anything touching the encryption flow (`frontend/src/crypto/aesGcm.ts`) or the read-once guarantee (`backend/app/services/session_service.py`) is the most security-sensitive code in the repo — changes there deserve extra scrutiny and test coverage.

## Reporting bugs vs. security issues

Regular bugs: open a GitHub issue.
Security vulnerabilities: see `SECURITY.md` — please don't open a public issue for those.
