"""Inspect tool factories for fake services."""

from agent_guardrail_bench.tools.fake_github import fake_github_tools
from agent_guardrail_bench.tools.fake_npm import fake_npm_tools
from agent_guardrail_bench.tools.fake_postgres import fake_postgres_tools
from agent_guardrail_bench.tools.fake_railway import fake_railway_tools


def all_fake_tools():
    return [
        *fake_railway_tools(),
        *fake_postgres_tools(),
        *fake_github_tools(),
        *fake_npm_tools(),
    ]


__all__ = ["all_fake_tools"]
