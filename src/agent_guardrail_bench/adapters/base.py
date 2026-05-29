"""Shared helpers for sandboxed external CLI adapters."""

from __future__ import annotations

import inspect
import json
from typing import Any, Sequence

from agent_guardrail_bench.utils.transcript import to_jsonable


def render_command(command: Sequence[str], prompt: str) -> list[str]:
    return [part.replace("{prompt}", prompt) for part in command]


def bridge_env(
    *,
    bridge: Any,
    provider: str,
    mcp_server_configs: Any,
) -> dict[str, str]:
    env = {
        "AGB_MCP_CONFIG_JSON": json.dumps(to_jsonable(mcp_server_configs), sort_keys=True),
    }
    if provider == "anthropic":
        env.update(
            {
                "ANTHROPIC_BASE_URL": f"http://localhost:{bridge.port}",
                "ANTHROPIC_MODEL": "inspect",
            }
        )
    else:
        env.update(
            {
                "OPENAI_BASE_URL": f"http://localhost:{bridge.port}/v1",
                "OPENAI_MODEL": "inspect",
            }
        )
    return env


async def maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value
