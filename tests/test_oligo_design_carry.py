"""Oligo design carried over from an earlier record (user, 2026-11-26: "After the first run
oligo design is known and therefore not to be repeated in each run")."""

from __future__ import annotations

from datetime import UTC, datetime

from qpcr_assay_check.config import load_config
from qpcr_assay_check.pipeline import evaluate, find_oligo_design, oligo_design_hash, write_outputs
from qpcr_assay_check.report.html import render_report

from .conftest import make_assay
from .test_run_full import env  # noqa: F401 - the fixture, used by name

NOW = datetime(2026, 11, 26, 8, 0, 0, tzinfo=UTC)


def test_the_fingerprint_follows_what_oligo_design_depends_on():
    assay, cfg = make_assay(), load_config()
    base = oligo_design_hash(assay, cfg.model_dump(mode="json"))
    other = make_assay(forward="GACCCCAAAATCAGCGAAAA")
    assert oligo_design_hash(other, cfg.model_dump(mode="json")) != base
    warm = load_config(None, {"reaction": {"annealing_temp_C": 62.0}})
    assert oligo_design_hash(assay, warm.model_dump(mode="json")) != base
    tight = load_config(None, {"thresholds": {"structures": {"warn_tm_c": 40.0}}})
    assert oligo_design_hash(assay, tight.model_dump(mode="json")) != base
    # the searches do not change the oligo design
    blast = load_config(None, {"specificity": {"max_amplicons": 1000}})
    assert oligo_design_hash(assay, blast.model_dump(mode="json")) == base


def test_the_newest_matching_record_is_found_and_named(tmp_path):
    assay, cfg = make_assay(), load_config()
    assert find_oligo_design(assay, cfg, tmp_path) is None
    first = evaluate(assay, cfg, qc_only=True, now=NOW)
    write_outputs(first, tmp_path, cfg)
    qc, source = find_oligo_design(assay, cfg, tmp_path)
    assert source.run_id == first.run_id and qc == first.oligo_qc
    # a record that carried it over names the record it came from, not itself
    later = evaluate(assay, cfg, qc_only=True, now=NOW.replace(hour=9), oligo_design=(qc, source))
    write_outputs(later, tmp_path, cfg)
    assert find_oligo_design(assay, cfg, tmp_path)[1].run_id == first.run_id
    # other oligos: nothing to carry over
    assert find_oligo_design(make_assay(forward="GACCCCAAAATCAGCGAAAA"), cfg, tmp_path) is None


def test_a_carried_record_keeps_the_status_and_says_where_it_came_from(tmp_path):
    assay, cfg = make_assay(), load_config()
    first = evaluate(assay, cfg, qc_only=True, now=NOW)
    write_outputs(first, tmp_path, cfg)
    carried = evaluate(assay, cfg, qc_only=True, now=NOW.replace(hour=9),
                       oligo_design=find_oligo_design(assay, cfg, tmp_path))  # fmt: skip
    assert carried.oligo_qc == first.oligo_qc and carried.overall.verdict == first.overall.verdict
    assert carried.oligo_design_from.run_id == first.run_id
    section = next(s for s in carried.sections if s.key == "oligo_qc")
    assert f"Carried over from record {first.run_id}" in section.note
    html = render_report(carried, cfg)
    assert "Carried over, not evaluated again." in html and first.run_id in html
    assert 'class="qcm"' not in html  # the QC tables stay in the first record
    assert "carried over from the record of 2026-11-26" in html  # Part A row


def test_the_cli_carries_it_over_and_refuses_it_for_a_qc_only_run(env):  # noqa: F811
    import json

    from .test_run_full import invoke, world_with

    env.install(world_with())
    r = invoke(env, "--qc-only", "--skip-oligo-design")
    assert r.exit_code == 64 and "leaves nothing to evaluate" in r.output
    first = invoke(env, "--yes")
    assert "Record written" in first.output and "carried over" not in first.output
    second = invoke(env, "--yes", "--skip-oligo-design")
    assert "Oligo design carried over from record" in second.output
    records = sorted(env.out.rglob("results.json"))
    old, new = (json.loads(p.read_text()) for p in records)
    assert old["oligo_design_from"] is None
    assert new["oligo_design_from"]["run_id"] == old["run_id"]
    assert new["oligo_qc"] == old["oligo_qc"]


def test_the_gui_passes_the_choice_to_the_command(tmp_path):
    from qpcr_assay_check.gui.runs import Job, JobStore, cli_command, new_job_id

    store = JobStore(tmp_path)

    def job(**kw: object) -> Job:
        return store.create(Job(id=new_job_id("a.yaml"), assay="a.yaml", assay_name="A",
                                skip_oligo_design=True, **kw), "assay_name: A\n")  # fmt: skip

    assert "--skip-oligo-design" in cli_command(job(), store, None)
    qc = job(qc_only=True)  # a QC-only run is the oligo design itself
    assert "--skip-oligo-design" not in cli_command(qc, store, None)
