# Running the bench inside a real CLI agent

The default `mode=inspect_native` runs the bench by calling a model API
directly from the host. That's the right shape for evaluating the
*model*'s guardrails — but it bypasses everything a coding-agent CLI
adds on top of the model: system prompt, permission policies, the
built-in tool harness, MCP filtering, and any CLI-side guardrail layer.

Two sandbox modes wrap the official CLIs so the bench evaluates the
*product* on top of the model:

- `mode=claude_code` — Anthropic's `claude` CLI.
- `mode=codex_cli` — OpenAI's `codex` CLI.

Both modes share the same sandbox image and Inspect Sandbox Agent
Bridge — the only thing that differs is which CLI binary runs inside
the container and which model API the bridge translates to.

## How the loop works

1. Inspect's `docker` sandbox provider brings up a container per sample
   from `sandbox/Dockerfile`.
2. The bench-side adapter wraps `inspect_swe.claude_code()` /
   `inspect_swe.codex_cli()`, which:
   - Starts a bridge proxy on `localhost:13131` inside the container.
   - Registers the bench's fake-service tools as an MCP server named
     `agent_guardrail_bench` (each tool surfaces as
     `mcp__agent_guardrail_bench__<tool-name>`).
   - Downloads and runs the CLI inside the container via the supported
     installer (side-steps the deprecated npm distribution path).
3. The CLI agent makes its native API calls (Anthropic-shaped for
   Claude Code, OpenAI-shaped for Codex). The bridge proxy receives
   them and routes back to the Inspect model configured by
   `--model ...` on the host.
4. The agent's tool calls hit the bench's fake services via MCP. Every
   call lands as an event in the eval transcript.
5. The guardrail scorer runs unchanged against that transcript.

## What's in this layer

- `sandbox/Dockerfile` — minimal `node:20-bookworm-slim` base. Provides
  Node (both CLIs' runtime), `tini`, and a non-root `agent` user.
  Does **not** install either CLI; that's delegated to `inspect_swe`.
- `compose.yaml` — Inspect docker sandbox provider config pointing at
  `sandbox/`.
- `src/agent_guardrail_bench/adapters/claude_code.py` — wrapper over
  `inspect_swe.claude_code()`. Disallows Claude Code's built-in tools
  (`Bash`, `Read`, `Edit`, `Glob`, `Grep`, `Write`, `WebFetch`, …) so
  the agent only acts through the bridged MCP surface.
- `src/agent_guardrail_bench/adapters/codex_cli.py` — wrapper over
  `inspect_swe.codex_cli()`. Codex has no `disallowed_tools` knob, so
  the wrapper instead defaults `web_search="disabled"` (Codex ships
  the live-web tool on by default).
- `src/agent_guardrail_bench/tasks/incident_guardrail.py` — auto-attaches
  `sandbox=("docker", "compose.yaml")` for both sandbox modes.

## One-time setup

```sh
docker compose build
```

Builds the shared image (~200 MB). `inspect_swe` downloads the
configured CLI version into the container on first sample; subsequent
samples reuse the per-container install.

## Running Claude Code mode

```sh
inspect eval \
  src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model anthropic/claude-sonnet-4-5 \
  -T mode=claude_code \
  -T scenario_id=replit_saastr_db_delete \
  --log-dir logs/claude-code
```

The bridge proxy is model-agnostic; you can also point Claude Code at
a non-Anthropic model:

```sh
inspect eval ... --model openai/gpt-4.1-mini -T mode=claude_code
```

## Running Codex CLI mode

```sh
inspect eval \
  src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model openai/gpt-4.1-mini \
  -T mode=codex_cli \
  -T scenario_id=replit_saastr_db_delete \
  --log-dir logs/codex-cli
```

Codex CLI talks OpenAI-shaped APIs natively, so pairing it with an
OpenAI model is the lowest-friction setup. The bridge can also
translate to non-OpenAI providers if you point `--model` at one.

## Limitations

- **Cold start.** First-sample container startup includes the
  `inspect_swe` CLI download. Subsequent samples on the same build are
  fast.
- **CLI authentication.** `inspect_swe` injects a stub API key and
  routes via the matching `*_BASE_URL=http://localhost:13131` to the
  bridge. Real auth happens host-side in Inspect.
- **No host-side agent state leaks into the sandbox.** Your host
  `~/.claude/` or `~/.codex/` (settings, hooks, MCP servers) do NOT
  flow into the container. The sandboxed CLI reads only the
  container's `/home/agent/.<cli>/`. That's intentional — the sandbox
  is the evaluation surface, not a clone of your host setup.
- **Codex tool-surfacing.** Codex CLI ships built-in `shell`,
  `apply_patch`, `update_plan`, etc. and there is no `disallowed_tools`
  knob to block them (Claude Code does have this knob and we use it).
  Codex's tool catalog also includes a newer `tool_search` tool that
  current standalone OpenAI endpoints reject, so the bench wrapper
  defaults `model_config="gpt-4o"` to pick an older catalog entry.
  Net effect: `mode=codex_cli` reliably starts and produces a scorable
  transcript, but Codex tends to reach for its built-in tools instead
  of the bridged bench tools in the current smoke runs. The scorer
  still fires (fabrication detection observed on the first smoke run),
  but rich bench-tool-call signal will need either Codex CLI exposing
  a way to scope its tool surface, or a bridge filter that strips the
  built-ins before the agent sees them. Tracked for follow-up.

## See also

- [`inspect_swe.claude_code()` reference](https://meridianlabs-ai.github.io/inspect_swe/)
- [`inspect_swe.codex_cli()` reference](https://meridianlabs-ai.github.io/inspect_swe/)
- [Inspect Sandbox Agent Bridge docs](https://inspect.aisi.org.uk/agent-bridge.html#sandbox-bridge)
- `vendor-evaluation-policy.md` — what passing this benchmark does and
  does not claim about your stack.
