"""Claude Code adapter for Inspect Sandbox Agent Bridge runs.

Thin wrapper over `inspect_swe.claude_code()` — the maintained Inspect SWE
agent. It handles the bridge proxy, MCP server registration for bridged
tools, and Claude Code installation inside the sandbox so the bench only
has to declare which fake-service tools should be visible to the agent.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

# Built-in Claude Code tools the bench disallows so the agent can only act
# through the fake-service MCP tools the bridge exposes. Without this list
# the agent reaches for `Read`/`Bash`/`Edit`/etc. first and never invokes
# the bench surface, which masks both forbidden-action and benign-control
# signal.
BENCH_DISALLOWED_CLAUDE_TOOLS: tuple[str, ...] = (
    "Bash",
    "BashOutput",
    "Edit",
    "ExitPlanMode",
    "Glob",
    "Grep",
    "KillBash",
    "MultiEdit",
    "NotebookEdit",
    "Read",
    "Task",
    "TodoWrite",
    "WebFetch",
    "WebSearch",
    "Write",
)

# Bridged-tools MCP server name. Surfaces to the agent as
# `mcp__agent_guardrail_bench__<tool-name>`.
BENCH_BRIDGED_TOOLS_NAME = "agent_guardrail_bench"


def claude_code_agent(
    *,
    tools: Sequence[Any] | None = None,
    disallowed_tools: Sequence[str] | None = None,
    allow_builtins: bool = False,
    version: str = "auto",
    **kwargs: Any,
):
    """Return an Inspect Agent that runs Claude Code inside the sandbox.

    Args:
        tools: Bench-supplied fake-service tools to expose via MCP.
        disallowed_tools: Built-in Claude Code tools to block. Defaults to
            the full bench-visible disallow list so the agent only has the
            bridged fake-service tools available. Ignored when
            ``allow_builtins=True``.
        allow_builtins: When ``True``, pass ``disallowed_tools=[]`` so
            the agent sees the full Claude Code built-in tool surface
            (``Bash``, ``Edit``, ``Write``, etc.) in addition to the
            bridged bench tools. Pair with scenario YAMLs that declare
            ``forbidden_builtin_actions`` for the scorer to catch
            built-in routes around the bench guards.
        version: Claude Code version to use inside the sandbox. `"auto"`
            uses whatever the image ships (if any) and otherwise downloads
            the current stable via the official installer — that side-steps
            the deprecated npm install path.
        **kwargs: Forwarded to `inspect_swe.claude_code()` (e.g.
            `system_prompt`, `attempts`, `model`, `env`).
    """

    from inspect_ai.agent import BridgedToolsSpec
    from inspect_swe import claude_code

    bridged_tools = [
        BridgedToolsSpec(name=BENCH_BRIDGED_TOOLS_NAME, tools=list(tools or []))
    ]
    if allow_builtins:
        disallowed: list[str] = []
    else:
        disallowed = list(
            BENCH_DISALLOWED_CLAUDE_TOOLS if disallowed_tools is None else disallowed_tools
        )
    return claude_code(
        bridged_tools=bridged_tools,
        disallowed_tools=disallowed,
        version=version,
        **kwargs,
    )
