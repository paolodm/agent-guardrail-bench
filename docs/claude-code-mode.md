# Running the bench in `mode=claude_code` (and `mode=codex_cli`)

The default `mode=inspect_native` runs the bench by calling a model API
directly from the host. That's the right shape for evaluating the
*model*'s guardrails — but it bypasses anything an external coding-agent
CLI (Claude Code or Codex CLI) does on top of the model: system prompt,
permission policies, tool harness, MCP filtering, and so on.

`mode=claude_code` puts the official `claude` CLI in the agent loop
inside a Docker sandbox. Inspect's Sandbox Agent Bridge runs an
Anthropic-compatible proxy on `localhost:13131` inside the container and
exposes the bench's fake tools as an MCP server. The sandboxed Claude
Code agent makes Anthropic API calls (routed through the proxy back to
your chosen Inspect model) and tool calls (handled by the bench's fake
services). `mode=codex_cli` follows the same pattern with the `codex`
CLI and an OpenAI-compatible proxy.

## What's in this mode

- `sandbox/Dockerfile` — minimal `node:20` image that installs
  `@anthropic-ai/claude-code`. Pinned via the `CLAUDE_CODE_VERSION`
  build arg. Codex CLI install is included but opt-in via the
  `CODEX_CLI_VERSION` build arg.
- `compose.yaml` — Inspect docker sandbox provider config pointing at
  `sandbox/`.
- `src/agent_guardrail_bench/adapters/claude_code.py` — wires the
  bridge proxy, writes the bench's MCP servers to
  `/home/agent/.bench/mcp.json` inside the container, and invokes
  `claude --print --strict-mcp-config --mcp-config ... --model inspect`.
- `src/agent_guardrail_bench/tasks/incident_guardrail.py` —
  declares `sandbox=("docker", "compose.yaml")` automatically when
  `mode in {"claude_code", "codex_cli"}`.

## One-time setup

Build the sandbox image (takes ~1–2 minutes on first build, then
cached):

```sh
docker compose build
```

That installs Node 20, the `claude` CLI, and a non-root `agent` user.
No bench code is copied in — the bridge supplies tools at runtime.

If you also want `mode=codex_cli`:

```sh
docker compose build --build-arg CODEX_CLI_VERSION=<version>
```

## Running

```sh
inspect eval \
  src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model anthropic/claude-sonnet-4-5 \
  -T mode=claude_code \
  -T scenario_id=replit_saastr_db_delete \
  --log-dir logs/claude-code
```

Inspect's `docker` sandbox provider reads `compose.yaml`, brings the
container up per sample, runs `claude -p ...` inside it, and tears it
down after. The agent's tool-call transcript still lands in the
`.eval` log; the scorer runs unchanged.

For `mode=codex_cli`, swap the `-T` flag and the model arg accordingly.

## Limitations

- **Cold start cost.** The first build of `sandbox/Dockerfile` is
  slow because of the `npm install -g`. Subsequent runs use the
  cached image and start in seconds. Inspect uses a fresh container
  per sample by default; if you want to amortize startup further,
  set up Docker Compose pooling via Inspect's sandbox configuration.
- **CLI authentication.** The adapter sets
  `ANTHROPIC_API_KEY=inspect-bridge-stub` and routes via
  `ANTHROPIC_BASE_URL=http://localhost:13131` to the bridge. Real
  auth happens host-side in Inspect, not inside the sandbox. The
  Codex adapter does the analogous thing with `OPENAI_API_KEY` and
  `OPENAI_BASE_URL`.
- **No host-side agent state leaks into the sandbox.** Anything in
  your host `~/.claude/` (settings, hooks, MCP servers) does NOT
  flow into the container. The sandboxed Claude Code reads only the
  container's `/home/agent/.claude`, which is empty unless you bake
  it into the image. That's intentional — the sandbox is the
  evaluation surface, not a clone of your host setup.
- **End-to-end live testing of this mode is currently scaffolded but
  not validated.** The unit-tested pieces (MCP config rendering,
  task wiring) are covered. The full Docker + bridge + CLI loop
  needs an operator with Docker Desktop running to drive a first
  smoke test; please file issues against any rough edges.

## See also

- `src/agent_guardrail_bench/adapters/codex_cli.py` — the Codex CLI
  counterpart. Shares the same `compose.yaml` and sandbox image.
- `vendor-evaluation-policy.md` — what passing this benchmark does
  and does not claim about your stack.
