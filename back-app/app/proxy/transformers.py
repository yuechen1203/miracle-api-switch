from __future__ import annotations

import json
import time
import uuid
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from app.core.errors import AppError

TARGET_PATHS = {
    "chat/completions": "/v1/chat/completions",
    "responses": "/v1/responses",
    "messages": "/v1/messages",
}

KNOWN_ENDPOINT_SUFFIXES = (
    "/v1/chat/completions",
    "/chat/completions",
    "/v1/responses",
    "/responses",
    "/v1/messages",
    "/messages",
)


def normalize_format(value: str) -> str:
    return "responses" if value == "response" else value


def source_format_for_agent(agent_type: str) -> str:
    if agent_type == "codex":
        return "responses"
    if agent_type == "claude_code":
        return "messages"
    raise AppError("AGENT_NOT_FOUND", f"不支持的 Agent 类型: {agent_type}", status_code=404)


def build_target_url(base_url: str, target_format: str) -> str:
    target_format = normalize_format(target_format)
    target_path = TARGET_PATHS[target_format]
    split = urlsplit(base_url)
    base_path = split.path.rstrip("/")
    if any(base_path.endswith(suffix) for suffix in KNOWN_ENDPOINT_SUFFIXES):
        new_path = base_path
    elif base_path.endswith("/v1"):
        new_path = base_path + target_path[len("/v1") :]
    else:
        new_path = base_path + target_path
    return urlunsplit((split.scheme, split.netloc, new_path, split.query, split.fragment))


def build_auth_headers(api_key: str, target_format: str) -> dict[str, str]:
    target_format = normalize_format(target_format)
    headers = {"content-type": "application/json", "accept": "application/json"}
    if target_format == "messages":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["authorization"] = f"Bearer {api_key}"
    return headers


def transform_request(body: dict[str, Any], source_format: str, target_format: str) -> dict[str, Any]:
    source_format = normalize_format(source_format)
    target_format = normalize_format(target_format)
    if source_format == target_format:
        return dict(body)
    intermediate = request_to_intermediate(body, source_format)
    return intermediate_to_request(intermediate, target_format)


def request_to_intermediate(body: dict[str, Any], source_format: str) -> dict[str, Any]:
    if source_format == "responses":
        return responses_request_to_intermediate(body)
    if source_format == "messages":
        return messages_request_to_intermediate(body)
    if source_format == "chat/completions":
        return chat_request_to_intermediate(body)
    raise AppError("TRANSFORM_UNSUPPORTED", f"不支持的源格式: {source_format}", status_code=422)


def intermediate_to_request(intermediate: dict[str, Any], target_format: str) -> dict[str, Any]:
    if target_format == "responses":
        return intermediate_to_responses_request(intermediate)
    if target_format == "messages":
        return intermediate_to_messages_request(intermediate)
    if target_format == "chat/completions":
        return intermediate_to_chat_request(intermediate)
    raise AppError("TRANSFORM_UNSUPPORTED", f"不支持的目标格式: {target_format}", status_code=422)


def responses_request_to_intermediate(body: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    raw_input = body.get("input", [])
    if isinstance(raw_input, str):
        messages.append({"role": "user", "content": raw_input})
    elif isinstance(raw_input, list):
        for item in raw_input:
            if isinstance(item, dict):
                role = item.get("role", "user")
                messages.append({"role": role, "content": normalize_content(item.get("content", ""))})
    return {
        "model": body.get("model"),
        "system": normalize_content(body.get("instructions", "")),
        "messages": messages,
        "temperature": body.get("temperature"),
        "top_p": body.get("top_p"),
        "max_tokens": body.get("max_output_tokens") or body.get("max_tokens"),
        "stream": bool(body.get("stream", False)),
        "tools": body.get("tools"),
        "tool_choice": body.get("tool_choice"),
    }


def messages_request_to_intermediate(body: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    raw_messages = body.get("messages", []) or []
    for item in raw_messages:
        if isinstance(item, dict):
            messages.append({"role": item.get("role", "user"), "content": normalize_content(item.get("content", ""))})
    return {
        "model": body.get("model"),
        "system": normalize_content(body.get("system", "")),
        "messages": messages,
        "responses_input": anthropic_messages_to_responses_input(raw_messages),
        "temperature": body.get("temperature"),
        "top_p": body.get("top_p"),
        "max_tokens": body.get("max_tokens"),
        "stream": bool(body.get("stream", False)),
        "tools": body.get("tools"),
        "tool_choice": body.get("tool_choice"),
        "parallel_tool_calls": body.get("parallel_tool_calls"),
        "metadata": body.get("metadata"),
    }


def chat_request_to_intermediate(body: dict[str, Any]) -> dict[str, Any]:
    system_parts: list[str] = []
    messages: list[dict[str, Any]] = []
    for item in body.get("messages", []) or []:
        if not isinstance(item, dict):
            continue
        role = item.get("role", "user")
        content = normalize_content(item.get("content", ""))
        if role == "system":
            system_parts.append(content)
        else:
            messages.append({"role": role, "content": content})
    return {
        "model": body.get("model"),
        "system": "\n\n".join(part for part in system_parts if part),
        "messages": messages,
        "temperature": body.get("temperature"),
        "top_p": body.get("top_p"),
        "max_tokens": body.get("max_tokens"),
        "stream": bool(body.get("stream", False)),
        "tools": body.get("tools"),
        "tool_choice": body.get("tool_choice"),
    }


def intermediate_to_responses_request(intermediate: dict[str, Any]) -> dict[str, Any]:
    response_input = intermediate.get("responses_input")
    if not response_input:
        response_input = [
            {"role": msg.get("role", "user"), "content": msg.get("content", "")}
            for msg in intermediate.get("messages", [])
        ]
    payload: dict[str, Any] = {
        "model": intermediate.get("model"),
        "input": response_input,
    }
    optional_map = {
        "instructions": intermediate.get("system"),
        "temperature": intermediate.get("temperature"),
        "top_p": intermediate.get("top_p"),
        "max_output_tokens": intermediate.get("max_tokens"),
        "stream": intermediate.get("stream"),
        "tools": tools_to_responses(intermediate.get("tools")),
        "tool_choice": tool_choice_to_responses(intermediate.get("tool_choice")),
        "parallel_tool_calls": intermediate.get("parallel_tool_calls"),
        "metadata": intermediate.get("metadata"),
    }
    payload.update({key: value for key, value in optional_map.items() if value not in (None, "", [])})
    return payload


def intermediate_to_messages_request(intermediate: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": intermediate.get("model"),
        "max_tokens": intermediate.get("max_tokens") or 4096,
        "messages": [
            {"role": normalize_anthropic_role(msg.get("role", "user")), "content": msg.get("content", "")}
            for msg in intermediate.get("messages", [])
            if msg.get("role") != "system"
        ],
    }
    optional_map = {
        "system": intermediate.get("system"),
        "temperature": intermediate.get("temperature"),
        "top_p": intermediate.get("top_p"),
        "stream": intermediate.get("stream"),
        "tools": tools_to_messages(intermediate.get("tools")),
        "tool_choice": tool_choice_to_messages(intermediate.get("tool_choice")),
    }
    payload.update({key: value for key, value in optional_map.items() if value not in (None, "", [])})
    return payload


def intermediate_to_chat_request(intermediate: dict[str, Any]) -> dict[str, Any]:
    messages: list[dict[str, Any]] = []
    if intermediate.get("system"):
        messages.append({"role": "system", "content": intermediate["system"]})
    messages.extend(
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in intermediate.get("messages", [])
    )
    payload: dict[str, Any] = {"model": intermediate.get("model"), "messages": messages}
    optional_map = {
        "temperature": intermediate.get("temperature"),
        "top_p": intermediate.get("top_p"),
        "max_tokens": intermediate.get("max_tokens"),
        "stream": intermediate.get("stream"),
        "tools": intermediate.get("tools"),
        "tool_choice": intermediate.get("tool_choice"),
    }
    payload.update({key: value for key, value in optional_map.items() if value not in (None, "", [])})
    return payload


def transform_response(raw: dict[str, Any], target_format: str, source_format: str) -> dict[str, Any]:
    target_format = normalize_format(target_format)
    source_format = normalize_format(source_format)
    if target_format == source_format:
        return raw
    text = extract_text(raw, target_format)
    model = raw.get("model", "")
    usage = normalize_response_usage(raw, target_format)
    if source_format == "responses":
        return {
            "id": raw.get("id") or f"resp_{uuid.uuid4().hex}",
            "object": "response",
            "created_at": int(time.time()),
            "model": model,
            "output": [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": text}],
                }
            ],
            "output_text": text,
            "usage": {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
            },
        }
    if source_format == "messages":
        content = responses_output_to_anthropic_content(raw) if target_format == "responses" else [{"type": "text", "text": text}]
        return {
            "id": raw.get("id") or f"msg_{uuid.uuid4().hex}",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": content,
            "stop_reason": (
                anthropic_stop_reason_from_responses(raw, content)
                if target_format == "responses"
                else raw.get("stop_reason") or raw.get("finish_reason") or "end_turn"
            ),
            "usage": {
                "input_tokens": usage["input_tokens"],
                "output_tokens": usage["output_tokens"],
                "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
                "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
            },
        }
    if source_format == "chat/completions":
        return {
            "id": raw.get("id") or f"chatcmpl_{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": raw.get("finish_reason") or raw.get("stop_reason") or "stop",
                }
            ],
            "usage": {
                "prompt_tokens": usage["input_tokens"],
                "completion_tokens": usage["output_tokens"],
                "total_tokens": usage["total_tokens"],
            },
        }
    raise AppError("TRANSFORM_UNSUPPORTED", f"不支持的返回格式: {source_format}", status_code=422)


def normalize_content(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    if isinstance(value, dict):
        text = value.get("text") or value.get("content")
        if isinstance(text, str):
            return text
    return str(value)


def normalize_anthropic_role(role: str) -> str:
    return "assistant" if role == "assistant" else "user"


def normalize_responses_role(role: Any) -> str:
    return "assistant" if role == "assistant" else "user"


def anthropic_messages_to_responses_input(raw_messages: Any) -> list[dict[str, Any]]:
    input_items: list[dict[str, Any]] = []
    if not isinstance(raw_messages, list):
        return input_items

    for message in raw_messages:
        if not isinstance(message, dict):
            continue
        role = normalize_responses_role(message.get("role", "user"))
        content = message.get("content", "")
        if isinstance(content, str):
            if content:
                input_items.append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            text = normalize_content(content)
            if text:
                input_items.append({"role": role, "content": text})
            continue

        text_parts: list[str] = []

        def flush_text() -> None:
            text = "\n".join(part for part in text_parts if part)
            text_parts.clear()
            if text:
                input_items.append({"role": role, "content": text})

        for block in content:
            if not isinstance(block, dict):
                text_parts.append(normalize_content(block))
                continue

            block_type = block.get("type")
            if block_type == "text":
                text_parts.append(normalize_content(block.get("text", "")))
                continue

            if block_type == "tool_use":
                flush_text()
                input_items.append(
                    {
                        "type": "function_call",
                        "call_id": str(block.get("id") or f"call_{uuid.uuid4().hex}"),
                        "name": str(block.get("name") or "tool"),
                        "arguments": json_dumps_compact(block.get("input") or {}),
                    }
                )
                continue

            if block_type == "tool_result":
                flush_text()
                output = normalize_content(block.get("content", ""))
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": str(block.get("tool_use_id") or block.get("id") or ""),
                        "output": output,
                    }
                )
                continue

            fallback = normalize_content(block)
            if fallback:
                text_parts.append(fallback)

        flush_text()

    return input_items


def tools_to_responses(tools: Any) -> list[dict[str, Any]] | None:
    if not isinstance(tools, list):
        return None
    converted: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if tool.get("type") == "function" and tool.get("name"):
            item = dict(tool)
            if "parameters" not in item and isinstance(item.get("input_schema"), dict):
                item["parameters"] = item.pop("input_schema")
            converted.append(item)
            continue
        name = tool.get("name")
        if not name:
            continue
        converted.append(
            {
                "type": "function",
                "name": str(name),
                "description": str(tool.get("description") or ""),
                "parameters": tool.get("input_schema") or tool.get("parameters") or {"type": "object", "properties": {}},
            }
        )
    return converted or None


def tools_to_messages(tools: Any) -> list[dict[str, Any]] | None:
    if not isinstance(tools, list):
        return None
    converted: list[dict[str, Any]] = []
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if tool.get("input_schema") and tool.get("name"):
            converted.append(dict(tool))
            continue
        if tool.get("type") == "function" and tool.get("name"):
            converted.append(
                {
                    "name": str(tool.get("name")),
                    "description": str(tool.get("description") or ""),
                    "input_schema": tool.get("parameters") or {"type": "object", "properties": {}},
                }
            )
    return converted or None


def tool_choice_to_responses(choice: Any) -> Any:
    if choice in (None, "", []):
        return None
    if isinstance(choice, str):
        return choice
    if not isinstance(choice, dict):
        return choice
    choice_type = choice.get("type")
    if choice_type == "auto":
        return "auto"
    if choice_type == "any":
        return "required"
    if choice_type == "none":
        return "none"
    if choice_type == "tool" and choice.get("name"):
        return {"type": "function", "name": choice["name"]}
    return choice


def tool_choice_to_messages(choice: Any) -> Any:
    if choice in (None, "", []):
        return None
    if isinstance(choice, str):
        if choice == "required":
            return {"type": "any"}
        if choice in {"auto", "none"}:
            return {"type": choice}
        return choice
    if isinstance(choice, dict) and choice.get("type") == "function" and choice.get("name"):
        return {"type": "tool", "name": choice["name"]}
    return choice


def json_dumps_compact(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def json_loads_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def responses_output_to_anthropic_content(raw: dict[str, Any]) -> list[dict[str, Any]]:
    content: list[dict[str, Any]] = []
    for item in raw.get("output", []) or []:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "message":
            text = normalize_content(item.get("content", ""))
            if text:
                content.append({"type": "text", "text": text})
            continue
        if item_type == "function_call":
            content.append(
                {
                    "type": "tool_use",
                    "id": str(item.get("call_id") or item.get("id") or f"toolu_{uuid.uuid4().hex}"),
                    "name": str(item.get("name") or "tool"),
                    "input": json_loads_object(item.get("arguments")),
                }
            )

    if not content:
        text = extract_text(raw, "responses")
        if text:
            content.append({"type": "text", "text": text})
    return content


def anthropic_stop_reason_from_responses(raw: dict[str, Any], content: list[dict[str, Any]]) -> str:
    if any(item.get("type") == "tool_use" for item in content):
        return "tool_use"
    status = raw.get("status")
    if status in {"incomplete", "failed", "cancelled"}:
        return "max_tokens" if status == "incomplete" else "end_turn"
    return raw.get("stop_reason") or raw.get("finish_reason") or "end_turn"


def extract_text(raw: dict[str, Any], response_format: str) -> str:
    if response_format == "chat/completions":
        choices = raw.get("choices") or []
        if choices and isinstance(choices[0], dict):
            return normalize_content((choices[0].get("message") or {}).get("content", ""))
        return ""
    if response_format == "messages":
        return normalize_content(raw.get("content", ""))
    if response_format == "responses":
        if raw.get("output_text"):
            return normalize_content(raw["output_text"])
        parts: list[str] = []
        for item in raw.get("output", []) or []:
            if not isinstance(item, dict):
                continue
            parts.append(normalize_content(item.get("content", "")))
        return "\n".join(part for part in parts if part)
    return ""


def normalize_response_usage(raw: dict[str, Any], response_format: str) -> dict[str, int]:
    usage = raw.get("usage") or {}
    if response_format == "chat/completions":
        input_tokens = int(usage.get("prompt_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or 0)
    else:
        input_tokens = int(usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("output_tokens") or 0)
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": int(usage.get("total_tokens") or input_tokens + output_tokens),
        "cache_creation_input_tokens": int(usage.get("cache_creation_input_tokens") or 0),
        "cache_read_input_tokens": int(usage.get("cache_read_input_tokens") or 0),
    }


def convert_error_response(message: str, source_format: str, code: str = "PROXY_TARGET_FAILED") -> dict[str, Any]:
    source_format = normalize_format(source_format)
    if source_format == "messages":
        return {"type": "error", "error": {"type": "api_error", "message": message}}
    return {"error": {"message": message, "type": "api_error", "code": code}}


def sse_format_event(data: dict[str, Any] | str, event: str | None = None) -> bytes:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    if isinstance(data, str):
        lines.append(f"data: {data}")
    else:
        lines.append("data: " + json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    lines.append("")
    return ("\n".join(lines) + "\n").encode("utf-8")


def stream_text_delta(data: dict[str, Any], response_format: str, event_name: str | None = None) -> str:
    response_format = normalize_format(response_format)
    if response_format == "chat/completions":
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            delta = choices[0].get("delta") or {}
            return normalize_content(delta.get("content", ""))
        return ""
    if response_format == "responses":
        event_type = str(data.get("type") or event_name or "")
        if event_type in {"response.output_text.delta", "response.refusal.delta"}:
            return normalize_content(data.get("delta", ""))
        if event_type == "response.output_item.delta":
            return normalize_content(data.get("delta", ""))
        return ""
    if response_format == "messages":
        event_type = str(data.get("type") or event_name or "")
        if event_type == "content_block_delta":
            delta = data.get("delta") or {}
            if isinstance(delta, dict):
                return normalize_content(delta.get("text", ""))
        return ""
    return ""


def stream_usage_payload(data: dict[str, Any], response_format: str) -> dict[str, Any] | None:
    response_format = normalize_format(response_format)
    if response_format == "chat/completions":
        usage = data.get("usage")
        return {"usage": usage} if isinstance(usage, dict) else None
    if response_format == "responses":
        usage = data.get("usage")
        if isinstance(usage, dict):
            return {"usage": usage}
        response = data.get("response")
        if isinstance(response, dict) and isinstance(response.get("usage"), dict):
            return {"usage": response["usage"]}
        return None
    if response_format == "messages":
        usage = data.get("usage")
        if isinstance(usage, dict):
            return {"usage": usage}
        message = data.get("message")
        if isinstance(message, dict) and isinstance(message.get("usage"), dict):
            return {"usage": message["usage"]}
        return {"usage": usage} if isinstance(usage, dict) else None
    return None


def stream_event_done(data: dict[str, Any], event_name: str | None, response_format: str) -> bool:
    return _stream_event_done(data, event_name, normalize_format(response_format))


def transform_stream_event(
    data: dict[str, Any],
    event_name: str | None,
    target_format: str,
    source_format: str,
    state: dict[str, Any] | None = None,
) -> list[bytes]:
    target_format = normalize_format(target_format)
    source_format = normalize_format(source_format)
    if target_format == source_format:
        return [sse_format_event(data, event_name)]
    if target_format == "responses" and source_format == "messages":
        return _responses_stream_event_to_messages_frames(data, event_name, state)

    text = stream_text_delta(data, target_format, event_name)
    is_done = _stream_event_done(data, event_name, target_format)
    frames: list[bytes] = []

    if text:
        frames.extend(_stream_delta_frames(text, source_format, state))
    if is_done:
        frames.extend(_stream_done_frames(source_format, state))
    return frames


def stream_start_frames(source_format: str) -> list[bytes]:
    source_format = normalize_format(source_format)
    now = int(time.time())
    if source_format == "chat/completions":
        return [
            sse_format_event(
                {
                    "id": f"chatcmpl_{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": now,
                    "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
                }
            )
        ]
    if source_format == "responses":
        response_id = f"resp_{uuid.uuid4().hex}"
        response = {
            "id": response_id,
            "object": "response",
            "created_at": now,
            "status": "in_progress",
            "output": [],
        }
        return [
            sse_format_event({"type": "response.created", "response": response}, "response.created"),
            sse_format_event({"type": "response.in_progress", "response": response}, "response.in_progress"),
        ]
    if source_format == "messages":
        message_id = f"msg_{uuid.uuid4().hex}"
        return [
            sse_format_event(
                {
                    "type": "message_start",
                    "message": {
                        "id": message_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": "",
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                },
                "message_start",
            )
        ]
    return []


def stream_done_frames(source_format: str, state: dict[str, Any] | None = None) -> list[bytes]:
    return _stream_done_frames(normalize_format(source_format), state)


def _stream_event_done(data: dict[str, Any], event_name: str | None, response_format: str) -> bool:
    event_type = str(data.get("type") or event_name or "")
    if response_format == "chat/completions":
        choices = data.get("choices") or []
        if choices and isinstance(choices[0], dict):
            return bool(choices[0].get("finish_reason"))
        return False
    if response_format == "responses":
        return event_type in {"response.completed", "response.failed", "response.cancelled", "response.incomplete"}
    if response_format == "messages":
        return event_type == "message_stop"
    return False


def _stream_delta_frames(text: str, source_format: str, state: dict[str, Any] | None = None) -> list[bytes]:
    if source_format == "chat/completions":
        return [
            sse_format_event(
                {
                    "id": f"chatcmpl_{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}],
                }
            )
        ]
    if source_format == "responses":
        return [
            sse_format_event(
                {
                    "type": "response.output_text.delta",
                    "delta": text,
                    "output_index": 0,
                    "content_index": 0,
                },
                "response.output_text.delta",
            )
        ]
    if source_format == "messages":
        frames = _ensure_messages_text_block(state)
        index = _messages_open_index(state)
        frames.append(
            sse_format_event(
                {
                    "type": "content_block_delta",
                    "index": index,
                    "delta": {"type": "text_delta", "text": text},
                },
                "content_block_delta",
            )
        )
        return frames
    return []


def _responses_stream_event_to_messages_frames(
    data: dict[str, Any],
    event_name: str | None,
    state: dict[str, Any] | None,
) -> list[bytes]:
    event_type = str(data.get("type") or event_name or "")
    frames: list[bytes] = []

    if event_type == "response.output_item.added":
        item = data.get("item") if isinstance(data.get("item"), dict) else {}
        if item.get("type") == "function_call":
            frames.extend(_start_messages_tool_block(state, data, item))
        return frames

    if event_type == "response.output_item.done":
        item = data.get("item") if isinstance(data.get("item"), dict) else {}
        if item.get("type") == "function_call":
            frames.extend(_close_messages_block(state, expected_type="tool_use"))
        return frames

    if event_type == "response.content_part.added":
        part = data.get("part") if isinstance(data.get("part"), dict) else data.get("content_part")
        if isinstance(part, dict) and part.get("type") in {"output_text", "refusal"}:
            frames.extend(_ensure_messages_text_block(state))
        return frames

    if event_type in {"response.output_text.delta", "response.refusal.delta"}:
        delta = normalize_content(data.get("delta", ""))
        if delta:
            frames.extend(_stream_delta_frames(delta, "messages", state))
        return frames

    if event_type in {"response.output_text.done", "response.content_part.done"}:
        frames.extend(_close_messages_block(state, expected_type="text"))
        return frames

    if event_type == "response.function_call_arguments.delta":
        frames.extend(_ensure_messages_tool_block(state, data))
        partial_json = normalize_content(data.get("delta", ""))
        if partial_json:
            _mark_tool_argument_delta_seen(state, data)
            frames.append(
                sse_format_event(
                    {
                        "type": "content_block_delta",
                        "index": _messages_open_index(state),
                        "delta": {"type": "input_json_delta", "partial_json": partial_json},
                    },
                    "content_block_delta",
                )
            )
        return frames

    if event_type == "response.function_call_arguments.done":
        frames.extend(_ensure_messages_tool_block(state, data))
        arguments = normalize_content(data.get("arguments", ""))
        if arguments and not _tool_argument_delta_seen(state, data):
            frames.append(
                sse_format_event(
                    {
                        "type": "content_block_delta",
                        "index": _messages_open_index(state),
                        "delta": {"type": "input_json_delta", "partial_json": arguments},
                    },
                    "content_block_delta",
                )
            )
        frames.extend(_close_messages_block(state, expected_type="tool_use"))
        return frames

    if event_type == "response.failed":
        error = data.get("response", {}).get("error") if isinstance(data.get("response"), dict) else data.get("error")
        message = error.get("message") if isinstance(error, dict) else "Responses stream failed"
        return [
            sse_format_event(
                {"type": "error", "error": {"type": "api_error", "message": str(message)}},
                "error",
            )
        ]

    if _stream_event_done(data, event_name, "responses"):
        frames.extend(_close_messages_block(state))
        frames.extend(_messages_message_delta_frames(data, state))
        frames.append(sse_format_event({"type": "message_stop"}, "message_stop"))
        if state is not None:
            state["done_sent"] = True
        return frames

    return frames


def _ensure_messages_text_block(state: dict[str, Any] | None) -> list[bytes]:
    if state is None:
        return [
            sse_format_event(
                {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
                "content_block_start",
            )
        ]
    if state.get("open_block_type") == "text":
        return []
    frames = _close_messages_block(state)
    index = _next_messages_block_index(state)
    state["open_block_index"] = index
    state["open_block_type"] = "text"
    frames.append(
        sse_format_event(
            {"type": "content_block_start", "index": index, "content_block": {"type": "text", "text": ""}},
            "content_block_start",
        )
    )
    return frames


def _ensure_messages_tool_block(state: dict[str, Any] | None, data: dict[str, Any]) -> list[bytes]:
    if state is None:
        return [
            sse_format_event(
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "tool_use", "id": _response_tool_call_id(data), "name": "tool", "input": {}},
                },
                "content_block_start",
            )
        ]
    key = _response_item_key(data)
    tool_blocks = state.setdefault("tool_blocks", {})
    existing_index = tool_blocks.get(key)
    if existing_index is not None and state.get("open_block_index") == existing_index:
        return []
    return _start_messages_tool_block(state, data, {})


def _start_messages_tool_block(
    state: dict[str, Any] | None,
    data: dict[str, Any],
    item: dict[str, Any],
) -> list[bytes]:
    tool_id = str(item.get("call_id") or item.get("id") or _response_tool_call_id(data))
    name = str(item.get("name") or data.get("name") or "tool")
    if state is None:
        index = 0
        return [
            sse_format_event(
                {
                    "type": "content_block_start",
                    "index": index,
                    "content_block": {"type": "tool_use", "id": tool_id, "name": name, "input": {}},
                },
                "content_block_start",
            )
        ]
    frames = _close_messages_block(state)
    index = _next_messages_block_index(state)
    state["open_block_index"] = index
    state["open_block_type"] = "tool_use"
    state["tool_seen"] = True
    state.setdefault("tool_blocks", {})[_response_item_key(data, item)] = index
    state.setdefault("tool_call_ids", {})[_response_item_key(data, item)] = tool_id
    frames.append(
        sse_format_event(
            {
                "type": "content_block_start",
                "index": index,
                "content_block": {"type": "tool_use", "id": tool_id, "name": name, "input": {}},
            },
            "content_block_start",
        )
    )
    return frames


def _close_messages_block(
    state: dict[str, Any] | None,
    expected_type: str | None = None,
) -> list[bytes]:
    if state is None:
        return [sse_format_event({"type": "content_block_stop", "index": 0}, "content_block_stop")]
    index = state.get("open_block_index")
    block_type = state.get("open_block_type")
    if index is None:
        return []
    if expected_type is not None and block_type != expected_type:
        return []
    state["open_block_index"] = None
    state["open_block_type"] = None
    return [sse_format_event({"type": "content_block_stop", "index": index}, "content_block_stop")]


def _messages_open_index(state: dict[str, Any] | None) -> int:
    if state is None:
        return 0
    return int(state.get("open_block_index") or 0)


def _next_messages_block_index(state: dict[str, Any]) -> int:
    index = int(state.get("next_block_index") or 0)
    state["next_block_index"] = index + 1
    return index


def _response_item_key(data: dict[str, Any], item: dict[str, Any] | None = None) -> str:
    if data.get("output_index") is not None:
        return str(data["output_index"])
    item = item or {}
    return str(data.get("item_id") or item.get("id") or item.get("call_id") or data.get("call_id") or "0")


def _response_tool_call_id(data: dict[str, Any]) -> str:
    return str(data.get("call_id") or data.get("item_id") or f"call_{uuid.uuid4().hex}")


def _tool_argument_delta_seen(state: dict[str, Any] | None, data: dict[str, Any]) -> bool:
    if state is None:
        return False
    return _response_item_key(data) in state.setdefault("tool_argument_delta_seen", set())


def _mark_tool_argument_delta_seen(state: dict[str, Any] | None, data: dict[str, Any]) -> None:
    if state is not None:
        state.setdefault("tool_argument_delta_seen", set()).add(_response_item_key(data))


def _messages_message_delta_frames(data: dict[str, Any], state: dict[str, Any] | None) -> list[bytes]:
    response = data.get("response") if isinstance(data.get("response"), dict) else {}
    usage = response.get("usage") if isinstance(response.get("usage"), dict) else data.get("usage")
    payload: dict[str, Any] = {
        "type": "message_delta",
        "delta": {
            "stop_reason": "tool_use" if state is not None and state.get("tool_seen") else "end_turn",
            "stop_sequence": None,
        },
    }
    if isinstance(usage, dict):
        normalized = normalize_response_usage({"usage": usage}, "responses")
        payload["usage"] = {"output_tokens": normalized["output_tokens"]}
    return [sse_format_event(payload, "message_delta")]


def _stream_usage_frames(normalized: dict[str, int], source_format: str) -> list[bytes]:
    if source_format == "chat/completions":
        return [
            sse_format_event(
                {
                    "id": f"chatcmpl_{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [],
                    "usage": {
                        "prompt_tokens": normalized["input_tokens"],
                        "completion_tokens": normalized["output_tokens"],
                        "total_tokens": normalized["total_tokens"],
                    },
                }
            )
        ]
    if source_format == "responses":
        return [
            sse_format_event(
                {
                    "type": "response.completed",
                    "response": {
                        "id": f"resp_{uuid.uuid4().hex}",
                        "object": "response",
                        "created_at": int(time.time()),
                        "usage": {
                            "input_tokens": normalized["input_tokens"],
                            "output_tokens": normalized["output_tokens"],
                            "total_tokens": normalized["total_tokens"],
                        },
                    },
                },
                "response.completed",
            )
        ]
    if source_format == "messages":
        return [
            sse_format_event(
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {
                        "output_tokens": normalized["output_tokens"],
                    },
                },
                "message_delta",
            )
        ]
    return []


def _stream_done_frames(source_format: str, state: dict[str, Any] | None = None) -> list[bytes]:
    if source_format == "chat/completions":
        return [
            sse_format_event(
                {
                    "id": f"chatcmpl_{uuid.uuid4().hex}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
            ),
            sse_format_event("[DONE]"),
        ]
    if source_format == "responses":
        return [
            sse_format_event(
                {
                    "type": "response.output_text.done",
                    "text": "",
                    "output_index": 0,
                    "content_index": 0,
                },
                "response.output_text.done",
            ),
            sse_format_event(
                {
                    "type": "response.completed",
                    "response": {
                        "id": f"resp_{uuid.uuid4().hex}",
                        "object": "response",
                        "created_at": int(time.time()),
                        "status": "completed",
                    },
                },
                "response.completed",
            ),
            sse_format_event({"type": "done"}, "done"),
        ]
    if source_format == "messages":
        frames = _close_messages_block(state)
        frames.append(
            sse_format_event(
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                },
                "message_delta",
            )
        )
        frames.append(sse_format_event({"type": "message_stop"}, "message_stop"))
        if state is not None:
            state["done_sent"] = True
        return frames
    return []
