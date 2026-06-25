from __future__ import annotations

import json

from app.proxy.transformers import (
    build_target_url,
    stream_text_delta,
    stream_usage_payload,
    transform_request,
    transform_response,
    transform_stream_event,
)


def test_build_target_url_avoids_duplicate_v1() -> None:
    assert build_target_url("https://api.example.com/v1", "responses") == "https://api.example.com/v1/responses"
    assert (
        build_target_url("https://api.example.com/v1/chat/completions", "chat/completions")
        == "https://api.example.com/v1/chat/completions"
    )
    assert build_target_url("https://api.example.com/base", "messages") == "https://api.example.com/base/v1/messages"


def test_responses_request_to_messages_request() -> None:
    payload = transform_request(
        {
            "model": "gpt-test",
            "instructions": "be concise",
            "input": [{"role": "user", "content": "hello"}],
            "max_output_tokens": 123,
        },
        "responses",
        "messages",
    )

    assert payload["model"] == "gpt-test"
    assert payload["system"] == "be concise"
    assert payload["max_tokens"] == 123
    assert payload["messages"] == [{"role": "user", "content": "hello"}]


def test_messages_response_to_responses_response() -> None:
    payload = transform_response(
        {
            "id": "msg_1",
            "model": "claude-test",
            "content": [{"type": "text", "text": "done"}],
            "usage": {"input_tokens": 10, "output_tokens": 3},
        },
        "messages",
        "responses",
    )

    assert payload["object"] == "response"
    assert payload["output_text"] == "done"
    assert payload["usage"]["total_tokens"] == 13


def test_streaming_request_is_converted() -> None:
    payload = transform_request({"model": "x", "input": "hello", "stream": True}, "responses", "messages")

    assert payload["stream"] is True
    assert payload["messages"] == [{"role": "user", "content": "hello"}]


def test_messages_request_to_responses_converts_tools_and_tool_blocks() -> None:
    payload = transform_request(
        {
            "model": "x",
            "max_tokens": 1000,
            "stream": True,
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": "run ls"}]},
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": "toolu_1",
                            "name": "bash",
                            "input": {"command": "ls"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "ok"}],
                },
            ],
            "tools": [
                {
                    "name": "bash",
                    "description": "Run a command",
                    "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}},
                }
            ],
            "tool_choice": {"type": "auto"},
        },
        "messages",
        "responses",
    )

    assert payload["max_output_tokens"] == 1000
    assert payload["stream"] is True
    assert payload["tools"] == [
        {
            "type": "function",
            "name": "bash",
            "description": "Run a command",
            "parameters": {"type": "object", "properties": {"command": {"type": "string"}}},
        }
    ]
    assert payload["tool_choice"] == "auto"
    assert payload["input"][0] == {"role": "user", "content": "run ls"}
    assert payload["input"][1] == {
        "type": "function_call",
        "call_id": "toolu_1",
        "name": "bash",
        "arguments": '{"command":"ls"}',
    }
    assert payload["input"][2] == {"type": "function_call_output", "call_id": "toolu_1", "output": "ok"}


def test_responses_function_call_response_to_messages_tool_use() -> None:
    payload = transform_response(
        {
            "id": "resp_1",
            "model": "gpt-test",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "bash",
                    "arguments": '{"command":"pwd"}',
                }
            ],
            "usage": {"input_tokens": 11, "output_tokens": 7, "total_tokens": 18},
        },
        "responses",
        "messages",
    )

    assert payload["type"] == "message"
    assert payload["stop_reason"] == "tool_use"
    assert payload["content"] == [
        {"type": "tool_use", "id": "call_1", "name": "bash", "input": {"command": "pwd"}}
    ]
    assert payload["usage"]["input_tokens"] == 11


def _sse_payloads(frames: list[bytes]) -> list[dict[str, object]]:
    payloads: list[dict[str, object]] = []
    for frame in frames:
        for line in frame.decode("utf-8").splitlines():
            if line.startswith("data: ") and line[6:] != "[DONE]":
                payloads.append(json.loads(line[6:]))
    return payloads


def test_messages_stream_delta_to_responses_stream_event() -> None:
    frames = transform_stream_event(
        {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "hello"}},
        "content_block_delta",
        "messages",
        "responses",
    )

    payloads = _sse_payloads(frames)
    assert payloads[0]["type"] == "response.output_text.delta"
    assert payloads[0]["delta"] == "hello"


def test_responses_text_stream_to_messages_stream_events() -> None:
    state: dict[str, object] = {}
    frames: list[bytes] = []
    frames.extend(
        transform_stream_event(
            {"type": "response.content_part.added", "part": {"type": "output_text", "text": ""}},
            "response.content_part.added",
            "responses",
            "messages",
            state,
        )
    )
    frames.extend(
        transform_stream_event(
            {"type": "response.output_text.delta", "delta": "hello"},
            "response.output_text.delta",
            "responses",
            "messages",
            state,
        )
    )
    frames.extend(
        transform_stream_event(
            {"type": "response.output_text.done", "text": "hello"},
            "response.output_text.done",
            "responses",
            "messages",
            state,
        )
    )
    frames.extend(
        transform_stream_event(
            {"type": "response.completed", "response": {"usage": {"input_tokens": 3, "output_tokens": 2}}},
            "response.completed",
            "responses",
            "messages",
            state,
        )
    )

    payloads = _sse_payloads(frames)
    assert [payload["type"] for payload in payloads] == [
        "content_block_start",
        "content_block_delta",
        "content_block_stop",
        "message_delta",
        "message_stop",
    ]
    assert payloads[1]["delta"] == {"type": "text_delta", "text": "hello"}
    assert payloads[3]["usage"] == {"output_tokens": 2}


def test_responses_function_call_stream_to_messages_tool_events() -> None:
    state: dict[str, object] = {}
    frames: list[bytes] = []
    frames.extend(
        transform_stream_event(
            {
                "type": "response.output_item.added",
                "output_index": 0,
                "item": {"type": "function_call", "call_id": "call_1", "name": "bash"},
            },
            "response.output_item.added",
            "responses",
            "messages",
            state,
        )
    )
    frames.extend(
        transform_stream_event(
            {"type": "response.function_call_arguments.delta", "output_index": 0, "delta": '{"command":"pwd"}'},
            "response.function_call_arguments.delta",
            "responses",
            "messages",
            state,
        )
    )
    frames.extend(
        transform_stream_event(
            {"type": "response.function_call_arguments.done", "output_index": 0},
            "response.function_call_arguments.done",
            "responses",
            "messages",
            state,
        )
    )
    frames.extend(
        transform_stream_event(
            {"type": "response.completed", "response": {"usage": {"input_tokens": 4, "output_tokens": 5}}},
            "response.completed",
            "responses",
            "messages",
            state,
        )
    )

    payloads = _sse_payloads(frames)
    assert payloads[0]["content_block"] == {"type": "tool_use", "id": "call_1", "name": "bash", "input": {}}
    assert payloads[1]["delta"] == {"type": "input_json_delta", "partial_json": '{"command":"pwd"}'}
    assert payloads[3]["delta"]["stop_reason"] == "tool_use"


def test_stream_usage_payload_reads_anthropic_message_start() -> None:
    usage = stream_usage_payload(
        {
            "type": "message_start",
            "message": {
                "usage": {
                    "input_tokens": 8,
                    "output_tokens": 1,
                    "cache_read_input_tokens": 2,
                }
            },
        },
        "messages",
    )

    assert usage == {
        "usage": {
            "input_tokens": 8,
            "output_tokens": 1,
            "cache_read_input_tokens": 2,
        }
    }


def test_stream_text_delta_reads_chat_chunk() -> None:
    assert (
        stream_text_delta(
            {"choices": [{"delta": {"content": "chunk"}}]},
            "chat/completions",
        )
        == "chunk"
    )
