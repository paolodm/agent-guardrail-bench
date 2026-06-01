"""Codex CLI adapter for Inspect Sandbox Agent Bridge runs.

Thin wrapper over `inspect_swe.codex_cli()` — the maintained Inspect SWE
agent for OpenAI's Codex CLI. It handles the bridge proxy, MCP server
registration for bridged tools, and Codex CLI installation inside the
sandbox so the bench only has to declare which fake-service tools should
be visible to the agent.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# Bridged-tools MCP server name. Surfaces to the agent as
# `mcp__agent_guardrail_bench__<tool-name>`.
BENCH_BRIDGED_TOOLS_NAME = "agent_guardrail_bench"


def codex_cli_agent(
    *,
    tools: Sequence[Any] | None = None,
    web_search: str = "disabled",
    version: str = "auto",
    model_config: str | None = "gpt-4o",
    **kwargs: Any,
):
    """Return an Inspect Agent that runs Codex CLI inside the sandbox.

    Codex's tool model differs from Claude Code's: there is no
    ``disallowed_tools`` knob, but Codex does ship a ``web_search`` tool
    on by default. The bench doesn't need the live web, so we disable it
    here to keep the agent's surface scoped to the bridged fake-service
    MCP tools the scorer is watching for.

    Newer Codex catalog entries (gpt-5*) emit a ``tool_search`` tool that
    is not yet accepted by OpenAI's standard model endpoints, so the
    wrapper pins ``model_config="gpt-4o"`` by default. That picks an
    older Codex catalog entry whose tool set is universally accepted.
    Pass ``model_config=None`` to let Codex auto-derive from the runtime
    model when you know it supports the newer tools.

    Args:
        tools: Bench-supplied fake-service tools to expose via MCP.
        web_search: One of ``"live"``, ``"cached"``, ``"disabled"``.
            Defaults to ``"disabled"`` for the bench.
        version: Codex CLI version to use inside the sandbox. ``"auto"``
            uses whatever the image ships (if any) and otherwise downloads
            the latest stable via the supported installer.
        model_config: Codex model slug used to pick the system prompt and
            tool catalog. Defaults to ``"gpt-4o"`` to avoid newer tools
            like ``tool_search`` that current OpenAI endpoints reject.
        **kwargs: Forwarded to ``inspect_swe.codex_cli()`` (e.g.
            ``system_prompt``, ``attempts``, ``model``, ``env``,
            ``config_overrides``).
    """

    from inspect_ai.agent import BridgedToolsSpec
    from inspect_swe import codex_cli

    bridged_tools = [
        BridgedToolsSpec(name=BENCH_BRIDGED_TOOLS_NAME, tools=list(tools or []))
    ]
    return codex_cli(
        bridged_tools=bridged_tools,
        web_search=web_search,
        version=version,
        model_config=model_config,
        **kwargs,
    )
