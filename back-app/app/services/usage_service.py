from __future__ import annotations

from typing import Any

from app.services.cache_store import CacheStore, utc_now


def empty_usage() -> dict[str, Any]:
    return {
        "request_count": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "last_request_at": None,
    }


def normalize_usage(raw_response: dict[str, Any], response_format: str) -> dict[str, int]:
    usage = raw_response.get("usage") or {}
    if not isinstance(usage, dict):
        usage = {}

    if response_format == "chat/completions":
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
        }

    input_tokens = int(usage.get("input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens") or 0),
        "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
    }


class UsageService:
    def __init__(self, cache: CacheStore) -> None:
        self.cache = cache

    def list_usage(self, agent_type: str) -> dict[str, Any]:
        return self.cache.get_usage(agent_type)["usage"]

    def get_usage(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        return self.list_usage(agent_type).get(provider_id, empty_usage())

    def record_proxy_response(
        self,
        agent_type: str,
        provider_id: str,
        raw_response: dict[str, Any],
        response_format: str,
    ) -> dict[str, Any]:
        data = self.cache.get_usage(agent_type)
        usage_map = data.setdefault("usage", {})
        current = usage_map.get(provider_id, empty_usage())
        delta = normalize_usage(raw_response, response_format)
        current["request_count"] = int(current.get("request_count") or 0) + 1
        for key in (
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "cache_creation_input_tokens",
            "cache_read_input_tokens",
        ):
            current[key] = int(current.get(key) or 0) + int(delta.get(key) or 0)
        current["last_request_at"] = utc_now()
        usage_map[provider_id] = current
        self.cache.save_usage(agent_type, data)
        print(
            "[usage]",
            f"agent={agent_type}",
            f"provider={provider_id}",
            f"input={delta['input_tokens']}",
            f"output={delta['output_tokens']}",
            f"total={delta['total_tokens']}",
            f"accumulated={current['total_tokens']}",
        )
        return current

    def record_request_without_usage(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        data = self.cache.get_usage(agent_type)
        usage_map = data.setdefault("usage", {})
        current = usage_map.get(provider_id, empty_usage())
        current["request_count"] = int(current.get("request_count") or 0) + 1
        current["last_request_at"] = utc_now()
        usage_map[provider_id] = current
        self.cache.save_usage(agent_type, data)
        return current

    def reset_usage(self, agent_type: str, provider_id: str) -> dict[str, Any]:
        data = self.cache.get_usage(agent_type)
        data.setdefault("usage", {})[provider_id] = empty_usage()
        self.cache.save_usage(agent_type, data)
        return data["usage"][provider_id]

    def reset_agent_usage(self, agent_type: str) -> dict[str, Any]:
        data = self.cache.get_usage(agent_type)
        usage_map = data.setdefault("usage", {})
        for provider_id in list(usage_map.keys()):
            usage_map[provider_id] = empty_usage()
        self.cache.save_usage(agent_type, data)
        return usage_map

    def delete_usage(self, agent_type: str, provider_id: str) -> None:
        data = self.cache.get_usage(agent_type)
        data.setdefault("usage", {}).pop(provider_id, None)
        self.cache.save_usage(agent_type, data)
