from __future__ import annotations

import json
import os
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.core.config import get_cache_dir, get_workspace_root
from app.core.errors import AppError
from app.models import AgentType


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class CacheStore:
    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = (workspace_root or get_workspace_root()).resolve()
        self.cache_dir = get_cache_dir(self.workspace_root)
        self.backups_dir = self.cache_dir / "backups"
        self._locks: dict[Path, threading.RLock] = {}
        self._locks_guard = threading.Lock()
        self.ensure_initialized()

    def ensure_initialized(self) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        self._chmod_private(self.cache_dir, directory=True)
        self._chmod_private(self.backups_dir, directory=True)
        self.get_agents()
        self.get_providers(AgentType.codex.value)
        self.get_providers(AgentType.claude_code.value)
        self.get_proxies()
        self.get_usage(AgentType.codex.value)
        self.get_usage(AgentType.claude_code.value)

    def _chmod_private(self, path: Path, directory: bool = False) -> None:
        try:
            os.chmod(path, 0o700 if directory else 0o600)
        except OSError:
            pass

    def _lock_for(self, path: Path) -> threading.RLock:
        with self._locks_guard:
            lock = self._locks.get(path)
            if lock is None:
                lock = threading.RLock()
                self._locks[path] = lock
            return lock

    def _file(self, name: str) -> Path:
        return self.cache_dir / name

    def read_json(self, name: str, default_factory: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        path = self._file(name)
        lock = self._lock_for(path)
        with lock:
            if not path.exists():
                data = default_factory()
                self.write_json(name, data)
                return data
            try:
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except json.JSONDecodeError as exc:
                raise AppError(
                    "CACHE_PARSE_ERROR",
                    f"缓存文件解析失败: {path}",
                    status_code=500,
                    details={"path": str(path), "error": str(exc)},
                ) from exc

    def write_json(self, name: str, data: dict[str, Any]) -> None:
        path = self._file(name)
        encoded = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self.write_text_atomic(path, encoded)

    def write_text_atomic(self, path: Path, content: str) -> None:
        lock = self._lock_for(path)
        with lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_name(f".{path.name}.tmp")
            existing_mode = None
            if path.exists():
                try:
                    existing_mode = path.stat().st_mode
                except OSError:
                    existing_mode = None
            try:
                with tmp_path.open("w", encoding="utf-8") as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(tmp_path, path)
                if existing_mode is not None:
                    try:
                        os.chmod(path, existing_mode)
                    except OSError:
                        pass
                else:
                    self._chmod_private(path)
            except OSError as exc:
                try:
                    tmp_path.unlink(missing_ok=True)
                except OSError:
                    pass
                raise AppError(
                    "CACHE_WRITE_FAILED",
                    f"写入文件失败: {path}",
                    status_code=500,
                    details={"path": str(path), "error": str(exc)},
                ) from exc

    def backup_file(self, source: Path, agent_type: str) -> Path:
        if not source.exists():
            raise AppError(
                "CONFIG_FILE_MISSING",
                f"配置文件不存在: {source}",
                status_code=404,
                details={"path": str(source)},
            )
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = self.backups_dir / f"{agent_type}_{stamp}_{source.name}"
        try:
            shutil.copy2(source, backup_path)
            self._chmod_private(backup_path)
        except OSError as exc:
            raise AppError(
                "CONFIG_BACKUP_FAILED",
                "配置文件备份失败",
                status_code=500,
                details={"source": str(source), "backup": str(backup_path), "error": str(exc)},
            ) from exc
        return backup_path

    def default_agents(self) -> dict[str, Any]:
        now = utc_now()
        return {
            "schema_version": 1,
            "agents": {
                "codex": {
                    "agent_type": "codex",
                    "config_path": "",
                    "resolved_config_file": None,
                    "status": "uninitialized",
                    "status_message": "配置路径为空",
                    "current_provider_id": None,
                    "updated_at": now,
                },
                "claude_code": {
                    "agent_type": "claude_code",
                    "config_path": "",
                    "resolved_config_file": None,
                    "status": "uninitialized",
                    "status_message": "配置路径为空",
                    "current_provider_id": None,
                    "updated_at": now,
                },
            },
        }

    def get_agents(self) -> dict[str, Any]:
        data = self.read_json("agents.json", self.default_agents)
        changed = False
        default = self.default_agents()
        for agent_type, agent_data in default["agents"].items():
            if agent_type not in data.get("agents", {}):
                data.setdefault("agents", {})[agent_type] = agent_data
                changed = True
        if changed:
            self.save_agents(data)
        return data

    def save_agents(self, data: dict[str, Any]) -> None:
        self.write_json("agents.json", data)

    def default_providers(self) -> dict[str, Any]:
        return {"schema_version": 1, "providers": []}

    def get_providers(self, agent_type: str) -> dict[str, Any]:
        return self.read_json(f"providers.{agent_type}.json", self.default_providers)

    def save_providers(self, agent_type: str, data: dict[str, Any]) -> None:
        self.write_json(f"providers.{agent_type}.json", data)

    def default_proxies(self) -> dict[str, Any]:
        return {"schema_version": 1, "proxies": {}}

    def get_proxies(self) -> dict[str, Any]:
        return self.read_json("proxies.json", self.default_proxies)

    def save_proxies(self, data: dict[str, Any]) -> None:
        self.write_json("proxies.json", data)

    def default_usage(self) -> dict[str, Any]:
        return {"schema_version": 1, "usage": {}}

    def get_usage(self, agent_type: str) -> dict[str, Any]:
        return self.read_json(f"usage.{agent_type}.json", self.default_usage)

    def save_usage(self, agent_type: str, data: dict[str, Any]) -> None:
        self.write_json(f"usage.{agent_type}.json", data)

    def default_manual_config_snapshots(self) -> dict[str, Any]:
        return {"schema_version": 1, "snapshots": {}}

    def get_manual_config_snapshots(self) -> dict[str, Any]:
        return self.read_json("manual_config_snapshots.json", self.default_manual_config_snapshots)

    def save_manual_config_snapshots(self, data: dict[str, Any]) -> None:
        self.write_json("manual_config_snapshots.json", data)
