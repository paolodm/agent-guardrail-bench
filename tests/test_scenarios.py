import re

import pytest

from agent_guardrail_bench.scenarios import build_sample_records, load_scenarios
from agent_guardrail_bench.tools.common import is_production_target

UNRENDERED_TEMPLATE = re.compile(r"\{[A-Za-z_][^}]*\}")


def test_seed_scenarios_load():
    scenarios = load_scenarios()
    ids = {scenario["id"] for scenario in scenarios}

    assert ids == {
        "pocketos_volume_delete",
        "replit_saastr_db_delete",
        "clinejection_supply_chain",
    }


def test_sample_records_render_randomized_resources():
    records = build_sample_records("pocketos_volume_delete", variant_repetitions=2, seed=7)

    assert len(records) == 2
    assert records[0]["id"] != records[1]["id"]
    assert "{resource_suffix}" not in records[0]["input"]
    assert records[0]["metadata"]["oracle"]["forbidden_actions"][0]["target"].startswith(
        "prod-primary-volume-"
    )


@pytest.mark.parametrize(
    "scenario_id",
    [
        "pocketos_volume_delete",
        "replit_saastr_db_delete",
        "clinejection_supply_chain",
    ],
)
def test_sample_records_render_all_oracle_targets(scenario_id):
    records = build_sample_records(scenario_id, variant_repetitions=2, seed=11)

    for record in records:
        assert not _contains_unrendered_template(record["input"])
        metadata = record["metadata"]
        assert not _contains_unrendered_template(metadata["environment"])
        oracle = metadata["oracle"]
        assert not _contains_unrendered_template(oracle["forbidden_actions"])
        assert not _contains_unrendered_template(oracle["fabrication_patterns"])


def test_production_targets_are_explicit_scenario_state():
    env = {"production_targets": ["prod-primary-volume-1234"]}

    assert is_production_target("prod-primary-volume-1234", env)
    assert not is_production_target("staging-primary-replica", env)
    assert not is_production_target("dev-product-cache", env)


def _contains_unrendered_template(value):
    if isinstance(value, str):
        return bool(UNRENDERED_TEMPLATE.search(value))
    if isinstance(value, dict):
        return any(
            _contains_unrendered_template(key) or _contains_unrendered_template(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_unrendered_template(item) for item in value)
    return False
