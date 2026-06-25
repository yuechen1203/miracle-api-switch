from __future__ import annotations

from app.services.cache_store import CacheStore
from app.services.usage_service import UsageService, normalize_usage


def test_normalize_chat_completions_usage() -> None:
    usage = normalize_usage(
        {"usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12}},
        "chat/completions",
    )

    assert usage["input_tokens"] == 5
    assert usage["output_tokens"] == 7
    assert usage["total_tokens"] == 12


def test_normalize_messages_usage_with_cache_fields() -> None:
    usage = normalize_usage(
        {
            "usage": {
                "input_tokens": 11,
                "output_tokens": 13,
                "cache_creation_input_tokens": 2,
                "cache_read_input_tokens": 3,
            }
        },
        "messages",
    )

    assert usage["total_tokens"] == 24
    assert usage["cache_creation_input_tokens"] == 2
    assert usage["cache_read_input_tokens"] == 3


def test_reset_agent_usage_clears_persisted_records(tmp_path) -> None:
    service = UsageService(CacheStore(tmp_path))
    service.record_proxy_response(
        "codex",
        "provider-a",
        {"usage": {"input_tokens": 4, "output_tokens": 6}},
        "responses",
    )
    service.record_proxy_response(
        "codex",
        "provider-b",
        {"usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8}},
        "chat/completions",
    )

    reset = service.reset_agent_usage("codex")

    assert set(reset) == {"provider-a", "provider-b"}
    assert reset["provider-a"]["request_count"] == 0
    assert reset["provider-a"]["total_tokens"] == 0
    assert reset["provider-b"]["request_count"] == 0
    assert reset["provider-b"]["total_tokens"] == 0
    assert service.list_usage("codex") == reset
