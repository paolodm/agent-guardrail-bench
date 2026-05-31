# syntax=docker/dockerfile:1.7

# Sandbox image for running Claude Code (and optionally Codex CLI) under
# Inspect's Sandbox Agent Bridge. Builds on top of node:20 because both CLIs
# are distributed as npm packages.

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

# Pin the Claude Code CLI version so re-builds are reproducible across
# benchmark sweeps. Bump the ARG to upgrade.
ARG CLAUDE_CODE_VERSION=2.1.131
RUN npm install -g --no-fund --no-audit \
        "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"

# Optional: install Codex CLI for `mode=codex_cli`. Comment out if you only
# need Claude Code support; keeping it here means a single image works for
# both adapters.
ARG CODEX_CLI_VERSION=
RUN if [ -n "${CODEX_CLI_VERSION}" ]; then \
        npm install -g --no-fund --no-audit "@openai/codex@${CODEX_CLI_VERSION}"; \
    fi

# Run as an unprivileged user so the bench cannot accidentally mutate the
# image. UID 1000 matches the Inspect Docker provider's default expectations.
RUN useradd --create-home --uid 1000 --shell /bin/bash agent
USER agent
ENV HOME=/home/agent \
    PATH=/home/agent/.local/bin:/usr/local/bin:/usr/bin:/bin

WORKDIR /home/agent

# The bench writes runtime artifacts (MCP config, prompt files) here. Keeping
# them under $HOME means they're owned by the agent user and don't need root
# to overwrite between iterations.
RUN mkdir -p /home/agent/.bench

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["sleep", "infinity"]
