from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "api_key",
    "authorization",
    "x-api-key",
    "anthropic_auth_token",
    "anthropic-token",
    "token",
    "key",
}


def mask_api_key(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 4:
        return "*" * len(value)
    if len(value) <= 8:
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
    if len(value) <= 16:
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"
    return f"{value[:8]}{'*' * 6}{value[-6:]}"


def scrub_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        scrubbed: dict[str, Any] = {}
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS or key.lower() in SENSITIVE_KEYS:
                scrubbed[key] = mask_api_key(str(item)) if item else item
            else:
                scrubbed[key] = scrub_sensitive(item)
        return scrubbed
    if isinstance(value, list):
        return [scrub_sensitive(item) for item in value]
    return value
