# Repository Guidelines

## Project Structure & Module Organization
- `apps/backend/` — Python services (FastAPI): `api-gateway`, `workflow_engine`, `workflow_scheduler`, `workflow_agent`.
- `apps/frontend/agent_team_web` — Next.js web app.
- `apps/internal-tools/` — Docs (`docusaurus-doc`) and a Next.js tool (`node-knowledge-uploader`).
- `apps/demo_apps/` — Small demo workflows and examples.
- `infra/` — Terraform + deployment assets; `scripts/` — helper scripts.
- `supabase/` — local config, migrations, and seed data.
- `docs/` — product, tech, and development design docs.
- Tests live under each app (`tests/`, `__tests__/`).

## Build, Test, and Development Commands
- Python (uv) — API Gateway dev: `cd apps/backend/api-gateway && uv sync && uv run uvicorn app.main:app --reload`.
- Python tests: `uv run pytest -v --cov` (e.g., in `apps/backend/api-gateway`).
- Integration tests (API Gateway): `bash run_integration_tests.sh`.
- Frontend dev: `cd apps/frontend/agent_team_web && npm install && npm run dev`.
- Internal tool tests: `cd apps/internal-tools/node-knowledge-uploader && npm install && npm test`.
- Supabase CLI: `npm run supabase` (root) or `./scripts/supabase-migrate.sh`.
- Pre-commit: `pre-commit install && pre-commit run --all-files`.

## Local Docker Workflow (Backend)
- Always rebuild after code changes: `cd apps/backend && docker compose down && docker compose up --build`.
- Set a build version so you can verify deployment:
  - Edit `apps/backend/.env` and set `VERSION=dev-YYYYMMDD-HHMM`.
  - The API Gateway reads `VERSION` via settings; check it in Swagger (`/docs`, top-right shows version) or logs on startup.

## Coding Style & Naming Conventions
- Python: Black (line length 100) and isort via pre-commit; 4-space indent; snake_case for modules/functions, PascalCase for classes; add type hints. Type checking via `pyrightconfig.json` at repo root.
- TypeScript/React: ESLint (Next config). Use PascalCase for components, camelCase for variables/hooks; colocate UI pieces in `src/components/...`.
- File names: Python `snake_case.py`; React components `ComponentName.tsx`; tests as shown below.

## Testing Guidelines
- Frameworks: pytest (+pytest-asyncio, pytest-cov) for Python; Jest for Node/Next apps.
- Python tests under `tests/` named `test_*.py`; JS/TS tests in `__tests__/` or `*.test.ts(x)`.
- Coverage: generate with `--cov` (coverage.xml used in services). Focus on changed code paths.

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject; prefer Conventional Commits where sensible (e.g., `feat:`, `fix:`). History mixes “fix …” and merge commits — aim for clarity going forward.
- PRs: include scope and rationale, linked issues, screenshots for UI, and a test plan (commands + expected results).

## Security & Configuration Tips
- Do not commit secrets. Use env files: see `apps/*/.env.example`, `apps/frontend/agent_team_web/.env.local.example`, `supabase/.env`.
- Sanitize logs and rotate any test keys used locally.

## Agent-Specific Instructions
- Check for AGENTS.md in subfolders; follow the most specific file for code style or runbooks within that directory tree.
