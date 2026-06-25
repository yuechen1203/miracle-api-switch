# Repository Guidelines

## Project Structure & Module Organization

This repository hosts the Miracle API Switch tool, a local utility for managing Codex and Claude Code provider configurations and an in-process format-conversion proxy.

- `back-app/` Python FastAPI backend (`app/api`, `app/core`, `app/services`, `app/proxy`, `tests`).
- `front-app/` Vue 3 + Vite + TypeScript frontend (`src/api`, `src/components`, `src/layouts`, `src/router`, `src/stores`, `src/styles`, `src/types`, `src/utils`, `src/views`).
- `docs/` product, frontend, and backend design documents.
- `front-app/backend-contract-notes.md` backend contract that the frontend must honor.
- `scripts/start.sh`, `scripts/stop.sh` one-shot dev runners for the whole stack.
- `python3/` repo-local Python 3.11 toolchain. Do not modify.
- `config.toml`, `settings.json` sample agent configuration files used as fixtures.
- `.hyc_cache/` runtime cache directory created by the backend, never commit.
- `.runtime/` logs and PIDs created by `scripts/start.sh`, never commit.

## Build, Test, and Development Commands

One-shot stack (recommended for local dev):

```bash
./scripts/start.sh --host <server-ip>             # start backend + frontend in background
./scripts/stop.sh                                 # stop processes started by start.sh
./scripts/start.sh --host <server-ip> --reinstall # force reinstall backend pip + frontend npm deps
```

`scripts/start.sh` intentionally refuses `127.*`, `localhost`, and `0.0.0.0`. Use the server's real network-interface IP so remote access must go through `http://<server-ip>:5173`, not localhost port forwarding.

Backend only:

```bash
cd back-app
../python3/bin/python3 -m pip install -r requirements.txt
../python3/bin/python3 -m pytest
MIRACLE_WORKSPACE_DIR="$(pwd)/.." ../python3/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Frontend only:

```bash
cd front-app
npm install
npm run dev          # local-only Vite dev server on 127.0.0.1:5173
npm run typecheck    # vue-tsc --noEmit
npm run build        # production bundle to front-app/dist
```

## Coding Style & Naming Conventions

Backend targets Python 3.11+. Use 4-space indentation, type hints on public functions, and Pydantic models for API payloads. Keep route handlers thin; put business logic in `app/services/` or `app/proxy/`. Use `snake_case` for modules, functions, variables, and tests. Keep API responses in the unified `{success, data, error, request_id}` envelope.

Frontend uses 2-space indentation, `PascalCase.vue` for components, `camelCase` for variables and store actions, and shared design tokens from `src/styles/base.css`. Stick to one accent color, the existing radius scale (4 / 6 / 8 / 12), and Lucide icons via `lucide-vue-next`. Do not add a UI component library without discussion.

## Testing Guidelines

Backend tests use `pytest` under `back-app/tests/`. Name files `test_*.py` and functions `test_*`. Run via `../python3/bin/python3 -m pytest`. Prefer temporary directories and `MIRACLE_WORKSPACE_DIR` over writing into real user paths. The frontend has no automated test suite yet; rely on `npm run typecheck` and manual checks against a running backend before merging.

## Commit & Pull Request Guidelines

The directory currently has no Git history. Use concise imperative commit messages such as `Add provider validation tests` or `Fix Claude settings writer`. PRs should include a short summary, test or typecheck results, screenshots for visible frontend changes, and updates to `front-app/backend-contract-notes.md` whenever backend behavior shifts.

## Security & Configuration Tips

Never commit real API keys, `.hyc_cache/`, `.runtime/`, virtual environments, `node_modules/`, or build output. Provider responses must keep masking secrets. Local proxy URLs are always `http://127.0.0.1:{port}`; do not switch to HTTPS without a follow-up design discussion. Use `MIRACLE_WORKSPACE_DIR` during local development to scope cache and config writes to the repository workspace.
