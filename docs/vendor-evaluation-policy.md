# Vendor Evaluation Policy

Agent Guardrail Bench is intended for public, reproducible guardrail regression
testing. It should be used carefully when evaluating named products or vendors.

## Non-Certification

A passing score is not certification. It does not mean an agent, sandbox,
approval layer, or vendor product is safe. It means the evaluated configuration
passed the specified benchmark version, scenario set, model settings, and run
conditions captured in the Inspect eval logs.

## Reproducibility

Public claims should include:

- Benchmark version or commit.
- Scenario IDs and limits.
- Model and agent mode.
- Sandbox configuration.
- Number of epochs or repeated runs.
- Inspect log location or exported log artifacts.
- Any non-default prompts, policies, adapters, or tool approvals.

## Vendor Review

When publishing product-specific findings:

- Give vendors enough technical detail to reproduce the scenario.
- Distinguish blocked attempts from executed harmful actions.
- Distinguish agent behavior from sandbox, approval-policy, or adapter behavior.
- Do not imply broad product safety from narrow scenario success.
- Do not imply broad product failure from one scenario without describing scope.

## Sensitive Details

Do not publish real credentials, real exploit chains against live systems, or
non-public customer data. Scenario specs should use deterministic fake services
and safe reproductions.

## Rankings

Rankings should be treated as experimental unless the run set is large,
versioned, and accompanied by logs. Prefer regression statements such as
"configuration A improved on scenario family B" over universal safety claims.
