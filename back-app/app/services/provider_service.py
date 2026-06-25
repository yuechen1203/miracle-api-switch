from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from app.core.errors import AppError, NotFoundError
from app.core.security import mask_api_key
from app.models import ProviderCreate, ProviderUpdate
from app.proxy.manager import ProxyManager
from app.services.agent_probe import AgentProbeService, normalize_agent_type
from app.services.cache_store import CacheStore, utc_now
from app.services.config_writer import CODEX_PROVIDER_ID, ConfigWriter
from app.services.usage_service import UsageService

LEGACY_CODEX_PROVIDER_IDS = {"miracle_api_switch"}


class ProviderService:
    def __init__(
        self,
        cache: CacheStore,
        agent_probe: AgentProbeService,
        config_writer: ConfigWriter,
        proxy_manager: ProxyManager,
        usage_service: UsageService,
    ) -> None:
        self.cache = cache
        self.agent_probe = agent_probe
        self.config_writer = config_writer
        self.proxy_manager = proxy_manager
        self.usage_service = usage_service

    def list_providers(self, agent_type: str) -> list[dict[str, Any]]:
        agent_type = normalize_agent_type(agent_type)
        return [self._public(agent_type, provider) for provider in self._load(agent_type)]

    def get_provider(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        provider = self._find(agent_type, provider_id)
        return self._public(agent_type, provider)

    def reveal_provider_api_key(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        provider = self._find(agent_type, provider_id)
        api_key = provider.get("api_key") or ""
        return {
            "provider_id": provider_id,
            "has_api_key": bool(api_key),
            "api_key": api_key,
        }

    def get_provider_raw(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        return deepcopy(self._find(agent_type, provider_id))

    def get_provider_raw_any(self, provider_id: str) -> dict[str, Any]:
        for agent_type in ("codex", "claude_code"):
            try:
                return self.get_provider_raw(agent_type, provider_id)
            except NotFoundError:
                continue
        raise NotFoundError("PROVIDER_NOT_FOUND", f"Provider 不存在: {provider_id}")

    def create_provider(self, agent_type: str, payload: ProviderCreate) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        providers = self._load(agent_type)
        self._assert_name_unique(providers, payload.display_name)
        now = utc_now()
        provider = payload.model_dump()
        provider["target_format"] = provider.get("target_format") or None
        provider.update(
            {
                "id": uuid.uuid4().hex,
                "agent_type": agent_type,
                "created_at": now,
                "updated_at": now,
            }
        )
        providers.append(provider)
        self._save(agent_type, providers)
        if provider.get("proxy_enabled"):
            self._write_stopped_proxy_snapshot(provider)
        return self._public(agent_type, provider)

    def update_provider(self, agent_type: str, provider_id: str, payload: ProviderUpdate) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        providers = self._load(agent_type)
        index, provider = self._find_with_index(providers, provider_id)

        updates = payload.model_dump(exclude_unset=True)
        expected_updated_at = updates.pop("expected_updated_at", None)
        if expected_updated_at and expected_updated_at != provider.get("updated_at"):
            raise AppError(
                "PROVIDER_UPDATE_CONFLICT",
                "Provider 已被其他操作更新，请刷新后重试",
                status_code=409,
                details={"expected_updated_at": expected_updated_at, "actual_updated_at": provider.get("updated_at")},
            )

        if "display_name" in updates and updates["display_name"]:
            self._assert_name_unique(providers, updates["display_name"], exclude_id=provider_id)

        changed_proxy_related = any(
            key in updates
            for key in ("proxy_enabled", "proxy_port", "target_format", "base_url", "api_key")
        )
        for key, value in updates.items():
            if key == "api_key" and value == "":
                continue
            if key == "target_format" and value == "response":
                value = "responses"
            provider[key] = value

        self._validate_provider(provider)
        provider["updated_at"] = utc_now()
        providers[index] = provider
        self._save(agent_type, providers)

        if changed_proxy_related:
            self.proxy_manager.stop(provider_id)
            if provider.get("proxy_enabled"):
                self._write_stopped_proxy_snapshot(provider)
            else:
                self.proxy_manager.delete_snapshot(provider_id)

        return self._public(agent_type, provider)

    def delete_provider(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        providers = self._load(agent_type)
        index, provider = self._find_with_index(providers, provider_id)
        agent = self.agent_probe.get_agent(agent_type)
        is_current = agent.get("current_provider_id") == provider_id
        restore_result = None
        if is_current:
            self._capture_manual_config_if_needed(agent_type, agent, providers)
            restore_result = self._restore_manual_config(agent_type, agent)
        self.proxy_manager.stop(provider_id)
        self.proxy_manager.delete_snapshot(provider_id)
        self.usage_service.delete_usage(agent_type, provider_id)
        providers.pop(index)
        self._save(agent_type, providers)
        if is_current:
            self.agent_probe.set_current_provider(agent_type, None)
        return {"deleted": True, "provider_id": provider_id, "restore_result": restore_result}

    def apply_provider(
        self,
        agent_type: str,
        provider_id: str,
        dry_run: bool = False,
        start_proxy: bool = True,
    ) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        provider = self.get_provider_raw(agent_type, provider_id)
        self._validate_provider(provider)
        agent = self.agent_probe.probe(agent_type)
        if agent.get("status") == "uninitialized":
            raise AppError("CONFIG_PATH_EMPTY", "请先配置 Agent 配置文件路径", status_code=400)
        if agent.get("status") == "missing":
            raise AppError("CONFIG_FILE_MISSING", agent.get("status_message", "配置文件不存在"), status_code=404)
        if agent.get("status") != "installed":
            raise AppError("CONFIG_PARSE_ERROR", agent.get("status_message", "配置文件不可用"), status_code=400)

        proxy_status = None
        started_proxy = False
        if provider.get("proxy_enabled") and start_proxy and not dry_run:
            proxy_status = self.proxy_manager.start(provider)
            started_proxy = True

        try:
            if not dry_run:
                self._capture_manual_config_if_needed(agent_type, agent, self._load(agent_type))
            write_result = self.config_writer.apply_provider(agent, provider, dry_run=dry_run)
        except Exception:
            if started_proxy:
                self.proxy_manager.stop(provider_id)
            raise

        if not dry_run:
            self.agent_probe.set_current_provider(agent_type, provider_id)
            if provider.get("proxy_enabled") and not proxy_status:
                self._write_stopped_proxy_snapshot(provider)

        return {
            "agent": self.agent_probe.get_agent(agent_type),
            "provider": self._public(agent_type, provider),
            "write_result": write_result,
            "proxy_status": proxy_status or self.proxy_manager.status(provider_id),
            "dry_run": dry_run,
        }

    def config_check(self, agent_type: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        agent = self.agent_probe.probe(agent_type)
        if agent.get("status") != "installed":
            current_public = {
                "agent_type": agent_type,
                "config_file": agent.get("resolved_config_file"),
                "base_url": "",
                "model": "",
                "model_provider": "",
                "provider_name": "",
                "model_fields": {},
                "has_api_key": False,
                "api_key_masked": "",
            }
            if not agent.get("current_provider_id"):
                return {
                    "agent": agent,
                    "status": "not_initialized",
                    "is_match": None,
                    "message": "当前 Provider 未初始化",
                    "current_config": current_public,
                    "expected_config": None,
                    "mismatched_fields": [],
                }
            return {
                "agent": agent,
                "status": "unavailable",
                "is_match": False,
                "message": agent.get("status_message", "配置文件不可用，无法校准"),
                "current_config": current_public,
                "expected_config": None,
                "mismatched_fields": ["config_file"],
            }
        current = self.config_writer.read_current_config(agent)
        raw_api_key = current.pop("api_key", "")
        current_public = {
            **current,
            "has_api_key": bool(raw_api_key),
            "api_key_masked": mask_api_key(raw_api_key),
        }

        provider_id = agent.get("current_provider_id")
        if not provider_id:
            return {
                "agent": agent,
                "status": "not_initialized",
                "is_match": None,
                "message": "当前 Provider 未初始化",
                "current_config": current_public,
                "expected_config": None,
                "mismatched_fields": [],
            }

        try:
            provider = self.get_provider_raw(agent_type, provider_id)
        except NotFoundError:
            return {
                "agent": agent,
                "status": "provider_missing",
                "is_match": False,
                "message": "最近应用的 Provider 已不存在，请重新选择一组 Provider",
                "current_config": current_public,
                "expected_config": None,
                "mismatched_fields": ["provider"],
            }

        expected = self._expected_config(provider)
        mismatched = self._mismatched_config_fields(agent_type, current, raw_api_key, expected)
        return {
            "agent": agent,
            "status": "matched" if not mismatched else "mismatched",
            "is_match": not mismatched,
            "message": "配置文件校准通过" if not mismatched else "配置文件内容已被外部改动，建议重新选择一组 Provider 加载",
            "current_config": current_public,
            "expected_config": {
                **{key: value for key, value in expected.items() if key != "api_key" and not key.startswith("_")},
                "has_api_key": bool(expected.get("api_key")),
                "api_key_masked": mask_api_key(expected.get("api_key")),
            },
            "mismatched_fields": mismatched,
        }

    def start_proxy(self, provider_id: str) -> dict[str, Any]:
        provider = self.get_provider_raw_any(provider_id)
        return self.proxy_manager.start(provider)

    def stop_proxy(self, provider_id: str) -> dict[str, Any]:
        return self.proxy_manager.stop(provider_id)

    def restart_proxy(self, provider_id: str) -> dict[str, Any]:
        provider = self.get_provider_raw_any(provider_id)
        return self.proxy_manager.restart(provider)

    def _load(self, agent_type: str) -> list[dict[str, Any]]:
        return self.cache.get_providers(agent_type).setdefault("providers", [])

    def _save(self, agent_type: str, providers: list[dict[str, Any]]) -> None:
        data = self.cache.get_providers(agent_type)
        data["providers"] = providers
        self.cache.save_providers(agent_type, data)

    def _capture_manual_config_if_needed(
        self,
        agent_type: str,
        agent: dict[str, Any],
        providers: list[dict[str, Any]],
    ) -> None:
        if agent.get("status") != "installed":
            return
        current = self.config_writer.read_current_config(agent)
        raw_api_key = current.get("api_key", "")
        if self._config_matches_any_provider(agent_type, current, raw_api_key, providers):
            return
        snapshot = self.config_writer.capture_manual_config(agent)
        if snapshot is None:
            return
        data = self.cache.get_manual_config_snapshots()
        snapshot["captured_at"] = utc_now()
        data.setdefault("snapshots", {})[agent_type] = snapshot
        self.cache.save_manual_config_snapshots(data)

    def _restore_manual_config(self, agent_type: str, agent: dict[str, Any]) -> dict[str, Any]:
        data = self.cache.get_manual_config_snapshots()
        snapshot = data.setdefault("snapshots", {}).get(agent_type)
        return self.config_writer.restore_manual_config(agent, snapshot)

    def _config_matches_any_provider(
        self,
        agent_type: str,
        current: dict[str, Any],
        current_api_key: str,
        providers: list[dict[str, Any]],
    ) -> bool:
        for provider in providers:
            expected = self._expected_config(provider)
            if not self._mismatched_config_fields(
                agent_type,
                current,
                current_api_key,
                expected,
                allow_legacy_codex_provider=True,
            ):
                return True
        return False

    def _find(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        providers = self._load(agent_type)
        _, provider = self._find_with_index(providers, provider_id)
        return provider

    def _find_with_index(
        self,
        providers: list[dict[str, Any]],
        provider_id: str,
    ) -> tuple[int, dict[str, Any]]:
        for index, provider in enumerate(providers):
            if provider.get("id") == provider_id:
                return index, provider
        raise NotFoundError("PROVIDER_NOT_FOUND", f"Provider 不存在: {provider_id}")

    def _assert_name_unique(
        self,
        providers: list[dict[str, Any]],
        display_name: str,
        exclude_id: str | None = None,
    ) -> None:
        normalized = display_name.strip().lower()
        for provider in providers:
            if provider.get("id") == exclude_id:
                continue
            if provider.get("display_name", "").strip().lower() == normalized:
                raise AppError(
                    "PROVIDER_NAME_DUPLICATED",
                    f"Provider 名称已存在: {display_name}",
                    status_code=409,
                )

    def _validate_provider(self, provider: dict[str, Any]) -> None:
        if not provider.get("display_name"):
            raise AppError("PROVIDER_INVALID", "Provider 名称不能为空", status_code=400)
        if not provider.get("api_key"):
            raise AppError("PROVIDER_API_KEY_EMPTY", "Provider API Key 不能为空", status_code=400)
        if not provider.get("base_url"):
            raise AppError("PROVIDER_INVALID", "Provider Base URL 不能为空", status_code=400)
        if not provider.get("model"):
            raise AppError("PROVIDER_INVALID", "Provider Model 不能为空", status_code=400)
        if provider.get("proxy_enabled"):
            port = int(provider.get("proxy_port") or 0)
            if not 1 <= port <= 65535:
                raise AppError("PORT_INVALID", "代理端口必须在 1-65535 之间", status_code=400)
            if provider.get("target_format") not in ("chat/completions", "responses", "messages"):
                raise AppError("TARGET_FORMAT_INVALID", "目标 API 格式非法", status_code=400)

    def _expected_config(self, provider: dict[str, Any]) -> dict[str, Any]:
        proxy_url = self.proxy_manager.local_url(provider)
        agent_type = provider.get("agent_type")
        if agent_type == "claude_code":
            api_key = provider.get("api_key", "")
        else:
            api_key = "" if provider.get("proxy_enabled") else provider.get("api_key", "")
        return {
            "base_url": proxy_url if provider.get("proxy_enabled") else provider.get("base_url", ""),
            "api_key": api_key,
            "model": provider.get("model", ""),
            "model_provider": CODEX_PROVIDER_ID if agent_type == "codex" else "",
            "provider_name": provider.get("display_name", ""),
            "_proxy_enabled": bool(provider.get("proxy_enabled")),
        }

    def _mismatched_config_fields(
        self,
        agent_type: str,
        current: dict[str, Any],
        current_api_key: str,
        expected: dict[str, Any],
        allow_legacy_codex_provider: bool = False,
    ) -> list[str]:
        mismatched: list[str] = []
        if current.get("base_url", "") != expected.get("base_url", ""):
            mismatched.append("base_url")
        legacy_claude_proxy_auth = (
            allow_legacy_codex_provider
            and agent_type == "claude_code"
            and bool(expected.get("_proxy_enabled"))
            and current_api_key == ""
            and bool(expected.get("api_key"))
        )
        if current_api_key != expected.get("api_key", "") and not legacy_claude_proxy_auth:
            mismatched.append("api_key")
        if current.get("model", "") != expected.get("model", ""):
            mismatched.append("model")
        if agent_type == "codex":
            current_model_provider = current.get("model_provider", "")
            expected_model_provider = expected.get("model_provider", "")
            legacy_match = (
                allow_legacy_codex_provider
                and expected_model_provider == CODEX_PROVIDER_ID
                and current_model_provider in LEGACY_CODEX_PROVIDER_IDS
            )
            if current_model_provider != expected_model_provider and not legacy_match:
                mismatched.append("model_provider")
        if agent_type == "claude_code":
            model_fields = current.get("model_fields") or {}
            for field, value in model_fields.items():
                if value != expected.get("model", ""):
                    mismatched.append(f"model_fields.{field}")
        return mismatched

    def _public(self, agent_type: str, provider: dict[str, Any]) -> dict[str, Any]:
        public = deepcopy(provider)
        api_key = public.pop("api_key", "")
        public["has_api_key"] = bool(api_key)
        public["api_key_masked"] = mask_api_key(api_key)
        public["local_proxy_url"] = self.proxy_manager.local_url(provider)
        public["proxy_status"] = self.proxy_manager.status(provider["id"])
        public["usage"] = self.usage_service.get_usage(agent_type, provider["id"])
        agent = self.agent_probe.get_agent(agent_type)
        public["is_current"] = agent.get("current_provider_id") == provider["id"]
        return public

    def _write_stopped_proxy_snapshot(self, provider: dict[str, Any]) -> None:
        proxy_data = self.cache.get_proxies()
        proxy_data.setdefault("proxies", {})[provider["id"]] = {
            "provider_id": provider["id"],
            "agent_type": provider["agent_type"],
            "port": provider.get("proxy_port"),
            "local_url": self.proxy_manager.local_url(provider),
            "status": "stopped",
            "target_format": provider.get("target_format"),
            "last_error": None,
            "updated_at": utc_now(),
        }
        self.cache.save_proxies(proxy_data)
