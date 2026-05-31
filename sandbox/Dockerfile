# syntax=docker/dockerfile:1.7

# Sandbox image for running Claude Code (and optionally Codex CLI) under
# Inspect's Sandbox Agent Bridge. Builds on top of node:20 because both CLIs
# are distributed as npm packages.
#
# Extension points for guardrail products like Ciphero are documented at the
# bottom of this file. They are intentionally NOT baked in by default — each
# operator wires their own guardrail stack.

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

# -----------------------------------------------------------------------------
# Extension point: Ciphero (or any other PreToolUse guardrail)
# -----------------------------------------------------------------------------
# Ciphero is the operator's defensive layer; we keep it out of this image so
# upstream can pin specific versions. Two ways to wire it in:
#
# 1) Volume-mount at runtime (recommended for local iteration). Edit
#    ../compose.yaml and uncomment the `volumes:` section that bind-mounts
#    your host ~/.ciphero and the matching settings.json fragment into the
#    container's /home/agent. See ../docs/claude-code-mode.md.
#
# 2) Bake into the image (recommended for CI / shared sweeps). Add a layer
#    here that COPYs your Ciphero install into /home/agent/.ciphero and
#    writes the PreToolUse hook entry into /home/agent/.claude/settings.json.
#    Example:
#
#        COPY --chown=agent:agent ciphero/ /home/agent/.ciphero/
#        COPY --chown=agent:agent ciphero/settings.fragment.json /tmp/cf.json
#        RUN mkdir -p /home/agent/.claude && \
#            jq -s '.[0] * .[1]' /tmp/cf.json /home/agent/.claude/settings.json \
#               > /home/agent/.claude/settings.json.new && \
#            mv /home/agent/.claude/settings.json.new /home/agent/.claude/settings.json
#
# Either way, once Ciphero is in place inside the container its PreToolUse
# hook will intercept every tool call that the sandboxed Claude Code agent
# makes against the bench's fake tools — which is the integration this bench
# is designed to surface.
