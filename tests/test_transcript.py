"""Regression tests for transcript extraction.

These tests guard against a class of bugs where the `_seen` cycle-detection
set in `to_jsonable` incorrectly suppresses sibling objects because CPython
reuses the `id()` of a short-lived intermediate (e.g. a dict produced by
`pydantic.BaseModel.model_dump()`) once it goes out of scope.
"""

from __future__ import annotations

import json

from agent_guardrail_bench.utils.events import ToolEvent
from agent_guardrail_bench.utils.transcript import extract_tool_events, to_jsonable


def _event_payload_string(action: str, target: str) -> str:
    return json.dumps(
        {
            "agent_guardrail_bench_event": True,
            "event": {
                "service": "fake_railway",
                "action": action,
                "target": target,
                "attempted": True,
                "executed": True,
                "blocked_by": None,
                "details": {},
                "ts": 0.0,
            },
        }
    )


def test_extract_tool_events_collects_sibling_pydantic_messages():
    """Two tool messages with the same shape must both be extracted."""
    try:
        from inspect_ai.model import ChatMessageTool, ChatMessageUser
        from inspect_ai.solver import TaskState
    except ImportError:
        import pytest

        pytest.skip("inspect_ai is not installed")

    messages = [
        ChatMessageUser(content="diagnose the migration"),
        ChatMessageTool(content=_event_payload_string("railway.list_services", "production")),
        ChatMessageTool(content=_event_payload_string("railway.list_services", "staging")),
        ChatMessageTool(content=_event_payload_string("postgres.query", "prod-db-1234")),
    ]
    state = TaskState(
        model="test/model",
        sample_id="sample",
        epoch=1,
        input="diagnose the migration",
        messages=messages,
        completed=True,
    )

    events = extract_tool_events(state)

    assert len(events) == 3
    actions = [(e.action, e.target) for e in events]
    assert ("railway.list_services", "production") in actions
    assert ("railway.list_services", "staging") in actions
    assert ("postgres.query", "prod-db-1234") in actions


def test_to_jsonable_does_not_repr_sibling_dicts():
    """Sibling dicts with reused memory addresses must not be repr-collapsed."""

    siblings = [
        {"agent_guardrail_bench_event": True, "event": {"action": "a", "target": "t1"}},
        {"agent_guardrail_bench_event": True, "event": {"action": "a", "target": "t2"}},
        {"agent_guardrail_bench_event": True, "event": {"action": "a", "target": "t3"}},
    ]

    result = to_jsonable(siblings)

    assert isinstance(result, list)
    assert len(result) == 3
    for item in result:
        assert isinstance(item, dict), f"sibling was collapsed to repr: {item!r}"
        assert item.get("agent_guardrail_bench_event") is True


def test_extract_tool_events_from_event_payload_dicts():
    """Sibling event payload dicts must each be extracted."""

    payloads = [ToolEvent(service="s", action="a", target=f"t{i}", executed=True).payload()
                for i in range(5)]

    events = extract_tool_events(payloads)

    assert len(events) == 5
    assert {e.target for e in events} == {"t0", "t1", "t2", "t3", "t4"}
