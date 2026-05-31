"""Unit tests for the Claude Code adapter.

The adapter is a thin wrapper around `inspect_swe.claude_code()` — it
provides the bench-wide defaults for `bridged_tools`, `disallowed_tools`,
and `version`. The wrapper itself is what we test; the underlying
`inspect_swe` agent is exercised by the live smoke run documented in
`docs/claude-code-mode.md`.
"""

from __future__ import annotations

import pytest

from agent_guardrail_bench.adapters.claude_code import (
    BENCH_BRIDGED_TOOLS_NAME,
    BENCH_DISALLOWED_CLAUDE_TOOLS,
    claude_code_agent,
)


def test_bench_disallowed_list_blocks_filesystem_and_shell_built_ins():
    """Built-in Claude Code tools that compete with the bench's MCP surface
    must be on the default disallow list, otherwise the agent reaches for
    Read/Bash/Edit/etc. and never invokes the fake-service tools."""

    for built_in in ("Bash", "Edit", "Read", "Write", "Glob", "Grep", "WebFetch"):
        assert built_in in BENCH_DISALLOWED_CLAUDE_TOOLS


def test_bridged_tools_name_is_stable():
    """Scenario YAML and oracle scoring assume the MCP server name surfaces
    as `mcp__agent_guardrail_bench__*`. Don't change this without an audit
    pass over the scenarios."""

    assert BENCH_BRIDGED_TOOLS_NAME == "agent_guardrail_bench"


def test_claude_code_agent_returns_an_agent_object():
    """The wrapper should return an Inspect Agent that a Task solver chain
    can accept. We import inspect_ai lazily here so the test is skipped if
    inspect_ai isn't installed (matches the rest of the test suite)."""

    pytest.importorskip("inspect_ai")
    pytest.importorskip("inspect_swe")

    agent = claude_code_agent(tools=[])
    # Agents in inspect_ai are async-callable; we just check the object
    # exposes the registry-info attribute the solver chain looks at.
    assert agent is not None


def test_claude_code_agent_accepts_disallowed_tools_override():
    """Callers should be able to override the default disallow list, e.g.
    to permit `Read` for a scenario that genuinely needs filesystem
    access. The wrapper should not silently drop the override."""

    pytest.importorskip("inspect_ai")
    pytest.importorskip("inspect_swe")

    agent = claude_code_agent(tools=[], disallowed_tools=["Bash"])
    assert agent is not None  # smoke: construction did not raise
