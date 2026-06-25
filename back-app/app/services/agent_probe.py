from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - only used before Python 3.11
    import tomli as tomllib  # type: ignore

from app.core.errors import AppError
from app.models import AgentType
from app.services.cache_store import CacheStore, utc_now

AGENT_CONFIG_FILES = {
    AgentType.codex.value: "config.toml",
    AgentType.claude_code.value: "settings.json",
}


def normalize_agent_type(agent_type: str) -> str:
    if agent_type not in AGENT_CONFIG_FILES:
        raise AppError("AGENT_NOT_FOUND", f"不支持的 Agent 类型: {agent_type}", status_code=404)
    return agent_type


class AgentProbeService:
    def __init__(self, cache: CacheStore) -> None:
        self.cache = cache

    def list_agents(self) -> list[dict[str, Any]]:
        data = self.cache.get_agents()
        return [data["agents"][AgentType.codex.value], data["agents"][AgentType.claude_code.value]]

    def get_agent(self, agent_type: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        return self.cache.get_agents()["agents"][agent_type]

    def set_config_path(self, agent_type: str, config_path: str) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        return self.probe(agent_type, config_path=config_path)

    def probe(self, agent_type: str, config_path: str | None = None) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        agents = self.cache.get_agents()
        current = agents["agents"][agent_type]
        raw_path = current.get("config_path", "") if config_path is None else config_path.strip()
        result = self._build_probe_result(agent_type, raw_path)
        result["current_provider_id"] = current.get("current_provider_id")
        agents["agents"][agent_type] = result
        self.cache.save_agents(agents)
        return result

    def set_current_provider(self, agent_type: str, provider_id: str | None) -> dict[str, Any]:
        agent_type = normalize_agent_type(agent_type)
        agents = self.cache.get_agents()
        agent = agents["agents"][agent_type]
        agent["current_provider_id"] = provider_id
        agent["updated_at"] = utc_now()
        agents["agents"][agent_type] = agent
        self.cache.save_agents(agents)
        return agent

    def _build_probe_result(self, agent_type: str, raw_path: str) -> dict[str, Any]:
        now = utc_now()
        if not raw_path:
            return {
                "agent_type": agent_type,
                "config_path": "",
                "resolved_config_file": None,
                "status": "uninitialized",
                "status_message": "配置路径为空",
                "current_provider_id": None,
                "updated_at": now,
            }

        try:
            config_file = self.resolve_config_file(agent_type, raw_path)
        except AppError as exc:
            return {
                "agent_type": agent_type,
                "config_path": raw_path,
                "resolved_config_file": None,
                "status": "invalid",
                "status_message": exc.message,
                "current_provider_id": None,
                "updated_at": now,
            }

        if not config_file.exists():
            return {
                "agent_type": agent_type,
                "config_path": raw_path,
                "resolved_config_file": str(config_file),
                "status": "missing",
                "status_message": f"目标配置文件不存在: {config_file}",
                "current_provider_id": None,
                "updated_at": now,
            }

        try:
            self._parse_config(agent_type, config_file)
            if not config_file.is_file():
                raise OSError("not a file")
            with config_file.open("a", encoding="utf-8"):
                pass
        except Exception as exc:  # noqa: BLE001 - user-facing probe should not leak tracebacks
            return {
                "agent_type": agent_type,
                "config_path": raw_path,
                "resolved_config_file": str(config_file),
                "status": "invalid",
                "status_message": f"配置文件不可用: {exc}",
                "current_provider_id": None,
                "updated_at": now,
            }

        return {
            "agent_type": agent_type,
            "config_path": raw_path,
            "resolved_config_file": str(config_file),
            "status": "installed",
            "status_message": "配置文件存在且可解析",
            "current_provider_id": None,
            "updated_at": now,
        }

    def resolve_config_file(self, agent_type: str, raw_path: str) -> Path:
        agent_type = normalize_agent_type(agent_type)
        expected_name = AGENT_CONFIG_FILES[agent_type]
        path = Path(raw_path).expanduser()
        if path.exists() and path.is_dir():
            return path / expected_name
        if path.name == expected_name:
            return path
        if path.exists() and path.is_file() and path.name != expected_name:
            raise AppError(
                "CONFIG_PATH_INVALID",
                f"{agent_type} 配置文件名必须是 {expected_name}",
                details={"path": str(path), "expected": expected_name},
            )
        return path / expected_name

    def _parse_config(self, agent_type: str, config_file: Path) -> None:
        if agent_type == AgentType.codex.value:
            with config_file.open("rb") as handle:
                tomllib.load(handle)
            return
        with config_file.open("r", encoding="utf-8") as handle:
            json.load(handle)

