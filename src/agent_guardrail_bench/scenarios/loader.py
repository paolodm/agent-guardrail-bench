"""Load and materialize portable incident-derived scenario specs."""

from __future__ import annotations

import random
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

SCENARIO_DIR = Path(__file__).resolve().parent


def scenario_paths() -> list[Path]:
    return sorted(SCENARIO_DIR.glob("*.yaml"))


def load_scenario(path_or_id: str | Path) -> dict[str, Any]:
    path = Path(path_or_id)
    if not path.exists():
        path = SCENARIO_DIR / f"{path_or_id}.yaml"
    with open(path, encoding="utf-8") as handle:
        spec = yaml.safe_load(handle)
    if not isinstance(spec, dict) or "id" not in spec:
        raise ValueError(f"Invalid scenario spec: {path}")
    return spec


def load_scenarios(scenario_id: str | None = None) -> list[dict[str, Any]]:
    if scenario_id:
        return [load_scenario(scenario_id)]
    return [load_scenario(path) for path in scenario_paths()]


def build_sample_records(
    scenario_id: str | None = None,
    *,
    variant_repetitions: int = 1,
    seed: int = 0,
) -> list[dict[str, Any]]:
    """Materialize scenario variants into Inspect-ready sample records."""

    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    for scenario in load_scenarios(scenario_id):
        for variant in scenario.get("variants", []):
            for repetition in range(variant_repetitions):
                suffix = f"{rng.randrange(1000, 9999)}"
                variables = dict(variant.get("variables") or {})
                variables.setdefault("resource_suffix", suffix)
                variables["resource_suffix"] = str(variables["resource_suffix"])
                variables = _render(variables, {"resource_suffix": variables["resource_suffix"]})
                rendered_variant = _render(deepcopy(variant), variables)
                sample_id = f"{scenario['id']}:{variant['id']}:{repetition}"
                oracle = {
                    "forbidden_actions": rendered_variant.get("forbidden_actions", []),
                    "forbidden_builtin_actions": rendered_variant.get(
                        "forbidden_builtin_actions", []
                    ),
                    "benign_controls": rendered_variant.get("benign_controls", []),
                    "expected_safe_behaviors": rendered_variant.get("expected_safe_behaviors", []),
                    "fabrication_patterns": rendered_variant.get("fabrication_patterns", []),
                    "minimum_benign_controls": rendered_variant.get("minimum_benign_controls", 1),
                }
                environment = rendered_variant.get("environment", {})
                records.append(
                    {
                        "id": sample_id,
                        "input": rendered_variant["prompt"],
                        "target": rendered_variant.get("target", "Complete the task safely."),
                        "metadata": {
                            "scenario_id": scenario["id"],
                            "scenario_title": scenario["title"],
                            "variant_id": rendered_variant["id"],
                            "repetition": repetition,
                            "resource_suffix": suffix,
                            "incident": scenario.get("incident", {}),
                            "services": scenario.get("services", []),
                            "tools": scenario.get("tools", []),
                            "environment": environment,
                            "oracle": oracle,
                        },
                    }
                )
    return records


def _render(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        return value.format(**variables)
    if isinstance(value, list):
        return [_render(item, variables) for item in value]
    if isinstance(value, dict):
        return {_render(key, variables): _render(item, variables) for key, item in value.items()}
    return value


def main() -> None:
    for scenario in load_scenarios():
        print(f"{scenario['id']}\t{scenario['title']}")


if __name__ == "__main__":
    main()
