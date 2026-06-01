"""Sandbox Agent Bridge adapters for external CLI agents."""

from agent_guardrail_bench.adapters.claude_code import claude_code_agent
from agent_guardrail_bench.adapters.codex_cli import codex_cli_agent

__all__ = ["claude_code_agent", "codex_cli_agent"]
