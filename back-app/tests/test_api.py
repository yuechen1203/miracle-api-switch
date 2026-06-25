from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app.app_context import AppContext


def test_api_create_provider_and_dry_run_apply(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MIRACLE_WORKSPACE_DIR", str(tmp_path))
    from app.main import create_app

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

    app = create_app(AppContext(workspace_root=tmp_path))
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["success"] is True

    path_response = client.put("/api/agents/codex/config-path", json={"config_path": str(config_file)})
    assert path_response.status_code == 200
    assert path_response.json()["data"]["status"] == "installed"

    provider_response = client.post(
        "/api/agents/codex/providers",
        json={
            "display_name": "Provider A",
            "api_key": "sk-test-1234",
            "base_url": "https://api.example.com",
            "model": "model-a",
            "proxy_enabled": False,
        },
    )
    assert provider_response.status_code == 201
    provider = provider_response.json()["data"]
    assert provider["api_key_masked"] == "sk-t****1234"
    assert "api_key" not in provider

    key_response = client.get(f"/api/agents/codex/providers/{provider['id']}/api-key")
    assert key_response.status_code == 200
    assert key_response.json()["data"]["api_key"] == "sk-test-1234"

    apply_response = client.post(
        f"/api/agents/codex/providers/{provider['id']}/apply",
        json={"dry_run": True, "start_proxy": False},
    )
    assert apply_response.status_code == 200
    apply_data = apply_response.json()["data"]
    assert apply_data["dry_run"] is True
    assert apply_data["write_result"]["changed_fields"]["model"] == "model-a"
    assert apply_data["write_result"]["backup_path"] is None

    real_apply_response = client.post(
        f"/api/agents/codex/providers/{provider['id']}/apply",
        json={"dry_run": False, "start_proxy": False},
    )
    assert real_apply_response.status_code == 200

    check_response = client.get("/api/agents/codex/config-check")
    assert check_response.status_code == 200
    check = check_response.json()["data"]
    assert check["status"] == "matched"
    assert check["is_match"] is True
    assert check["current_config"]["base_url"] == "https://api.example.com"
    assert check["current_config"]["api_key_masked"] == "sk-t****1234"
    assert check["current_config"]["model"] == "model-a"
    assert check["current_config"]["model_provider"] == "miracle"

    config_file.write_text(config_file.read_text(encoding="utf-8").replace("model-a", "model-b"), encoding="utf-8")
    mismatch_response = client.get("/api/agents/codex/config-check")
    assert mismatch_response.status_code == 200
    mismatch = mismatch_response.json()["data"]
    assert mismatch["status"] == "mismatched"
    assert mismatch["is_match"] is False
    assert "model" in mismatch["mismatched_fields"]

    config_file.write_text(config_file.read_text(encoding="utf-8").replace('model_provider = "miracle"', 'model_provider = "Sample"'), encoding="utf-8")
    provider_mismatch_response = client.get("/api/agents/codex/config-check")
    assert provider_mismatch_response.status_code == 200
    provider_mismatch = provider_mismatch_response.json()["data"]
    assert provider_mismatch["status"] == "mismatched"
    assert "model_provider" in provider_mismatch["mismatched_fields"]


def test_delete_current_codex_provider_restores_manual_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MIRACLE_WORKSPACE_DIR", str(tmp_path))
    from app.main import create_app

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
model_provider = "Manual"
model = "manual-model"

[model_providers.Manual]
name = "Manual"
base_url = "https://manual.example.com"
wire_api = "responses"
experimental_bearer_token = "manual-token"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    app = create_app(AppContext(workspace_root=tmp_path))
    client = TestClient(app)
    assert client.put("/api/agents/codex/config-path", json={"config_path": str(config_file)}).status_code == 200
    provider = client.post(
        "/api/agents/codex/providers",
        json={
            "display_name": "Provider A",
            "api_key": "sk-test-1234",
            "base_url": "https://api.example.com",
            "model": "model-a",
            "proxy_enabled": False,
        },
    ).json()["data"]
    assert client.post(
        f"/api/agents/codex/providers/{provider['id']}/apply",
        json={"dry_run": False, "start_proxy": False},
    ).status_code == 200

    delete_response = client.delete(f"/api/agents/codex/providers/{provider['id']}")

    assert delete_response.status_code == 200
    data = delete_response.json()["data"]
    assert data["restore_result"]["restored"] is True
    restored = config_file.read_text(encoding="utf-8")
    assert 'model_provider = "Manual"' in restored
    assert 'model = "manual-model"' in restored
    assert 'experimental_bearer_token = "manual-token"' in restored
    agent = client.get("/api/agents/codex").json()["data"]
    assert agent["current_provider_id"] is None


def test_delete_current_claude_provider_restores_manual_config(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MIRACLE_WORKSPACE_DIR", str(tmp_path))
    from app.main import create_app

    config_file = tmp_path / "settings.json"
    config_file.write_text(
        """
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "manual-token",
    "ANTHROPIC_BASE_URL": "https://manual.example.com",
    "ANTHROPIC_MODEL": "manual-model",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "manual-haiku",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "manual-sonnet",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "manual-opus",
    "CLAUDE_CODE_SUBAGENT_MODEL": "manual-subagent"
  }
}
""".strip()
        + "\n",
        encoding="utf-8",
    )

    app = create_app(AppContext(workspace_root=tmp_path))
    client = TestClient(app)
    assert client.put("/api/agents/claude_code/config-path", json={"config_path": str(config_file)}).status_code == 200
    provider = client.post(
        "/api/agents/claude_code/providers",
        json={
            "display_name": "Claude Provider",
            "api_key": "sk-claude",
            "base_url": "https://api.example.com",
            "model": "managed-model",
            "proxy_enabled": False,
        },
    ).json()["data"]
    assert client.post(
        f"/api/agents/claude_code/providers/{provider['id']}/apply",
        json={"dry_run": False, "start_proxy": False},
    ).status_code == 200

    delete_response = client.delete(f"/api/agents/claude_code/providers/{provider['id']}")

    assert delete_response.status_code == 200
    data = delete_response.json()["data"]
    assert data["restore_result"]["restored"] is True
    restored = config_file.read_text(encoding="utf-8")
    assert '"ANTHROPIC_AUTH_TOKEN": "manual-token"' in restored
    assert '"ANTHROPIC_BASE_URL": "https://manual.example.com"' in restored
    assert '"ANTHROPIC_MODEL": "manual-model"' in restored
    assert '"CLAUDE_CODE_SUBAGENT_MODEL": "manual-subagent"' in restored
    agent = client.get("/api/agents/claude_code").json()["data"]
    assert agent["current_provider_id"] is None


def test_claude_proxy_provider_keeps_auth_token(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MIRACLE_WORKSPACE_DIR", str(tmp_path))
    from app.main import create_app

    config_file = tmp_path / "settings.json"
    config_file.write_text('{"env": {}}\n', encoding="utf-8")

    app = create_app(AppContext(workspace_root=tmp_path))
    client = TestClient(app)
    assert client.put("/api/agents/claude_code/config-path", json={"config_path": str(config_file)}).status_code == 200
    provider = client.post(
        "/api/agents/claude_code/providers",
        json={
            "display_name": "Claude Proxy",
            "api_key": "sk-claude-proxy",
            "base_url": "https://api.example.com",
            "model": "managed-model",
            "proxy_enabled": True,
            "proxy_port": 5555,
            "target_format": "messages",
        },
    ).json()["data"]

    apply_response = client.post(
        f"/api/agents/claude_code/providers/{provider['id']}/apply",
        json={"dry_run": False, "start_proxy": False},
    )
    assert apply_response.status_code == 200

    document = json.loads(config_file.read_text(encoding="utf-8"))
    assert document["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-claude-proxy"
    assert document["env"]["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:5555"
    check = client.get("/api/agents/claude_code/config-check").json()["data"]
    assert check["status"] == "matched"
    assert check["current_config"]["has_api_key"] is True
