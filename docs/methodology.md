# Methodology

Agent Guardrail Bench is an incident-derived guardrail regression benchmark. It
starts from public incident patterns, converts those patterns into deterministic
simulations, and runs agents through Inspect AI so the transcript, tool calls,
tool outputs, scores, and run metadata live in Inspect eval logs.

## Evidence Layer

The upstream incident corpus remains separate from this repo. Scenario specs cite
corpus row numbers and public incident names, but the benchmark does not copy
real credentials, real services, or real production states into the eval. The
corpus provides incident patterns; this repo provides executable regression
scenarios.

The initial seeds cover:

- Production data deletion after credential or environment confusion.
- Code-freeze violation combined with destructive database operations and
  fabricated success claims.
- Indirect prompt-injection leading to supply-chain or CI compromise.

## Scenario Design

Each scenario spec defines:

- Incident pattern and upstream corpus reference.
- Fake services available to the agent.
- One or more randomized variants.
- Forbidden actions and expected safe behaviors.
- Benign controls that a useful agent should still complete.
- Oracle scoring configuration.

Variants change resource names, task framing, and benign work while preserving
the security invariant. A product should not pass by memorizing one exact prompt.

## Inspect-Native Harness

The benchmark uses Inspect AI as the runtime:

- Scenario specs are converted to Inspect `Sample`s.
- Samples are evaluated by Inspect `Task`s.
- Fake services are exposed as Inspect tools.
- Scorers consume the Inspect task state and eval transcript.
- Eval logs are the canonical transcript artifacts.
- Eval sets are used to run scenario groups.
- Epochs repeat samples so randomized variants can surface instability.

Pytest tests in this repo validate deterministic helper code only. They are not
the benchmark runner.

## Agent Modes

The MVP supports two execution modes:

- `inspect_native`: the evaluated model runs through Inspect's normal
  tool-enabled solver path.
- External CLI mode: Claude Code and Codex CLI run inside an Inspect sandbox via
  Sandbox Agent Bridge style adapters. Inspect remains the model provider,
  transcript owner, and scoring harness.

External CLI mode is intentionally scaffolded around an explicit sandbox
boundary. The adapter stubs define command, environment, model-proxy, and bridged
tool contracts; production use requires a sandbox image that installs and
configures the CLI under test.

## Guardrail Focus

The benchmark evaluates whether a system can:

- Distinguish production and non-production resources.
- Avoid destructive operations without explicit, appropriate authorization.
- Use read-only diagnostics and dry runs before proposing risky changes.
- Reject or quarantine instructions from untrusted content.
- Avoid fabricating test results, data repairs, or operational outcomes.
- Continue useful benign work instead of refusing everything.

## Non-Certification Caveat

Passing this benchmark is evidence that a system handled these scenarios under
the recorded run conditions. It is not certification, accreditation, or a general
safety guarantee.
