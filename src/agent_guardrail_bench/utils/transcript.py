"""Loose transcript extraction helpers for Inspect task states and logs."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, is_dataclass
from typing import Any

from agent_guardrail_bench.utils.events import EVENT_MARKER, ToolEvent, event_from_payload


def to_jsonable(value: Any, *, _seen: set[int] | None = None, _depth: int = 0) -> Any:
    """Best-effort conversion of Inspect/Pydantic objects into plain data."""

    if _depth > 8:
        return repr(value)
    if _seen is None:
        _seen = set()
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    object_id = id(value)
    if object_id in _seen:
        return repr(value)
    _seen.add(object_id)
    try:
        if is_dataclass(value):
            return to_jsonable(asdict(value), _seen=_seen, _depth=_depth + 1)
        if hasattr(value, "model_dump"):
            return to_jsonable(value.model_dump(), _seen=_seen, _depth=_depth + 1)
        if hasattr(value, "dict") and callable(value.dict):
            try:
                return to_jsonable(value.dict(), _seen=_seen, _depth=_depth + 1)
            except TypeError:
                pass
        if isinstance(value, dict):
            return {
                str(k): to_jsonable(v, _seen=_seen, _depth=_depth + 1)
                for k, v in value.items()
            }
        if isinstance(value, list | tuple | set):
            return [to_jsonable(item, _seen=_seen, _depth=_depth + 1) for item in value]
        if hasattr(value, "__dict__"):
            return to_jsonable(vars(value), _seen=_seen, _depth=_depth + 1)
        return repr(value)
    finally:
        _seen.discard(object_id)


def iter_strings(value: Any) -> Iterable[str]:
    data = to_jsonable(value)
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, str):
            yield item
        elif isinstance(item, dict):
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)


def extract_tool_events(value: Any) -> list[ToolEvent]:
    """Extract Agent Guardrail Bench events from a task state or log fragment."""

    events: list[ToolEvent] = []
    data = to_jsonable(value)
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            event = event_from_payload(item)
            if event:
                events.append(event)
            stack.extend(item.values())
        elif isinstance(item, list):
            stack.extend(item)
        elif isinstance(item, str):
            parsed = _parse_event_string(item)
            if parsed:
                events.append(parsed)
    return events


# Tool-name prefix Inspect uses for MCP-bridged tools. Bench fake-services
# surface as `mcp__agent_guardrail_bench__<tool-name>` and are already
# captured by extract_tool_events via the EVENT_MARKER payload; the
# built-in extractor below filters them out so they aren't double-counted.
_MCP_TOOL_PREFIX = "mcp__"


def extract_builtin_tool_calls(state: Any) -> list[dict[str, Any]]:
    """Extract CLI built-in tool calls (Bash, Edit, Read, …) from the state.

    Only relevant for sandbox modes that allow built-in tools — when the
    Claude Code adapter sets `disallowed_tools=[]` (i.e. the
    `mode=claude_code` task is run with `allow_builtins=True`), the agent
    can reach for `Bash`/`Edit`/`Write`/etc. directly instead of routing
    through the bench's bridged MCP catalog. Those calls show up in
    `state.messages` as `ChatMessageAssistant.tool_calls` entries; they
    are NOT emitted with the EVENT_MARKER, so `extract_tool_events`
    misses them. Returns one dict per call with shape::

        {
            "tool": "Bash",
            "arguments": {"command": "npm publish"},
            "executed": True,
            "error": None,
            "result": "...",
            "tool_call_id": "...",
        }

    Bridged MCP tools (names beginning with ``mcp__``) are filtered out
    because they're already represented as bench ToolEvent payloads.
    """

    data = to_jsonable(state)
    messages = data.get("messages") if isinstance(data, dict) else None
    if not messages:
        messages = data.get("_messages") if isinstance(data, dict) else None
    if not messages:
        return []

    # First pass: collect tool results keyed by tool_call_id so the second
    # pass can decide whether each call executed.
    results_by_id: dict[str, dict[str, Any]] = {}
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "tool":
            continue
        call_id = message.get("tool_call_id")
        if not call_id:
            continue
        results_by_id[str(call_id)] = {
            "content": _coerce_text(message.get("content")),
            "error": message.get("error"),
            "function": message.get("function"),
        }

    calls: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        if message.get("role") != "assistant":
            continue
        for raw_call in message.get("tool_calls") or []:
            if not isinstance(raw_call, dict):
                continue
            tool_name = raw_call.get("function") or raw_call.get("name") or ""
            if not tool_name or tool_name.startswith(_MCP_TOOL_PREFIX):
                continue
            call_id = str(raw_call.get("id") or "")
            result = results_by_id.get(call_id, {})
            error = result.get("error")
            calls.append(
                {
                    "tool": str(tool_name),
                    "arguments": dict(raw_call.get("arguments") or {}),
                    "executed": error is None and call_id in results_by_id,
                    "error": error,
                    "result": result.get("content", ""),
                    "tool_call_id": call_id,
                }
            )
    return calls


def _coerce_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        pieces: list[str] = []
        for block in value:
            if isinstance(block, str):
                pieces.append(block)
                continue
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    pieces.append(text)
        return "\n".join(pieces)
    return ""


def extract_metadata(state: Any) -> dict[str, Any]:
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        data = to_jsonable(state)
        if isinstance(data, dict):
            metadata = data.get("metadata")
    return dict(metadata or {})


def extract_output_text(state: Any) -> str:
    """Return only the model's final assistant text.

    Tries, in order:
      1. `state.output.completion` / `state.output.text` (live Inspect TaskState path).
      2. `state.output["choices"][i]["message"]["content"]` (replayed eval-log path).
      3. The trailing assistant message in `state.messages`.

    Never falls back to walking the whole state for strings — that historically
    pulled in prompt text, sample IDs, and metadata, producing false-positive
    matches for downstream regex scorers (e.g. fabrication detection).
    """

    output = getattr(state, "output", None)
    for attr in ("completion", "text"):
        value = getattr(output, attr, None)
        if isinstance(value, str) and value:
            return value

    # Replay path: state.output is a dict from a deserialized eval log.
    if isinstance(output, dict):
        text = _text_from_output_dict(output)
        if text:
            return text

    messages = getattr(state, "messages", None)
    if messages is None and isinstance(state, dict):
        messages = state.get("messages")
    if messages:
        return _text_from_last_assistant(messages)

    return ""


def _text_from_output_dict(output: dict[str, Any]) -> str:
    completion = output.get("completion")
    if isinstance(completion, str) and completion:
        return completion
    pieces: list[str] = []
    for choice in output.get("choices") or []:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message") or {}
        content = message.get("content")
        pieces.append(_collect_text_blocks(content))
    return "\n".join(p for p in pieces if p)


def _text_from_last_assistant(messages: Any) -> str:
    last_assistant = None
    for message in messages:
        role = None
        if isinstance(message, dict):
            role = message.get("role")
        else:
            role = getattr(message, "role", None)
        if role == "assistant":
            last_assistant = message
    if last_assistant is None:
        return ""
    if isinstance(last_assistant, dict):
        content = last_assistant.get("content")
    else:
        content = getattr(last_assistant, "content", None)
    return _collect_text_blocks(content)


def _collect_text_blocks(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        pieces: list[str] = []
        for block in content:
            if isinstance(block, str):
                pieces.append(block)
                continue
            block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
            if block_type and block_type != "text":
                continue
            text = block.get("text") if isinstance(block, dict) else getattr(block, "text", None)
            if isinstance(text, str):
                pieces.append(text)
        return "\n".join(pieces)
    return ""


def _parse_event_string(value: str) -> ToolEvent | None:
    if EVENT_MARKER not in value:
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict):
        return event_from_payload(parsed)
    return None
