# Running the bench in `mode=claude_code`

The default `mode=inspect_native` runs the bench by calling a model API
directly from the host. That's the right shape for evaluating the
*model*'s guardrails — but it bypasses everything Claude Code adds on
top of the model: system prompt, permission policies, the built-in tool
harness, MCP filtering, and any Claude-Code-side guardrail layer.

`mode=claude_code` puts the official `claude` CLI in the agent loop
inside a Docker sandbox. Inspect's Sandbox Agent Bridge runs an
Anthropic-compatible proxy on `localhost:13131` inside the container,
exposes the bench's fake tools as an MCP server, and routes the agent's
Anthropic API calls back to whatever Inspect model the operator picked.

## What's in this mode

- `sandbox/Dockerfile` — minimal `node:20` base. Provides Node (Claude
  Code's runtime), `tini`, and a non-root `agent` user. **Does not**
  install Claude Code itself; the adapter delegates installation to
  `inspect_swe`, which uses the supported installer at sample time. That
  side-steps the deprecated npm distribution path.
- `compose.yaml` — Inspect's `docker` sandbox provider config pointing
  at `sandbox/`.
- `src/agent_guardrail_bench/adapters/claude_code.py` — thin wrapper
  over [`inspect_swe.claude_code()`](https://meridianlabs-ai.github.io/inspect_swe/).
  Supplies the bench's `BridgedToolsSpec`, disallows Claude Code's
  built-in tools (`Bash`, `Read`, `Edit`, `Glob`, `Grep`, `Write`,
  `WebFetch`, …) so the agent only acts through the bench's fake-service
  MCP tools, and pins `version="auto"`.
- `src/agent_guardrail_bench/tasks/incident_guardrail.py` —
  automatically attaches `sandbox=("docker", "compose.yaml")` when
  `mode=claude_code`.

## One-time setup

```sh
docker compose build
```

Builds a small (~200 MB) image. `inspect_swe` will download the
configured Claude Code version into the container on first sample —
subsequent samples reuse the per-container install.

## Running

```sh
inspect eval \
  src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model anthropic/claude-sonnet-4-5 \
  -T mode=claude_code \
  -T scenario_id=replit_saastr_db_delete \
  --log-dir logs/claude-code
```

Inspect's `docker` provider reads `compose.yaml`, brings the container
up per sample, runs `claude` inside it via `inspect_swe`, and tears the
container down after. The agent's tool-call transcript lands in the
`.eval` log; the scorer runs unchanged.

You can also point the bridge at a different model — e.g.
`--model openai/gpt-4.1-mini`. The proxy translates Anthropic-shaped
requests from Claude Code into the target model's API on the way back.

## Limitations

- **Cold start.** First-sample container startup includes the
  `inspect_swe` Claude Code download. Subsequent samples on the same
  build are fast.
- **CLI authentication.** `inspect_swe` injects a stub
  `ANTHROPIC_API_KEY` and routes via `ANTHROPIC_BASE_URL=http://localhost:13131`
  to the bridge proxy. Real auth happens host-side in Inspect.
- **No host-side agent state leaks into the sandbox.** Your host
  `~/.claude/` (settings, hooks, MCP servers) does NOT flow into the
  container. The sandboxed Claude Code reads only the container's
  `/home/agent/.claude`. That's intentional — the sandbox is the
  evaluation surface, not a clone of your host setup.

## See also

- [`inspect_swe.claude_code()` reference](https://meridianlabs-ai.github.io/inspect_swe/)
- [Inspect Sandbox Agent Bridge docs](https://inspect.aisi.org.uk/agent-bridge.html#sandbox-bridge)
- `vendor-evaluation-policy.md` — what passing this benchmark does and
  does not claim about your stack.
