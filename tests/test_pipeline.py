import json
from datetime import UTC, datetime

from qpcr_assay_check.config import load_config
from qpcr_assay_check.pipeline import evaluate, inputs_hash, write_outputs
from qpcr_assay_check.results import RunResult

from .conftest import make_assay

NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC)


def test_inputs_hash_is_stable_and_sensitive(cfg, n1, tmp_path):
    h = inputs_hash(n1, cfg)
    assert h == inputs_hash(make_assay(), cfg)
    assert h != inputs_hash(make_assay(forward="GACCCCAAAATCAGCGAAAC"), cfg)
    p = tmp_path / "c.yaml"
    p.write_text("reaction:\n  mg_mM: 2.5\n")
    assert h != inputs_hash(n1, load_config(p))


def test_evaluate_is_reproducible_for_a_fixed_time(cfg, n1):
    a = evaluate(n1, cfg, qc_only=True, now=NOW)
    b = evaluate(n1, cfg, qc_only=True, now=NOW)
    assert a.model_dump_json() == b.model_dump_json()
    assert a.generated_at == "2026-09-20T12:00:00Z"
    assert a.run_id.startswith("cdc-n1-20260920T120000Z-")
    assert a.network_used is False


def test_write_outputs_creates_the_record_and_json_round_trips(cfg, n1, tmp_path):
    cfg_no_charts = load_config()
    cfg_no_charts.report.include_charts = False
    result = evaluate(n1, cfg_no_charts, qc_only=True, now=NOW)
    run_dir = write_outputs(result, tmp_path, cfg_no_charts)
    assert {p.name for p in run_dir.iterdir()} == {"results.json", "report.html", "results.xlsx"}
    data = json.loads((run_dir / "results.json").read_text())
    assert data["schema_version"] == 1
    assert data["overall"]["verdict"] == "WARN"
    assert RunResult.model_validate(data).inputs_hash == result.inputs_hash


def test_existing_records_are_never_overwritten(n1, tmp_path):
    cfg = load_config()
    cfg.report.include_charts = False
    result = evaluate(n1, cfg, qc_only=True, now=NOW)
    first = write_outputs(result, tmp_path, cfg)
    second = write_outputs(result, tmp_path, cfg)
    assert first != second and second.name == f"{first.name}-2"
    assert (first / "results.json").exists() and (second / "results.json").exists()
