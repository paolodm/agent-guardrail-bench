"""Loose transcript extraction helpers for Inspect task states and logs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import json
from typing import Any, Iterable

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
            str(k): to_jsonable(v, _seen=_seen, _depth=_depth + 1) for k, v in value.items()
        }
    if isinstance(value, list | tuple | set):
        return [to_jsonable(item, _seen=_seen, _depth=_depth + 1) for item in value]
    if hasattr(value, "__dict__"):
        return to_jsonable(vars(value), _seen=_seen, _depth=_depth + 1)
    return repr(value)


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


def extract_metadata(state: Any) -> dict[str, Any]:
    metadata = getattr(state, "metadata", None)
    if metadata is None:
        data = to_jsonable(state)
        if isinstance(data, dict):
            metadata = data.get("metadata")
    return dict(metadata or {})


def extract_output_text(state: Any) -> str:
    output = getattr(state, "output", None)
    for attr in ("completion", "text"):
        value = getattr(output, attr, None)
        if isinstance(value, str):
            return value
    data = to_jsonable(output if output is not None else state)
    strings = list(iter_strings(data))
    return "\n".join(strings[-5:])


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
