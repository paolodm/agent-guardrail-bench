"""Claude Code adapter scaffold for Inspect Sandbox Agent Bridge runs."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from agent_guardrail_bench.adapters.base import bridge_env, maybe_await, render_command

DEFAULT_CLAUDE_CODE_COMMAND = ("claude", "-p", "{prompt}")


def claude_code_agent(
    *,
    tools: Sequence[Any] | None = None,
    command: Sequence[str] = DEFAULT_CLAUDE_CODE_COMMAND,
):
    """Return an Inspect Agent that invokes Claude Code inside the sandbox.

    The sandbox image is expected to install `claude` and configure it to use the
    Anthropic-compatible proxy exposed by `sandbox_agent_bridge`.
    """

    from inspect_ai.agent import Agent, AgentState, BridgedToolsSpec, agent, sandbox_agent_bridge
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
                prompt = user_prompt(state.messages)
                result = await maybe_await(
                    sandbox().exec(
                        cmd=render_command(command, prompt.text),
                        env=bridge_env(
                            bridge=bridge,
                            provider="anthropic",
                            mcp_server_configs=bridge.mcp_server_configs,
                        ),
                    )
                )
                if not result.success:
                    raise RuntimeError(f"Claude Code failed: {result.stderr}")
                return bridge.state

        return execute

    return _claude_code_agent()
