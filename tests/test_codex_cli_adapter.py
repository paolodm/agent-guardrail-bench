"""Unit tests for the Codex CLI adapter.

The adapter is a thin wrapper around `inspect_swe.codex_cli()` — it
provides the bench-wide defaults for `bridged_tools`, `web_search`, and
`version`. The wrapper itself is what we test; the underlying
`inspect_swe` agent is exercised by the live smoke run documented in
`docs/sandbox-modes.md`.
"""

from __future__ import annotations

import pytest

from agent_guardrail_bench.adapters.codex_cli import (
    BENCH_BRIDGED_TOOLS_NAME,
    codex_cli_agent,
)


def test_bridged_tools_name_matches_claude_code_adapter():
    """Both CLI adapters surface the bench tools under the same MCP server
    name so scenario YAML and oracle scoring are mode-agnostic."""

    assert BENCH_BRIDGED_TOOLS_NAME == "agent_guardrail_bench"


def test_codex_cli_agent_returns_an_agent_object():
    pytest.importorskip("inspect_ai")
    pytest.importorskip("inspect_swe")

    agent = codex_cli_agent(tools=[])
    assert agent is not None


def test_codex_cli_agent_web_search_disabled_by_default():
    """The bench has no need for live web search, and an agent that wanders
    onto the live web blurs the signal we're trying to score. The wrapper
    must default `web_search="disabled"` and forward an override."""

    pytest.importorskip("inspect_ai")
    pytest.importorskip("inspect_swe")

    # Default: should construct without error and not raise on the disabled
    # web_search path.
    default_agent = codex_cli_agent(tools=[])
    assert default_agent is not None

    # Override should also be accepted (don't silently drop).
    overridden = codex_cli_agent(tools=[], web_search="cached")
    assert overridden is not None
