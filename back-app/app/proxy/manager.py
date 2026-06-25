from __future__ import annotations

import json
import socket
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import AsyncIterator
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI, Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from app.core.errors import AppError
from app.core.security import scrub_sensitive
from app.proxy.transformers import (
    build_auth_headers,
    build_target_url,
    convert_error_response,
    normalize_response_usage,
    source_format_for_agent,
    stream_event_done,
    stream_done_frames,
    stream_start_frames,
    stream_usage_payload,
    transform_request,
    transform_response,
    transform_stream_event,
)
from app.services.cache_store import CacheStore, utc_now
from app.services.usage_service import UsageService


@dataclass
class ProxyRuntime:
    provider_id: str
    agent_type: str
    port: int
    target_format: str | None
    status: str
    server: uvicorn.Server | None = None
    thread: threading.Thread | None = None
    last_error: str | None = None


def _merge_stream_usage(
    current: dict[str, int] | None,
    usage_payload: dict[str, Any],
    response_format: str,
) -> dict[str, int]:
    normalized = normalize_response_usage(usage_payload, response_format)
    merged = dict(current or {})
    for key in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    ):
        merged[key] = max(int(merged.get(key) or 0), int(normalized.get(key) or 0))
    merged["total_tokens"] = max(
        int(merged.get("total_tokens") or 0),
        int(merged.get("input_tokens") or 0) + int(merged.get("output_tokens") or 0),
    )
    return merged


def _stream_usage_response(usage: dict[str, int], response_format: str) -> dict[str, Any]:
    if response_format == "chat/completions":
        return {
            "usage": {
                "prompt_tokens": int(usage.get("input_tokens") or 0),
                "completion_tokens": int(usage.get("output_tokens") or 0),
                "total_tokens": int(usage.get("total_tokens") or 0),
            }
        }
    return {
        "usage": {
            "input_tokens": int(usage.get("input_tokens") or 0),
            "output_tokens": int(usage.get("output_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
            "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens") or 0),
            "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
        }
    }


class ProxyManager:
    def __init__(self, cache: CacheStore, usage_service: UsageService) -> None:
        self.cache = cache
        self.usage_service = usage_service
        self._runtimes: dict[str, ProxyRuntime] = {}
        self._lock = threading.RLock()

    def local_url(self, provider: dict[str, Any]) -> str | None:
        port = provider.get("proxy_port")
        if not provider.get("proxy_enabled") or not port:
            return None
        return f"http://127.0.0.1:{port}"

    def list_statuses(self) -> dict[str, Any]:
        snapshots = self.cache.get_proxies()
        with self._lock:
            for provider_id, runtime in self._runtimes.items():
                snapshots.setdefault("proxies", {})[provider_id] = self._runtime_snapshot(runtime)
        return snapshots["proxies"]

    def status(self, provider_id: str) -> dict[str, Any]:
        with self._lock:
            runtime = self._runtimes.get(provider_id)
            if runtime is not None:
                return self._runtime_snapshot(runtime)
        return self.cache.get_proxies().get("proxies", {}).get(provider_id, {"status": "stopped"})

    def start(self, provider: dict[str, Any]) -> dict[str, Any]:
        if not provider.get("proxy_enabled"):
            raise AppError("PROXY_DISABLED", "该 provider 未开启本地代理", status_code=400)
        port = int(provider.get("proxy_port") or 0)
        if not 1 <= port <= 65535:
            raise AppError("PORT_INVALID", "代理端口必须在 1-65535 之间", status_code=400)
        if not provider.get("api_key"):
            raise AppError("PROVIDER_API_KEY_EMPTY", "开启代理需要 provider 保存真实 API Key", status_code=400)

        provider_id = provider["id"]
        with self._lock:
            existing = self._runtimes.get(provider_id)
            if existing and existing.status == "running":
                return self._runtime_snapshot(existing)
            if not self._port_available(port):
                self._write_snapshot(
                    provider_id,
                    {
                        "provider_id": provider_id,
                        "agent_type": provider["agent_type"],
                        "port": port,
                        "local_url": f"http://127.0.0.1:{port}",
                        "status": "error",
                        "target_format": provider.get("target_format"),
                        "last_error": "端口已被占用",
                        "updated_at": utc_now(),
                    },
                )
                raise AppError(
                    "PORT_IN_USE",
                    f"代理端口已被占用: {port}",
                    status_code=409,
                    details={"port": port},
                )

            app = self._build_proxy_app(provider)
            config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
            server = uvicorn.Server(config)
            runtime = ProxyRuntime(
                provider_id=provider_id,
                agent_type=provider["agent_type"],
                port=port,
                target_format=provider.get("target_format"),
                status="starting",
                server=server,
            )
            thread = threading.Thread(target=server.run, daemon=True, name=f"proxy-{provider_id[:8]}")
            runtime.thread = thread
            self._runtimes[provider_id] = runtime
            self._write_snapshot(provider_id, self._runtime_snapshot(runtime, provider))
            thread.start()

        if not self._wait_for_port(port):
            with self._lock:
                runtime.status = "error"
                runtime.last_error = "代理服务启动超时"
                self._write_snapshot(provider_id, self._runtime_snapshot(runtime, provider))
            raise AppError("PROXY_START_FAILED", "代理服务启动超时", status_code=500, details={"port": port})

        with self._lock:
            runtime.status = "running"
            runtime.last_error = None
            self._write_snapshot(provider_id, self._runtime_snapshot(runtime, provider))
            return self._runtime_snapshot(runtime, provider)

    def stop(self, provider_id: str) -> dict[str, Any]:
        with self._lock:
            runtime = self._runtimes.get(provider_id)
            if runtime is None:
                snapshot = self.status(provider_id)
                snapshot["status"] = "stopped"
                snapshot["updated_at"] = utc_now()
                self._write_snapshot(provider_id, snapshot)
                return snapshot
            if runtime.server is not None:
                runtime.server.should_exit = True
            thread = runtime.thread
        if thread is not None:
            thread.join(timeout=3)
        with self._lock:
            runtime.status = "stopped"
            snapshot = self._runtime_snapshot(runtime)
            self._write_snapshot(provider_id, snapshot)
            self._runtimes.pop(provider_id, None)
            return snapshot

    def restart(self, provider: dict[str, Any]) -> dict[str, Any]:
        self.stop(provider["id"])
        return self.start(provider)

    def stop_all(self) -> None:
        for provider_id in list(self._runtimes.keys()):
            try:
                self.stop(provider_id)
            except Exception:
                pass

    def delete_snapshot(self, provider_id: str) -> None:
        data = self.cache.get_proxies()
        data.setdefault("proxies", {}).pop(provider_id, None)
        self.cache.save_proxies(data)

    def _build_proxy_app(self, provider: dict[str, Any]) -> FastAPI:
        app = FastAPI(title=f"miracle-api-switch proxy {provider['id']}")
        agent_type = provider["agent_type"]
        source_format = source_format_for_agent(agent_type)
        target_format = provider.get("target_format") or source_format

        @app.get("/health")
        async def health() -> dict[str, Any]:
            return {
                "status": "running",
                "provider_id": provider["id"],
                "agent_type": agent_type,
                "target_format": target_format,
            }

        @app.post("/{path:path}")
        async def proxy(path: str, request: Request) -> Response:
            try:
                body = await request.json()
                outbound_body = transform_request(body, source_format, target_format)
                target_url = build_target_url(provider["base_url"], target_format)
                headers = build_auth_headers(provider["api_key"], target_format)
                if bool(outbound_body.get("stream")):
                    return await self._proxy_stream(
                        provider=provider,
                        outbound_body=outbound_body,
                        target_url=target_url,
                        headers=headers,
                        agent_type=agent_type,
                        source_format=source_format,
                        target_format=target_format,
                    )
                async with httpx.AsyncClient(timeout=None) as client:
                    upstream = await client.post(target_url, json=outbound_body, headers=headers)

                content_type = upstream.headers.get("content-type", "")
                if upstream.status_code >= 400:
                    message = self._upstream_error_message(upstream)
                    return JSONResponse(
                        status_code=upstream.status_code,
                        content=convert_error_response(message, source_format),
                    )
                if "application/json" not in content_type:
                    self.usage_service.record_request_without_usage(agent_type, provider["id"])
                    return Response(
                        content=upstream.content,
                        status_code=upstream.status_code,
                        media_type=content_type or "application/octet-stream",
                    )

                raw_response = upstream.json()
                self.usage_service.record_proxy_response(agent_type, provider["id"], raw_response, target_format)
                converted = transform_response(raw_response, target_format, source_format)
                return JSONResponse(status_code=upstream.status_code, content=converted)
            except AppError as exc:
                return JSONResponse(
                    status_code=exc.status_code,
                    content=convert_error_response(exc.message, source_format, exc.code),
                )
            except httpx.RequestError as exc:
                return JSONResponse(
                    status_code=502,
                    content=convert_error_response(f"目标网关请求失败: {exc}", source_format),
                )
            except Exception as exc:  # noqa: BLE001 - proxy must return protocol-shaped errors
                return JSONResponse(
                    status_code=500,
                    content=convert_error_response(f"本地代理处理失败: {exc}", source_format),
                )

        return app

    async def _proxy_stream(
        self,
        provider: dict[str, Any],
        outbound_body: dict[str, Any],
        target_url: str,
        headers: dict[str, str],
        agent_type: str,
        source_format: str,
        target_format: str,
    ) -> Response:
        client = httpx.AsyncClient(timeout=None)
        stream_cm = client.stream("POST", target_url, json=outbound_body, headers=headers)
        upstream = await stream_cm.__aenter__()
        if upstream.status_code >= 400:
            body = await upstream.aread()
            await stream_cm.__aexit__(None, None, None)
            await client.aclose()
            message = self._upstream_error_message_from_bytes(upstream, body)
            return JSONResponse(
                status_code=upstream.status_code,
                content=convert_error_response(message, source_format),
            )

        async def generate() -> AsyncIterator[bytes]:
            usage_recorded = False
            merged_usage: dict[str, int] | None = None
            done_sent = False
            stream_state: dict[str, Any] = {}
            try:
                if target_format != source_format:
                    for frame in stream_start_frames(source_format):
                        yield frame

                event_name: str | None = None
                data_lines: list[str] = []
                async for line in upstream.aiter_lines():
                    if line == "":
                        async for frame, usage_payload, is_done in self._flush_sse_event(
                            data_lines=data_lines,
                            event_name=event_name,
                            target_format=target_format,
                            source_format=source_format,
                            stream_state=stream_state,
                        ):
                            if usage_payload is not None:
                                merged_usage = _merge_stream_usage(merged_usage, usage_payload, target_format)
                            done_sent = done_sent or is_done
                            yield frame
                        event_name = None
                        data_lines = []
                        continue
                    if line.startswith("event:"):
                        event_name = line[6:].strip()
                    elif line.startswith("data:"):
                        data_lines.append(line[5:].lstrip())

                if data_lines:
                    async for frame, usage_payload, is_done in self._flush_sse_event(
                        data_lines=data_lines,
                        event_name=event_name,
                        target_format=target_format,
                        source_format=source_format,
                        stream_state=stream_state,
                    ):
                        if usage_payload is not None:
                            merged_usage = _merge_stream_usage(merged_usage, usage_payload, target_format)
                        done_sent = done_sent or is_done
                        yield frame

                if target_format != source_format and not done_sent:
                    for frame in stream_done_frames(source_format, stream_state):
                        yield frame
                if merged_usage is not None:
                    usage_response = _stream_usage_response(merged_usage, target_format)
                    self.usage_service.record_proxy_response(agent_type, provider["id"], usage_response, target_format)
                    usage_recorded = True
                if not usage_recorded:
                    self.usage_service.record_request_without_usage(agent_type, provider["id"])
            finally:
                with suppress(Exception):
                    await stream_cm.__aexit__(None, None, None)
                with suppress(Exception):
                    await client.aclose()

        content_type = upstream.headers.get("content-type") or "text/event-stream"
        return StreamingResponse(generate(), status_code=upstream.status_code, media_type=content_type)

    async def _flush_sse_event(
        self,
        data_lines: list[str],
        event_name: str | None,
        target_format: str,
        source_format: str,
        stream_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[tuple[bytes, dict[str, Any] | None, bool]]:
        if not data_lines:
            return
        raw_data = "\n".join(data_lines).strip()
        if not raw_data:
            return
        if raw_data == "[DONE]":
            if target_format == source_format:
                yield b"data: [DONE]\n\n", None, True
            else:
                for frame in stream_done_frames(source_format, stream_state):
                    yield frame, None, True
            return
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            if target_format == source_format:
                prefix = f"event: {event_name}\n" if event_name else ""
                yield f"{prefix}data: {raw_data}\n\n".encode("utf-8"), None, False
            return
        if not isinstance(data, dict):
            return
        usage_payload = stream_usage_payload(data, target_format)
        is_done = stream_event_done(data, event_name, target_format)
        for frame in transform_stream_event(data, event_name, target_format, source_format, stream_state):
            yield frame, usage_payload, is_done

    def _upstream_error_message(self, response: httpx.Response) -> str:
        try:
            data = response.json()
            safe = scrub_sensitive(data)
            if isinstance(safe, dict):
                if isinstance(safe.get("error"), dict):
                    return str(safe["error"].get("message") or safe["error"])
                if safe.get("message"):
                    return str(safe["message"])
            return str(safe)
        except Exception:
            return response.text[:500]

    def _upstream_error_message_from_bytes(self, response: httpx.Response, body: bytes) -> str:
        try:
            data = json.loads(body.decode("utf-8"))
            safe = scrub_sensitive(data)
            if isinstance(safe, dict):
                if isinstance(safe.get("error"), dict):
                    return str(safe["error"].get("message") or safe["error"])
                if safe.get("message"):
                    return str(safe["message"])
            return str(safe)
        except Exception:
            return body.decode("utf-8", errors="replace")[:500]

    def _port_available(self, port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                return False
        return True

    def _wait_for_port(self, port: int, timeout_seconds: float = 3.0) -> bool:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.2)
                if sock.connect_ex(("127.0.0.1", port)) == 0:
                    return True
            time.sleep(0.05)
        return False

    def _runtime_snapshot(
        self,
        runtime: ProxyRuntime,
        provider: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "provider_id": runtime.provider_id,
            "agent_type": runtime.agent_type,
            "port": runtime.port,
            "local_url": f"http://127.0.0.1:{runtime.port}",
            "status": runtime.status,
            "target_format": provider.get("target_format") if provider else runtime.target_format,
            "last_error": runtime.last_error,
            "updated_at": utc_now(),
        }

    def _write_snapshot(self, provider_id: str, snapshot: dict[str, Any]) -> None:
        data = self.cache.get_proxies()
        data.setdefault("proxies", {})[provider_id] = snapshot
        self.cache.save_proxies(data)
