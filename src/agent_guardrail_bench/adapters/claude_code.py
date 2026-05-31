"""Claude Code adapter for Inspect Sandbox Agent Bridge runs.

Runs the official `claude` CLI inside a Docker sandbox, points it at the
Inspect bridge proxy for model calls, and exposes the bench's fake tools via
an MCP config file rendered into the container at runtime. Any PreToolUse
hook installed inside the sandbox (e.g. Ciphero) sees every tool call the
agent makes — that is the integration this adapter is designed to enable.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from agent_guardrail_bench.adapters.base import bridge_env, maybe_await

# Path inside the sandbox where the bench writes the MCP server config.
SANDBOX_MCP_CONFIG_PATH = "/home/agent/.bench/mcp.json"

# `--strict-mcp-config` makes the sandboxed Claude Code ignore any MCP
# servers configured in /home/agent/.claude/*. We always want the agent to
# only see the bench's bridged tools, never whatever a curious operator
# left in their image.
DEFAULT_CLAUDE_CODE_COMMAND: tuple[str, ...] = (
    "claude",
    "--print",
    "--output-format",
    "json",
    "--model",
    "inspect",
    "--mcp-config",
    SANDBOX_MCP_CONFIG_PATH,
    "--strict-mcp-config",
    "--permission-mode",
    "bypassPermissions",
)


def claude_code_agent(
    *,
    tools: Sequence[Any] | None = None,
    command: Sequence[str] = DEFAULT_CLAUDE_CODE_COMMAND,
    mcp_config_path: str = SANDBOX_MCP_CONFIG_PATH,
):
    """Return an Inspect Agent that invokes Claude Code inside the sandbox.

    The sandbox image (see `sandbox/Dockerfile`) must install the `claude`
    CLI and run as a user that can read/write `mcp_config_path`. The image
    is also the appropriate place to install any PreToolUse hook (Ciphero
    or equivalent) — see `docs/claude-code-mode.md`.
    """

    from inspect_ai.agent import (
        Agent,
        AgentState,
        BridgedToolsSpec,
        agent,
        sandbox_agent_bridge,
    )
    from inspect_ai.model import user_prompt
    from inspect_ai.util import sandbox

    @agent
    def _claude_code_agent() -> Agent:
        async def execute(state: AgentState) -> AgentState:
            bridged_tools = [
                BridgedToolsSpec(name="agent_guardrail_bench", tools=list(tools or []))
            ]
            async with sandbox_agent_bridge(
                state,
                model="inspect",
                bridged_tools=bridged_tools,
            ) as bridge:
                config_blob = _render_mcp_config(bridge.mcp_server_configs)
                await maybe_await(
                    sandbox().write_file(mcp_config_path, config_blob)
                )

                prompt = user_prompt(state.messages)
                env = bridge_env(
                    bridge=bridge,
                    provider="anthropic",
                    mcp_server_configs=bridge.mcp_server_configs,
                )
                # Claude Code refuses to run without an API key in the env
                # even when ANTHROPIC_BASE_URL points at a stub proxy.
                env.setdefault("ANTHROPIC_API_KEY", "inspect-bridge-stub")

                result = await maybe_await(
                    sandbox().exec(
                        cmd=list(command),
                        input=prompt.text,
                        env=env,
                    )
                )
                if not result.success:
                    raise RuntimeError(
                        "Claude Code adapter failed.\n"
                        f"exit={result.returncode}\nstderr={result.stderr}"
                    )
                return bridge.state

        return execute

    return _claude_code_agent()


def _render_mcp_config(server_configs: Any) -> str:
    """Translate Inspect's MCPServerConfig objects into Claude Code's format.

    Claude Code's `--mcp-config` expects a JSON file shaped like
    `{"mcpServers": {<name>: {<server config>}}}`. Inspect's bridge returns
    MCPServerConfigHTTP (or MCPServerConfigStdio) Pydantic models; we
    serialize each into the matching Claude Code entry.
    """

    servers: dict[str, dict[str, Any]] = {}
    for config in server_configs or []:
        name = getattr(config, "name", None) or "agent_guardrail_bench"
        servers[name] = _server_config_dict(config)
    return json.dumps({"mcpServers": servers}, sort_keys=True)


def _server_config_dict(config: Any) -> dict[str, Any]:
    transport = getattr(config, "type", None)
    if transport in ("http", "sse"):
        entry: dict[str, Any] = {
            "type": transport,
            "url": getattr(config, "url"),
        }
        headers = getattr(config, "headers", None)
        if headers:
            entry["headers"] = dict(headers)
        return entry
    if transport == "stdio":
        entry = {
            "type": "stdio",
            "command": getattr(config, "command"),
            "args": list(getattr(config, "args", []) or []),
        }
        env = getattr(config, "env", None)
        if env:
            entry["env"] = dict(env)
        cwd = getattr(config, "cwd", None)
        if cwd:
            entry["cwd"] = str(cwd)
        return entry
    # Fallback: assume the object is already a plain dict or has model_dump.
    if hasattr(config, "model_dump"):
        return dict(config.model_dump())
    if isinstance(config, dict):
        return dict(config)
    raise ValueError(f"Unsupported MCP server config: {config!r}")
