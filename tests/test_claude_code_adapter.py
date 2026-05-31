"""Unit tests for the Claude Code adapter's MCP config translation.

The full sandbox launch is integration-tested out of band (see
docs/claude-code-mode.md) — this file only covers the pure-Python plumbing
that turns Inspect's `bridge.mcp_server_configs` into the JSON shape Claude
Code's `--mcp-config` expects.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from agent_guardrail_bench.adapters.claude_code import (
    SANDBOX_MCP_CONFIG_PATH,
    _render_mcp_config,
    _server_config_dict,
)


@dataclass
class _StubHttpServer:
    name: str
    url: str
    type: str = "http"
    headers: dict[str, str] | None = None


@dataclass
class _StubStdioServer:
    name: str
    command: str
    args: list[str]
    type: str = "stdio"
    env: dict[str, str] | None = None
    cwd: str | None = None


def test_render_mcp_config_http_server_round_trips():
    cfg = _StubHttpServer(
        name="agent_guardrail_bench",
        url="http://localhost:13131/mcp/agent_guardrail_bench",
        headers={"Authorization": "Bearer secret-token"},
    )
    rendered = json.loads(_render_mcp_config([cfg]))
    assert "mcpServers" in rendered
    assert set(rendered["mcpServers"]) == {"agent_guardrail_bench"}
    entry = rendered["mcpServers"]["agent_guardrail_bench"]
    assert entry["type"] == "http"
    assert entry["url"].startswith("http://localhost:13131")
    assert entry["headers"]["Authorization"] == "Bearer secret-token"


def test_render_mcp_config_stdio_server_round_trips():
    cfg = _StubStdioServer(
        name="agent_guardrail_bench",
        command="/usr/local/bin/inspect-mcp",
        args=["--stdin"],
        env={"INSPECT_BRIDGE": "1"},
        cwd="/home/agent",
    )
    rendered = json.loads(_render_mcp_config([cfg]))
    entry = rendered["mcpServers"]["agent_guardrail_bench"]
    assert entry == {
        "type": "stdio",
        "command": "/usr/local/bin/inspect-mcp",
        "args": ["--stdin"],
        "env": {"INSPECT_BRIDGE": "1"},
        "cwd": "/home/agent",
    }


def test_render_mcp_config_keeps_servers_separated_by_name():
    cfg_a = _StubHttpServer(name="bench_a", url="http://localhost:13131/mcp/a")
    cfg_b = _StubHttpServer(name="bench_b", url="http://localhost:13131/mcp/b")
    rendered = json.loads(_render_mcp_config([cfg_a, cfg_b]))
    assert set(rendered["mcpServers"]) == {"bench_a", "bench_b"}
    assert rendered["mcpServers"]["bench_a"]["url"].endswith("/a")
    assert rendered["mcpServers"]["bench_b"]["url"].endswith("/b")


def test_render_mcp_config_with_no_servers_returns_empty_block():
    rendered = json.loads(_render_mcp_config([]))
    assert rendered == {"mcpServers": {}}


def test_server_config_dict_rejects_unknown_transport():
    @dataclass
    class _Bogus:
        type: str = "carrier_pigeon"

    import pytest

    with pytest.raises(ValueError, match="Unsupported MCP server config"):
        _server_config_dict(_Bogus())


def test_sandbox_mcp_config_path_is_under_agent_home():
    assert SANDBOX_MCP_CONFIG_PATH.startswith("/home/agent/")
