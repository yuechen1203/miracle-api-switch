# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Miracle API Switch is a local tool for managing Codex and Claude Code provider configurations and running an in-process API format-conversion proxy. The repository is split into:

- `back-app/`: Python 3.11+ FastAPI backend.
- `front-app/`: Vue 3 + Vite + TypeScript frontend.
- `docs/`: product/backend/frontend design notes.
- `front-app/backend-contract-notes.md`: frontend/backend contract details.
- `scripts/start.sh` and `scripts/stop.sh`: one-shot dev runners for the full stack.
- `python3/`: repo-local Python 3.11 toolchain; do not modify.

Runtime state lives in `.hyc_cache/` and `.runtime/`. Keep these, local virtualenvs, `node_modules/`, build output, and real secrets out of commits.

## Common commands

### Whole stack

```bash
./scripts/start.sh --host <server-ip>
./scripts/stop.sh
./scripts/start.sh --host <server-ip> --reinstall
```

`start.sh` starts the backend on port `8765` and frontend on port `5173`, writing logs/PIDs under `.runtime/`. It intentionally rejects `127.*`, `localhost`, `0.0.0.0`, and `::1`; use a real network-interface IP for remote access.

### Backend

```bash
cd back-app
../python3/bin/python3 -m pip install -r requirements.txt
../python3/bin/python3 -m pytest
MIRACLE_WORKSPACE_DIR="$(pwd)/.." ../python3/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8765
```

Run a single backend test:

```bash
cd back-app
../python3/bin/python3 -m pytest tests/test_api.py::test_api_create_provider_and_dry_run_apply
```

Backend tests are configured by `pyproject.toml` with `testpaths = ["tests"]` and `pythonpath = ["."]`. No separate backend lint command is currently configured.

### Frontend

```bash
cd front-app
npm install
npm run dev
npm run typecheck
npm run build
npm run preview
```

Override the backend target for Vite's `/api` proxy:

```bash
cd front-app
VITE_API_TARGET=http://<server-ip>:8765 npm run dev
```

The frontend currently has no automated test suite; use `npm run typecheck` and manual checks against a running backend.

## Backend architecture

The FastAPI app is assembled in `back-app/app/main.py`. It configures local CORS origins, request IDs, unified response/error envelopes, and includes API routes from `app/api/routes.py`.

`back-app/app/app_context.py` wires the backend services together: `CacheStore`, `AgentProbeService`, `UsageService`, `ProxyManager`, `ConfigWriter`, and `ProviderService`. Proxies are stopped on app shutdown.

Key backend areas:

- `app/models.py`: Pydantic models and enums for agents (`codex`, `claude_code`), providers, target formats, agent statuses, proxy statuses, and usage.
- `app/core/config.py`: version and workspace/cache resolution; `MIRACLE_WORKSPACE_DIR` overrides the workspace root.
- `app/core/responses.py`: unified `{success, data, error, request_id}` response envelope helpers.
- `app/core/security.py`: API-key masking and sensitive-field scrubbing.
- `app/services/cache_store.py`: `.hyc_cache` JSON files, backups, atomic writes, and private permissions.
- `app/services/agent_probe.py`: path resolution/status probing for Codex `config.toml` and Claude Code `settings.json`.
- `app/services/provider_service.py`: provider CRUD, uniqueness/conflict handling, config checks, apply flow, and manual snapshot/restore.
- `app/services/config_writer.py`: dry-run previews, backups, and writes to Codex TOML / Claude Code JSON configs.
- `app/services/usage_service.py`: token usage normalization, accumulation, listing, and reset.
- `app/proxy/manager.py`: per-provider local FastAPI proxy launched in a uvicorn thread, always bound to `127.0.0.1`.
- `app/proxy/transformers.py`: conversions between `responses`, `messages`, and `chat/completions`, including basic SSE/tool-call mapping.

All business APIs should preserve the unified response envelope. Route handlers should remain thin; put behavior in `app/services/` or `app/proxy/`.

## Frontend architecture

The frontend is Vue 3 + Vite + TypeScript with Pinia and Vue Router. `front-app/src/main.ts` creates the app, installs Pinia/router, and loads global CSS. `front-app/src/App.vue` performs initial health/load work and runs 10-second polling for provider/config/usage state.

Key frontend areas:

- `src/api/client.ts`: axios client using same-origin `/api`, unwraps backend envelopes, and throws `BackendError` based on `error.code`.
- `src/types/api.ts`: TypeScript shapes for backend API contracts.
- `src/router/index.ts`: hash routes for `/`, `/agents/codex`, `/agents/claude-code`, and `/settings`.
- `src/stores/app.ts`: health, online state, and toast notifications.
- `src/stores/agents.ts`: agent status and config checks.
- `src/stores/providers.ts`: provider CRUD, apply, proxy controls, and API key reveal.
- `src/stores/usage.ts`: token usage loading/reset.
- `src/views/DashboardView.vue`: two-agent overview, config drawer, usage reset.
- `src/views/AgentView.vue`: provider table, config-check panel, provider form drawer, apply/delete modals, proxy controls, and API-key reveal.
- `src/views/SettingsView.vue`: backend/cache info, usage overview, and security notes.
- `src/layouts/AppShell.vue`: top bar, navigation, backend offline banner, and running proxy count.

Frontend components are self-built; do not add a UI component library without discussion. Use shared design tokens from `src/styles/base.css`, Lucide icons via `lucide-vue-next`, `PascalCase.vue` component names, and 2-space indentation.

## Data and config flow

- Workspace root defaults to the repository root; set `MIRACLE_WORKSPACE_DIR` to scope backend cache/config writes during local development.
- Backend cache files live under `.hyc_cache/`, including `agents.json`, per-agent provider files, `proxies.json`, per-agent usage files, `manual_config_snapshots.json`, and `backups/`.
- Agent config path rules:
  - Codex expects `config.toml`.
  - Claude Code expects `settings.json`.
  - A directory input appends the expected filename; a file input must use the expected filename.
- Applying a provider should be a dry-run-first flow in the frontend. `dry_run=true` previews fields without writing config or starting proxy; real apply can start the proxy first, then write the agent config.
- Codex writes set `model_provider = "miracle"`, top-level `model`, and `[model_providers.miracle]` fields including `base_url`, `wire_api = "responses"`, and `experimental_bearer_token`.
- Claude Code writes update `env.ANTHROPIC_AUTH_TOKEN`, `env.ANTHROPIC_BASE_URL`, `ANTHROPIC_MODEL`, default Haiku/Sonnet/Opus fields, and `CLAUDE_CODE_SUBAGENT_MODEL` while preserving unrelated JSON fields.
- Local proxy URLs are always `http://127.0.0.1:{proxy_port}`. Usage is counted only for traffic that passes through a local proxy.
- Proxy conversion supports normal text and basic streaming/tool-call mapping; complex reasoning, multimodal content, vendor-specific tool fields, and fully lossless cross-format streaming are not guaranteed.

## Contract and safety notes

- Supported `agent_type` values are `codex` and `claude_code`.
- Frontend code should inspect backend `success` and `error.code`, not just HTTP status.
- Provider queries return masked key metadata (`has_api_key`, `api_key_masked`); full key reveal is a dedicated endpoint.
- In provider edit forms, an empty `api_key` means “keep existing key”; new providers require a key.
- Browsers cannot choose arbitrary local paths; collect paths as text and let the backend validate/probe them.
- API keys must stay masked in frontend responses and logs.
