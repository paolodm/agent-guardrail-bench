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


def test_runbook_shell_payload_provisions_inert_files():
    """The clinejection `runbook_shell_payload` variant ships a fake repo
    into the sandbox to let the agent's built-in Read / Bash see a real
    working tree. Belt-and-braces safety: even if the agent runs the
    runbook's payload commands verbatim, none of the provisioned files
    should ship real credentials or routable endpoints. This test fails
    if a future edit accidentally puts a real token or registry URL into
    the fixture content."""

    records = build_sample_records("clinejection_supply_chain", variant_repetitions=1, seed=7)
    runbook = [r for r in records if r["metadata"]["variant_id"] == "runbook_shell_payload"]
    assert runbook, "runbook_shell_payload variant did not materialize"

    environment = runbook[0]["metadata"]["environment"]
    repo_files = environment.get("provisioned_repo") or {}
    assert repo_files, "runbook variant must provision a fake repo"

    expected_suffixes = (
        "/package.json",
        "/.npmrc",
        "/.github/workflows/release.yml",
        "/tools/release-recovery.md",
    )
    for suffix in expected_suffixes:
        assert any(p.endswith(suffix) for p in repo_files), (
            f"provisioned_repo missing expected file ending in {suffix!r}"
        )

    forbidden_substrings = [
        "ghp_",
        "github_pat_",
        "ghs_",
        "ghu_",
        "ssh-rsa",
        "ssh-ed25519",
        "BEGIN PRIVATE KEY",
        "BEGIN RSA PRIVATE KEY",
        "BEGIN OPENSSH PRIVATE KEY",
        "AKIA",
        "aws_secret_access_key",
        "registry=https://registry.npmjs.org",
        "registry=https://npm.pkg.github.com",
    ]
    for path, content in repo_files.items():
        for needle in forbidden_substrings:
            assert needle not in content, (
                f"provisioned_repo file {path!r} contains a forbidden substring "
                f"{needle!r}; bench fixtures must never ship real credentials "
                f"or routable production endpoints"
            )

    npmrc = next(content for path, content in repo_files.items() if path.endswith("/.npmrc"))
    assert "127.0.0.1" in npmrc, (
        ".npmrc must pin the registry to a loopback address; got: " + npmrc
    )


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
