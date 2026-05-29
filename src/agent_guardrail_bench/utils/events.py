"""Shared event schema emitted by deterministic fake services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
import time
from typing import Any

EVENT_MARKER = "agent_guardrail_bench_event"
EVENT_LOG_ENV = "AGB_EVENT_LOG_PATH"


@dataclass(frozen=True)
class ToolEvent:
    """Observable fake-service action for transcript and oracle scoring."""

    service: str
    action: str
    target: str
    attempted: bool = True
    executed: bool = False
    blocked_by: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def payload(self) -> dict[str, Any]:
        return {EVENT_MARKER: True, "event": asdict(self)}


def emit_event(event: ToolEvent) -> str:
    """Return an event payload and optionally append it to a JSONL event file."""

    payload = event.payload()
    path = os.environ.get(EVENT_LOG_ENV)
    if path:
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return json.dumps(payload, sort_keys=True)


def event_from_payload(payload: dict[str, Any]) -> ToolEvent | None:
    if not payload.get(EVENT_MARKER):
        return None
    event = payload.get("event")
    if not isinstance(event, dict):
        return None
    return ToolEvent(
        service=str(event.get("service", "")),
        action=str(event.get("action", "")),
        target=str(event.get("target", "")),
        attempted=bool(event.get("attempted", False)),
        executed=bool(event.get("executed", False)),
        blocked_by=event.get("blocked_by"),
        details=dict(event.get("details") or {}),
        ts=float(event.get("ts", 0.0)),
    )
