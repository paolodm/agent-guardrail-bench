"""Common helpers for deterministic fake Inspect tools."""

from __future__ import annotations

import re
from typing import Any

from agent_guardrail_bench.utils.events import ToolEvent, emit_event

DESTRUCTIVE_SQL = re.compile(r"\b(drop|delete|truncate|alter|update|insert)\b", re.I)
READ_ONLY_SQL = re.compile(r"\bselect\b", re.I)
SCENARIO_ENVIRONMENT_KEY = "agent_guardrail_bench.environment"


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


def scenario_environment() -> dict[str, Any]:
    """Read the current Inspect sample's scenario environment."""

    try:
        from inspect_ai.util import store
    except ImportError:
        return {}

    try:
        env = store().get(SCENARIO_ENVIRONMENT_KEY, {})
    except Exception:
        return {}
    return dict(env or {})


def is_production_target(value: str, env: dict[str, Any] | None = None) -> bool:
    environment = scenario_environment() if env is None else env
    return value in set(environment.get("production_targets") or [])


def has_valid_approval(approval_id: str | None, env: dict[str, Any] | None = None) -> bool:
    if not approval_id:
        return False
    environment = scenario_environment() if env is None else env
    valid_ids = set(str(item) for item in environment.get("valid_approval_ids") or [])
    return str(approval_id) in valid_ids


def env_flag(name: str, default: bool = False, env: dict[str, Any] | None = None) -> bool:
    environment = scenario_environment() if env is None else env
    return bool(environment.get(name, default))
