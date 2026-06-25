from __future__ import annotations

import json

import tomlkit

from app.proxy.manager import ProxyManager
from app.services.cache_store import CacheStore
from app.services.config_writer import ConfigWriter
from app.services.usage_service import UsageService


def make_writer(tmp_path):
    cache = CacheStore(workspace_root=tmp_path)
    usage = UsageService(cache)
    proxy_manager = ProxyManager(cache, usage)
    return ConfigWriter(cache, proxy_manager)


def base_provider(agent_type: str, proxy_enabled: bool = False) -> dict:
    return {
        "id": "provider-1",
        "agent_type": agent_type,
        "display_name": "Test Provider",
        "api_key": "sk-test",
        "base_url": "https://api.example.com",
        "model": "model-test",
        "proxy_enabled": proxy_enabled,
        "proxy_port": 5555 if proxy_enabled else None,
        "target_format": "messages" if proxy_enabled else None,
    }


def test_apply_codex_provider_updates_common_provider(tmp_path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
model_provider = "Sample"
model = ""

[model_providers.Sample]
name = "Sample"
base_url = ""
wire_api = ""
experimental_bearer_token = ""
""".strip()
        + "\n",
        encoding="utf-8",
    )

    writer = make_writer(tmp_path)
    result = writer.apply_provider(
        {"resolved_config_file": str(config_file)},
        base_provider("codex"),
    )

    document = tomlkit.parse(config_file.read_text(encoding="utf-8"))
    assert result["backup_path"]
    assert document["model_provider"] == "miracle"
    assert document["model"] == "model-test"
    assert document["model_providers"]["miracle"]["base_url"] == "https://api.example.com"
    assert document["model_providers"]["miracle"]["experimental_bearer_token"] == "sk-test"
    assert "env_key" not in document["model_providers"]["miracle"]


def test_apply_claude_provider_updates_env_fields(tmp_path) -> None:
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps({"language": "zh-CN", "env": {}}), encoding="utf-8")

    writer = make_writer(tmp_path)
    result = writer.apply_provider(
        {"resolved_config_file": str(config_file)},
        base_provider("claude_code", proxy_enabled=True),
    )

    document = json.loads(config_file.read_text(encoding="utf-8"))
    assert result["backup_path"]
    assert document["language"] == "zh-CN"
    assert document["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-test"
    assert document["env"]["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:5555"
    assert document["env"]["ANTHROPIC_MODEL"] == "model-test"
    assert document["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "model-test"
