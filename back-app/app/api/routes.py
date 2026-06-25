from __future__ import annotations

from fastapi import APIRouter, Request

from app.app_context import AppContext
from app.core.config import APP_NAME, APP_VERSION
from app.core.responses import ok
from app.models import ApplyProviderRequest, ConfigPathRequest, ProviderCreate, ProviderUpdate

router = APIRouter(prefix="/api")


def get_context(request: Request) -> AppContext:
    return request.app.state.ctx


@router.get("/health")
async def health(request: Request):
    ctx = get_context(request)
    return ok(
        {
            "name": APP_NAME,
            "version": APP_VERSION,
            "status": "ok",
            "started_at": ctx.started_at,
            "workspace_root": str(ctx.cache.workspace_root),
            "cache_dir": str(ctx.cache.cache_dir),
        },
        request,
    )


@router.get("/agents")
async def list_agents(request: Request):
    ctx = get_context(request)
    return ok(ctx.agent_probe.list_agents(), request)


@router.get("/agents/{agent_type}")
async def get_agent(agent_type: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.agent_probe.get_agent(agent_type), request)


@router.put("/agents/{agent_type}/config-path")
async def set_config_path(agent_type: str, payload: ConfigPathRequest, request: Request):
    ctx = get_context(request)
    return ok(ctx.agent_probe.set_config_path(agent_type, payload.config_path), request)


@router.post("/agents/{agent_type}/probe")
async def probe_agent(agent_type: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.agent_probe.probe(agent_type), request)


@router.get("/agents/{agent_type}/config-check")
async def config_check(agent_type: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.config_check(agent_type), request)


@router.get("/agents/{agent_type}/providers")
async def list_providers(agent_type: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.list_providers(agent_type), request)


@router.post("/agents/{agent_type}/providers")
async def create_provider(agent_type: str, payload: ProviderCreate, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.create_provider(agent_type, payload), request, status_code=201)


@router.get("/agents/{agent_type}/providers/{provider_id}")
async def get_provider(agent_type: str, provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.get_provider(agent_type, provider_id), request)


@router.get("/agents/{agent_type}/providers/{provider_id}/api-key")
async def reveal_provider_api_key(agent_type: str, provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.reveal_provider_api_key(agent_type, provider_id), request)


@router.patch("/agents/{agent_type}/providers/{provider_id}")
async def update_provider(agent_type: str, provider_id: str, payload: ProviderUpdate, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.update_provider(agent_type, provider_id, payload), request)


@router.delete("/agents/{agent_type}/providers/{provider_id}")
async def delete_provider(agent_type: str, provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.delete_provider(agent_type, provider_id), request)


@router.post("/agents/{agent_type}/providers/{provider_id}/apply")
async def apply_provider(agent_type: str, provider_id: str, payload: ApplyProviderRequest, request: Request):
    ctx = get_context(request)
    return ok(
        ctx.providers.apply_provider(
            agent_type,
            provider_id,
            dry_run=payload.dry_run,
            start_proxy=payload.start_proxy,
        ),
        request,
    )


@router.get("/proxies")
async def list_proxies(request: Request):
    ctx = get_context(request)
    return ok(ctx.proxy_manager.list_statuses(), request)


@router.get("/proxies/{provider_id}")
async def get_proxy(provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.proxy_manager.status(provider_id), request)


@router.post("/proxies/{provider_id}/start")
async def start_proxy(provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.start_proxy(provider_id), request)


@router.post("/proxies/{provider_id}/stop")
async def stop_proxy(provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.stop_proxy(provider_id), request)


@router.post("/proxies/{provider_id}/restart")
async def restart_proxy(provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.providers.restart_proxy(provider_id), request)


@router.get("/agents/{agent_type}/usage")
async def list_usage(agent_type: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.usage.list_usage(agent_type), request)


@router.post("/agents/{agent_type}/usage/reset")
async def reset_agent_usage(agent_type: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.usage.reset_agent_usage(agent_type), request)


@router.get("/agents/{agent_type}/providers/{provider_id}/usage")
async def get_usage(agent_type: str, provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.usage.get_usage(agent_type, provider_id), request)


@router.post("/agents/{agent_type}/providers/{provider_id}/usage/reset")
async def reset_usage(agent_type: str, provider_id: str, request: Request):
    ctx = get_context(request)
    return ok(ctx.usage.reset_usage(agent_type, provider_id), request)
