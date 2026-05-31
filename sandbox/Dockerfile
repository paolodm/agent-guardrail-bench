# syntax=docker/dockerfile:1.7

# Sandbox image for running Claude Code under Inspect's Sandbox Agent Bridge.
#
# The bench delegates Claude Code installation to `inspect_swe.claude_code()`
# (see `src/agent_guardrail_bench/adapters/claude_code.py`). The adapter is
# configured with `version="auto"` so the agent downloads the current stable
# Claude Code via the official installer at sample time — that side-steps
# the deprecated npm distribution path Anthropic flagged.
#
# This image therefore only needs to provide a base environment with `node`
# (Claude Code's runtime), the small set of system tools the installer
# expects, and a non-root user the agent runs as.

FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        python3 \
        python3-pip \
        tini \
    && rm -rf /var/lib/apt/lists/*

# The node base image already ships a `node` user on uid 1000. Repurpose
# that slot for an `agent` user so the Inspect Docker provider's default
# expectations and the adapter's /home/agent/* paths stay consistent.
RUN userdel -r node \
    && useradd --create-home --uid 1000 --shell /bin/bash agent
USER agent
ENV HOME=/home/agent \
    PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin

WORKDIR /home/agent

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]
