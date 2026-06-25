from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import tomlkit

from app.core.errors import AppError
from app.proxy.manager import ProxyManager
from app.services.cache_store import CacheStore

CODEX_PROVIDER_ID = "miracle"
CODEX_TOKEN_FIELD = "experimental_bearer_token"
LEGACY_CODEX_TOKEN_FIELD = "env_key"
CLAUDE_MODEL_FIELDS = (
    "ANTHROPIC_MODEL",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "CLAUDE_CODE_SUBAGENT_MODEL",
)


class ConfigWriter:
    def __init__(self, cache: CacheStore, proxy_manager: ProxyManager) -> None:
        self.cache = cache
        self.proxy_manager = proxy_manager

    def apply_provider(
        self,
        agent: dict[str, Any],
        provider: dict[str, Any],
        dry_run: bool = False,
    ) -> dict[str, Any]:
        agent_type = provider["agent_type"]
        config_file_value = agent.get("resolved_config_file")
        if not config_file_value:
            raise AppError("CONFIG_PATH_EMPTY", "Agent 配置文件路径未初始化", status_code=400)
        config_file = Path(config_file_value)
        if not config_file.exists():
            raise AppError(
                "CONFIG_FILE_MISSING",
                f"配置文件不存在: {config_file}",
                status_code=404,
                details={"path": str(config_file)},
            )
        if agent_type == "codex":
            return self._apply_codex(config_file, provider, dry_run=dry_run)
        if agent_type == "claude_code":
            return self._apply_claude_code(config_file, provider, dry_run=dry_run)
        raise AppError("AGENT_NOT_FOUND", f"不支持的 Agent 类型: {agent_type}", status_code=404)

    def capture_manual_config(self, agent: dict[str, Any]) -> dict[str, Any] | None:
        agent_type = agent.get("agent_type")
        config_file_value = agent.get("resolved_config_file")
        if not config_file_value:
            return None
        config_file = Path(config_file_value)
        if not config_file.exists():
            return None
        if agent_type == "codex":
            return self._capture_codex_manual_config(config_file)
        if agent_type == "claude_code":
            return self._capture_claude_manual_config(config_file)
        return None

    def restore_manual_config(self, agent: dict[str, Any], snapshot: dict[str, Any] | None) -> dict[str, Any]:
        if not snapshot:
            return {"restored": False, "reason": "snapshot_missing", "backup_path": None}
        agent_type = agent.get("agent_type")
        config_file_value = agent.get("resolved_config_file")
        if not config_file_value:
            raise AppError("CONFIG_PATH_EMPTY", "Agent 配置文件路径未初始化", status_code=400)
        config_file = Path(config_file_value)
        if not config_file.exists():
            raise AppError(
                "CONFIG_FILE_MISSING",
                f"配置文件不存在: {config_file}",
                status_code=404,
                details={"path": str(config_file)},
            )
        if agent_type == "codex":
            return self._restore_codex_manual_config(config_file, snapshot)
        if agent_type == "claude_code":
            return self._restore_claude_manual_config(config_file, snapshot)
        raise AppError("AGENT_NOT_FOUND", f"不支持的 Agent 类型: {agent_type}", status_code=404)

    def read_current_config(self, agent: dict[str, Any]) -> dict[str, Any]:
        agent_type = agent.get("agent_type")
        config_file_value = agent.get("resolved_config_file")
        result = {
            "agent_type": agent_type,
            "config_file": config_file_value,
            "base_url": "",
            "api_key": "",
            "model": "",
            "model_provider": "",
            "provider_name": "",
            "model_fields": {},
        }
        if not config_file_value:
            return result
        config_file = Path(config_file_value)
        if not config_file.exists():
            return result
        if agent_type == "codex":
            return self._read_codex(config_file, result)
        if agent_type == "claude_code":
            return self._read_claude_code(config_file, result)
        return result

    def _read_codex(self, config_file: Path, base: dict[str, Any]) -> dict[str, Any]:
        try:
            document = tomlkit.parse(config_file.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Codex 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc

        current_model_provider = str(document.get("model_provider") or "")
        providers = document.get("model_providers") or {}
        provider_table = {}
        try:
            provider_table = providers.get(current_model_provider or CODEX_PROVIDER_ID) or {}
        except AttributeError:
            provider_table = {}

        base.update(
            {
                "base_url": str(provider_table.get("base_url") or ""),
                "api_key": str(
                    provider_table.get(CODEX_TOKEN_FIELD)
                    or provider_table.get(LEGACY_CODEX_TOKEN_FIELD)
                    or ""
                ),
                "model": str(document.get("model") or ""),
                "model_provider": current_model_provider,
                "provider_name": str(provider_table.get("name") or ""),
            }
        )
        return base

    def _read_claude_code(self, config_file: Path, base: dict[str, Any]) -> dict[str, Any]:
        try:
            with config_file.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Claude Code 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc
        if not isinstance(document, dict):
            raise AppError("CONFIG_PARSE_ERROR", "Claude Code 配置文件必须是 JSON object", status_code=400)

        env = document.get("env") or {}
        if not isinstance(env, dict):
            env = {}
        model_fields = {field: str(env.get(field) or "") for field in CLAUDE_MODEL_FIELDS}
        base.update(
            {
                "base_url": str(env.get("ANTHROPIC_BASE_URL") or ""),
                "api_key": str(env.get("ANTHROPIC_AUTH_TOKEN") or ""),
                "model": model_fields.get("ANTHROPIC_MODEL") or next(
                    (value for value in model_fields.values() if value),
                    "",
                ),
                "provider_name": "",
                "model_fields": model_fields,
            }
        )
        return base

    def _apply_codex(self, config_file: Path, provider: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        try:
            document = tomlkit.parse(config_file.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Codex 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc

        proxy_url = self.proxy_manager.local_url(provider)
        base_url = proxy_url if provider.get("proxy_enabled") else provider["base_url"]
        bearer_token = "" if provider.get("proxy_enabled") else provider["api_key"]

        providers = document.get("model_providers")
        if providers is None:
            providers = tomlkit.table()
            document["model_providers"] = providers
        if CODEX_PROVIDER_ID not in providers:
            providers[CODEX_PROVIDER_ID] = tomlkit.table()
        provider_table = providers[CODEX_PROVIDER_ID]

        document["model_provider"] = CODEX_PROVIDER_ID
        document["model"] = provider["model"]
        provider_table["name"] = provider["display_name"]
        provider_table["base_url"] = base_url
        provider_table["wire_api"] = "responses"
        provider_table[CODEX_TOKEN_FIELD] = bearer_token
        try:
            del provider_table[LEGACY_CODEX_TOKEN_FIELD]
        except KeyError:
            pass

        preview = {
            "config_file": str(config_file),
            "agent_type": "codex",
            "dry_run": dry_run,
            "backup_path": None,
            "changed_fields": {
                "model_provider": CODEX_PROVIDER_ID,
                "model": provider["model"],
                f"model_providers.{CODEX_PROVIDER_ID}.name": provider["display_name"],
                f"model_providers.{CODEX_PROVIDER_ID}.base_url": base_url,
                f"model_providers.{CODEX_PROVIDER_ID}.wire_api": "responses",
                f"model_providers.{CODEX_PROVIDER_ID}.{CODEX_TOKEN_FIELD}": "<empty>" if not bearer_token else "<api-key>",
            },
        }
        if dry_run:
            return preview
        backup = self.cache.backup_file(config_file, "codex")
        self._write_config_file(config_file, tomlkit.dumps(document))
        preview["backup_path"] = str(backup)
        return preview

    def _capture_codex_manual_config(self, config_file: Path) -> dict[str, Any]:
        try:
            document = tomlkit.parse(config_file.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Codex 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc
        model_provider = str(document.get("model_provider") or "")
        provider_config: dict[str, Any] = {}
        providers = document.get("model_providers") or {}
        try:
            provider_table = providers.get(model_provider) or {}
        except AttributeError:
            provider_table = {}
        for key in ("name", "base_url", "wire_api", CODEX_TOKEN_FIELD, LEGACY_CODEX_TOKEN_FIELD):
            if key in provider_table:
                provider_config[key] = str(provider_table.get(key) or "")
        return {
            "agent_type": "codex",
            "config_file": str(config_file),
            "model": str(document.get("model") or ""),
            "model_provider": model_provider,
            "provider_config": provider_config,
        }

    def _restore_codex_manual_config(self, config_file: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
        try:
            document = tomlkit.parse(config_file.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Codex 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc

        model_provider = str(snapshot.get("model_provider") or "")
        document["model"] = str(snapshot.get("model") or "")
        document["model_provider"] = model_provider

        provider_config = snapshot.get("provider_config")
        if model_provider and isinstance(provider_config, dict):
            providers = document.get("model_providers")
            if providers is None:
                providers = tomlkit.table()
                document["model_providers"] = providers
            if model_provider not in providers:
                providers[model_provider] = tomlkit.table()
            provider_table = providers[model_provider]
            for key in ("name", "base_url", "wire_api"):
                if key in provider_config:
                    provider_table[key] = str(provider_config.get(key) or "")
            token = provider_config.get(CODEX_TOKEN_FIELD)
            if token is None:
                token = provider_config.get(LEGACY_CODEX_TOKEN_FIELD, "")
            provider_table[CODEX_TOKEN_FIELD] = str(token or "")
            try:
                del provider_table[LEGACY_CODEX_TOKEN_FIELD]
            except KeyError:
                pass

        backup = self.cache.backup_file(config_file, "codex")
        self._write_config_file(config_file, tomlkit.dumps(document))
        return {
            "restored": True,
            "config_file": str(config_file),
            "backup_path": str(backup),
            "changed_fields": ["model", "model_provider"],
        }

    def _apply_claude_code(self, config_file: Path, provider: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        try:
            with config_file.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Claude Code 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc
        if not isinstance(document, dict):
            raise AppError("CONFIG_PARSE_ERROR", "Claude Code 配置文件必须是 JSON object", status_code=400)

        env = document.setdefault("env", {})
        if not isinstance(env, dict):
            raise AppError("CONFIG_PARSE_ERROR", "`settings.json` 中的 env 字段必须是 object", status_code=400)

        proxy_url = self.proxy_manager.local_url(provider)
        base_url = proxy_url if provider.get("proxy_enabled") else provider["base_url"]
        token = provider["api_key"]

        env["ANTHROPIC_AUTH_TOKEN"] = token
        env["ANTHROPIC_BASE_URL"] = base_url
        for field in CLAUDE_MODEL_FIELDS:
            env[field] = provider["model"]

        preview = {
            "config_file": str(config_file),
            "agent_type": "claude_code",
            "dry_run": dry_run,
            "backup_path": None,
            "changed_fields": {
                "env.ANTHROPIC_AUTH_TOKEN": "<empty>" if not token else "<api-key>",
                "env.ANTHROPIC_BASE_URL": base_url,
                **{f"env.{field}": provider["model"] for field in CLAUDE_MODEL_FIELDS},
            },
        }
        if dry_run:
            return preview
        backup = self.cache.backup_file(config_file, "claude_code")
        self._write_config_file(config_file, json.dumps(document, ensure_ascii=False, indent=4) + "\n")
        preview["backup_path"] = str(backup)
        return preview

    def _capture_claude_manual_config(self, config_file: Path) -> dict[str, Any]:
        try:
            with config_file.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Claude Code 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc
        if not isinstance(document, dict):
            raise AppError("CONFIG_PARSE_ERROR", "Claude Code 配置文件必须是 JSON object", status_code=400)
        env = document.get("env") or {}
        if not isinstance(env, dict):
            env = {}
        fields = {
            "ANTHROPIC_AUTH_TOKEN": str(env.get("ANTHROPIC_AUTH_TOKEN") or ""),
            "ANTHROPIC_BASE_URL": str(env.get("ANTHROPIC_BASE_URL") or ""),
            **{field: str(env.get(field) or "") for field in CLAUDE_MODEL_FIELDS},
        }
        return {
            "agent_type": "claude_code",
            "config_file": str(config_file),
            "env": fields,
        }

    def _restore_claude_manual_config(self, config_file: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
        try:
            with config_file.open("r", encoding="utf-8") as handle:
                document = json.load(handle)
        except Exception as exc:  # noqa: BLE001
            raise AppError(
                "CONFIG_PARSE_ERROR",
                f"Claude Code 配置文件解析失败: {config_file}",
                status_code=400,
                details={"path": str(config_file), "error": str(exc)},
            ) from exc
        if not isinstance(document, dict):
            raise AppError("CONFIG_PARSE_ERROR", "Claude Code 配置文件必须是 JSON object", status_code=400)
        env = document.setdefault("env", {})
        if not isinstance(env, dict):
            raise AppError("CONFIG_PARSE_ERROR", "`settings.json` 中的 env 字段必须是 object", status_code=400)

        snapshot_env = snapshot.get("env") or {}
        changed_fields: list[str] = []
        for field in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", *CLAUDE_MODEL_FIELDS):
            env[field] = str(snapshot_env.get(field) or "")
            changed_fields.append(f"env.{field}")

        backup = self.cache.backup_file(config_file, "claude_code")
        self._write_config_file(config_file, json.dumps(document, ensure_ascii=False, indent=4) + "\n")
        return {
            "restored": True,
            "config_file": str(config_file),
            "backup_path": str(backup),
            "changed_fields": changed_fields,
        }

    def _write_config_file(self, config_file: Path, content: str) -> None:
        try:
            self.cache.write_text_atomic(config_file, content)
        except AppError as exc:
            raise AppError(
                "CONFIG_WRITE_FAILED",
                f"配置文件写入失败: {config_file}",
                status_code=500,
                details=exc.details,
            ) from exc
