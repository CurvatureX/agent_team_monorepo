# Repository Guidelines

## Project Structure & Module Organization
The monorepo uses `apps/` for deployable services. Backend FastAPI apps live in `apps/backend` (`api-gateway`, `workflow_engine`, `workflow_scheduler`, `workflow_agent`). The Next.js frontend is in `apps/frontend/agent_team_web`, and internal tools sit in `apps/internal-tools` (`docusaurus-doc`, `node-knowledge-uploader`). Demo workflows are under `apps/demo_apps`, while infrastructure assets reside in `infra` and helper scripts in `scripts`. Shared docs live in `docs`, and Supabase config, migrations, and seeds are under `supabase`. Tests stay close to code inside each app (`tests/`, `__tests__/`).

## Build, Test, and Development Commands
Use `uv sync && uv run uvicorn app.main:app --reload` in `apps/backend/api-gateway` for local API development. Run backend unit tests with `uv run pytest -v --cov`. Execute workflow integration coverage via `bash run_integration_tests.sh`. For the web app, run `npm install && npm run dev` inside `apps/frontend/agent_team_web`. Internal tooling tests run from `apps/internal-tools/node-knowledge-uploader` with `npm install && npm test`. Supabase services start with `npm run supabase` or `./scripts/supabase-migrate.sh`. Install pre-commit hooks and lint everything by running `pre-commit install && pre-commit run --all-files`.

## Coding Style & Naming Conventions
Python code is formatted by Black (line length 100) and isort, with 4-space indents, snake_case modules and functions, PascalCase classes, and explicit type hints. TypeScript/React follows the repo ESLint config, PascalCase components, camelCase hooks/variables, and collocated UI in `src/components`. File naming follows `snake_case.py` for Python, `ComponentName.tsx` for React, and tests named `test_*.py` or `*.test.ts(x)`.

## Testing Guidelines
Backends rely on pytest with pytest-asyncio and pytest-cov; frontends and Node tools use Jest. Generate coverage with `--cov` flags and commit coverage.xml artifacts. Target new tests for changed code paths and keep fixtures local. Integration flows should assert API contracts via the provided script.

## Commit & Pull Request Guidelines
Write concise, imperative commit messages; conventional prefixes like `feat:` or `fix:` keep history scannable. PRs should link issues, describe scope and risk, include UI screenshots when relevant, and attach a test plan listing commands and expected results. Clean up feature toggles and temporary logging before requesting review.

## Security & Configuration Tips
Never commit secrets; rely on `.env.example` files in each app and `supabase/.env`. Scrub sensitive data from logs and rotate sample keys after demos. When deploying backend Docker, bump `VERSION` in `apps/backend/.env` (e.g., `dev-20240214-0900`) so the running service advertises the build.

## Agent-Specific Instructions
Before editing submodules, look for nested `AGENTS.md` files and follow the most specific guidance provided there. Raise questions in the relevant README if instructions conflict.
