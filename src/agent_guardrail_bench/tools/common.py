"""Common helpers for deterministic fake Inspect tools."""

from __future__ import annotations

import re
from typing import Any

from agent_guardrail_bench.utils.events import ToolEvent, emit_event

DESTRUCTIVE_SQL = re.compile(r"\b(drop|delete|truncate|alter|update|insert)\b", re.I)


def service_event(
    *,
    service: str,
    action: str,
    target: str,
    executed: bool,
    blocked_by: str | None = None,
    **details: Any,
) -> str:
    return emit_event(
        ToolEvent(
            service=service,
            action=action,
            target=target,
            attempted=True,
            executed=executed,
            blocked_by=blocked_by,
            details={key: value for key, value in details.items() if value is not None},
        )
    )


def looks_production(value: str) -> bool:
    return any(marker in value.lower() for marker in ("prod", "production", "primary"))
