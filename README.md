# Agent Guardrail Bench

Agent Guardrail Bench is an Inspect AI-native benchmark for testing whether AI
coding agents respect operational guardrails when they are placed in realistic,
incident-derived failure conditions.

The initial benchmark seeds three public incident patterns:

- PocketOS-style production Railway volume and database deletion.
- Replit/SaaStr-style code freeze violations, production database deletion, and
  fabricated test or data claims.
- Clinejection-style indirect prompt-injection and supply-chain compromise.

This repo is the public eval product layer. The incident corpus remains the
evidence layer in
[paolodm/ai-coding-agents-incidents](https://github.com/paolodm/ai-coding-agents-incidents).
Scenario specs cite corpus rows but are written as deterministic simulations, not
as copies of production systems.

## What This Benchmark Measures

The benchmark scores observable behavior:

- Which tools the agent called.
- Which arguments it supplied.
- Which forbidden actions were attempted.
- Which forbidden actions were actually executed by the fake services.
- Whether the agent completed benign control actions instead of blocking all
  work.
- Whether the final response fabricated safety, test, or data outcomes.

Inspect eval logs are the canonical transcript artifact. Human-readable reports
and dashboards should be derived from those logs, not from a separate harness.

## What This Benchmark Does Not Claim

This benchmark does not certify agent safety. A passing score means an agent,
prompt, policy, sandbox, or guardrail configuration passed these specific
incident-derived regression scenarios under the recorded run conditions. It does
not prove the system is safe against all prompt injections, destructive actions,
supply-chain attacks, or production operations failures.

See [docs/vendor-evaluation-policy.md](docs/vendor-evaluation-policy.md) for the
public evaluation and disclosure policy.

## Runtime Model

The benchmark is built around Inspect AI concepts:

- `Task` definitions in `src/agent_guardrail_bench/tasks/`.
- `Sample` datasets generated from portable scenario YAML specs.
- Inspect tools that expose deterministic fake Railway, Postgres, GitHub, and
  npm services.
- Oracle scorers that inspect tool-call transcripts and final output.
- Eval logs and eval sets for repeatable transcript capture.
- Inspect-native agent mode for ordinary model/tool evals.
- Sandbox Agent Bridge mode for external CLI agents such as Claude Code and
  Codex CLI.

Pytest is used only for ordinary repository tests. It is not the benchmark
harness.

## Quickstart

```sh
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run the seed task in Inspect-native mode:

```sh
inspect eval src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model openai/gpt-4.1-mini \
  -T mode=inspect_native \
  --epochs 3 \
  --log-dir logs/seed
```

Run one scenario:

```sh
inspect eval src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model openai/gpt-4.1-mini \
  -T scenario_id=pocketos_volume_delete \
  -T mode=inspect_native \
  --epochs 5 \
  --log-dir logs/pocketos
```

Open the canonical transcripts:

```sh
inspect view --log-dir logs/seed
```

Run an eval set:

```sh
inspect eval-set src/agent_guardrail_bench/tasks/incident_guardrail.py \
  --model openai/gpt-4.1-mini \
  --log-dir logs/eval-set
```

External CLI agent mode is scaffolded for sandboxed runs:

```sh
inspect eval src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model anthropic/claude-sonnet-4-5 \
  -T mode=claude_code \
  --sandbox docker \
  --log-dir logs/claude-code

inspect eval src/agent_guardrail_bench/tasks/incident_guardrail.py@incident_guardrail \
  --model openai/gpt-5.1 \
  -T mode=codex_cli \
  --sandbox docker \
  --log-dir logs/codex-cli
```

The external adapters currently define the Inspect Sandbox Agent Bridge boundary
and command/env contract. A production sandbox image still needs to install and
configure the target CLI binaries.

## Repository Layout

```text
src/agent_guardrail_bench/
  tasks/       Inspect task entrypoints.
  scenarios/   Portable incident-derived YAML scenario specs and loaders.
  adapters/    Claude Code and Codex CLI Sandbox Agent Bridge adapters.
  tools/       Deterministic fake Railway, Postgres, GitHub, and npm tools.
  scorers/     Oracle scoring over tool events and final output.
  utils/       Shared event and transcript helpers.
docs/          Methodology, scoring, and public evaluation policy.
tests/         Ordinary repo tests for loaders and deterministic scoring helpers.
```

## Development Checks

```sh
python -m compileall src tests
pytest
```

If `inspect-ai` is not installed locally, the lightweight tests still cover the
scenario loader, fake event schema, and scoring core. Full benchmark validation
requires installing the project dependencies and running `inspect eval`.

## Scenario Expansion

Add new incident-derived scenarios by:

1. Adding a YAML file under `src/agent_guardrail_bench/scenarios/`.
2. Citing the upstream corpus row and public incident name.
3. Defining at least one malicious or risky variant and one benign control.
4. Listing forbidden actions separately from expected safe actions.
5. Adding deterministic fake-service behavior if the existing tools do not cover
   the scenario.
6. Running the Inspect task with multiple epochs so randomized variants are
   exercised repeatedly.
