from agent_guardrail_bench.scenarios import build_sample_records, load_scenarios


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
