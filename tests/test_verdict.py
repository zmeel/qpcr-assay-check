from qpcr_assay_check.config import load_config
from qpcr_assay_check.models import Status
from qpcr_assay_check.verdict import EXIT_CODES, Verdict, combine, exit_code, verdict_from_status


def test_precedence_fail_over_incomplete_over_warn_over_pass():
    req = ["a", "b"]
    assert combine({"a": Verdict.PASS, "b": Verdict.PASS}, req) is Verdict.PASS
    assert combine({"a": Verdict.PASS, "b": Verdict.WARN}, req) is Verdict.WARN
    assert combine({"a": Verdict.WARN, "b": None}, req) is Verdict.INCOMPLETE
    assert combine({"a": Verdict.FAIL, "b": None}, req) is Verdict.FAIL
    assert combine({"a": Verdict.INCOMPLETE, "b": Verdict.PASS}, req) is Verdict.INCOMPLETE


def test_missing_evidence_is_never_a_pass():
    assert combine({}, ["specificity"]) is Verdict.INCOMPLETE
    assert combine({"oligo_qc": Verdict.PASS}, ["oligo_qc", "specificity"]) is Verdict.INCOMPLETE


def test_only_required_sections_count():
    assert combine({"a": Verdict.PASS, "b": Verdict.FAIL}, ["a"]) is Verdict.PASS


def test_exit_codes_are_distinct_and_stable():
    assert [
        exit_code(v) for v in (Verdict.PASS, Verdict.WARN, Verdict.FAIL, Verdict.INCOMPLETE)
    ] == [0, 10, 20, 30]
    assert len(set(EXIT_CODES.values())) == 4


def test_info_maps_to_pass():
    assert verdict_from_status(Status.INFO) is Verdict.PASS


def test_pipeline_full_run_is_incomplete_even_when_qc_passes(tmp_path, n1):
    from qpcr_assay_check.pipeline import evaluate

    p = tmp_path / "c.yaml"
    p.write_text("thresholds:\n  pair:\n    primer_tm_diff_c: {warn_above: 5, fail_above: 8}\n")
    cfg = load_config(p)
    qc_only = evaluate(n1, cfg, qc_only=True)
    full = evaluate(n1, cfg)
    assert qc_only.overall.verdict is Verdict.PASS and qc_only.overall.exit_code == 0
    assert full.overall.verdict is Verdict.INCOMPLETE and full.overall.exit_code == 30
    assert any("Not evaluated" in line for line in full.overall.rationale)


def test_fail_is_not_masked_by_incomplete(cfg):
    from qpcr_assay_check.pipeline import evaluate

    from .conftest import make_assay

    full = evaluate(make_assay(forward="GGGGGGCCCCCCGGGGGGCC"), cfg)
    assert full.overall.verdict is Verdict.FAIL
