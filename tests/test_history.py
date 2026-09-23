"""Unit tests for history/diff.py (natural-key matching) and history/store.py (finding runs)."""

from __future__ import annotations

from qpcr_assay_check.history.diff import compute_history
from qpcr_assay_check.history.store import find_previous_run
from qpcr_assay_check.inclusivity.models import (
    InclusivityOligoResult,
    InclusivityResult,
    WindowStats,
)
from qpcr_assay_check.models import Status
from qpcr_assay_check.results import OverallResult, QCReport, RunResult, SectionResult
from qpcr_assay_check.specificity.models import AmpliconResult, SiteResult, SpecificityResult
from qpcr_assay_check.verdict import Verdict

from .conftest import make_assay

ACC = "OT000001.1"


def _site(
    id_, *, tier="background", role="forward", accession=ACC, start=100, end=119,
    level="critical", n_mismatch=2, n_gap=0,
):  # fmt: skip
    n = end - start + 1
    return SiteResult(
        id=id_, tier=tier, query=role, role=role, oligo="A" * n, accession=accession, taxid=100,
        organism="Bacterium exemplum", orientation="+", subject_start=start, subject_end=end,
        source="blast_full", q_aln="A" * n, s_aln="A" * n, midline="|" * n, n_match=n - n_mismatch,
        n_mismatch=n_mismatch, n_gap=n_gap, n_ambiguous=0, defect_positions=[1],
        mismatches_last5=0, mismatches_last3=0, terminal_defect=False, clean_3prime_nt=5,
        level=level,
    )  # fmt: skip


def _amplicon(
    id_, *, tier="background", accession=ACC, start=100, end=200, roles="forward/reverse",
    classification="likely_detected",
):  # fmt: skip
    return AmpliconResult(
        id=id_, tier=tier, accession=accession, taxid=100, organism="Bacterium exemplum",
        roles=roles, left_site="S1", right_site="S2", start=start, end=end, length=end - start + 1,
        classification=classification, record_type="genomic",
    )  # fmt: skip


def _spec(sites=None, amplicons=None, verdict=Verdict.PASS) -> SpecificityResult:
    return SpecificityResult(
        verdict=verdict, verdict_sites=verdict, verdict_amplicons=verdict, rationale=[],
        findings=[], counts=[], n_sites={}, sites=sites or [], amplicons=amplicons or [],
    )  # fmt: skip


def _window(
    year, *, sample_size, n_perfect, n_one=0, n_two=0, n_three=0, per_position=None, pop=None
):
    return WindowStats(
        year=year, population_size=pop, sample_size=sample_size, n_perfect=n_perfect,
        n_one_mismatch=n_one, n_two_plus_mismatch=n_two, n_three_prime_mismatch=n_three,
        per_position_mismatches=per_position or [0] * 20,
    )  # fmt: skip


def _incl(role_windows: dict[str, list[WindowStats]]) -> InclusivityResult:
    oligos = [
        InclusivityOligoResult(role=role, oligo="A" * 20, windows=windows)
        for role, windows in role_windows.items()
    ]
    return InclusivityResult(
        tier_searched=True, target_taxid=1, oligos=oligos, verdict=Verdict.PASS
    )


def _minimal_run(
    *, run_id="r1", generated_at="2025-01-01T00:00:00Z", inputs_hash="h1", sections=None,
    specificity=None, inclusivity=None, overall_verdict=Verdict.PASS,
) -> RunResult:  # fmt: skip
    return RunResult(
        tool={"name": "qpcr-assay-check", "version": "0.0.0"},
        run_id=run_id,
        generated_at=generated_at,
        inputs_hash=inputs_hash,
        mode="full",
        network_used=True,
        environment={},
        assay=make_assay(),
        config={},
        oligo_qc=QCReport(oligos=[], checks=[], structures=[], status=Status.PASS),
        specificity=specificity,
        inclusivity=inclusivity,
        sections=sections or [],
        overall=OverallResult(
            verdict=overall_verdict, exit_code=0, rationale=[], required_sections=[]
        ),
    )


def test_no_previous_run_is_incomplete_not_a_silent_pass():
    h = compute_history(
        None, inputs_hash="h", section_verdicts={}, section_titles={}, sites=[], amplicons=[],
        inclusivity=None,
    )  # fmt: skip
    assert h.has_previous is False
    assert h.verdict is Verdict.INCOMPLETE
    assert "First run" in h.rationale[0]


def test_identical_evidence_gives_pass_and_no_diff_entries():
    site = _site("Sold")
    spec_section = SectionResult(
        key="specificity", title="Specificity", state="evaluated", verdict=Verdict.FAIL
    )
    previous = _minimal_run(
        sections=[spec_section], specificity=_spec(sites=[site], verdict=Verdict.FAIL)
    )
    h = compute_history(
        previous, inputs_hash="h1",
        section_verdicts={"specificity": Verdict.FAIL},
        section_titles={"specificity": "Specificity"},
        sites=[_site("Snew")],  # same natural key, same level/mismatches, different run-local id
        amplicons=[], inclusivity=None,
    )  # fmt: skip
    assert h.verdict is Verdict.PASS
    assert h.new_sites == h.resolved_sites == h.changed_sites == []
    assert h.inputs_changed is False
    assert "No meaningful change" in h.rationale[0]


def test_a_new_critical_site_warns_and_is_reported():
    spec_section = SectionResult(
        key="specificity", title="Specificity", state="evaluated", verdict=Verdict.PASS
    )
    previous = _minimal_run(sections=[spec_section], specificity=_spec(sites=[]))
    h = compute_history(
        previous, inputs_hash="h1",
        section_verdicts={"specificity": Verdict.FAIL},
        section_titles={"specificity": "Specificity"},
        sites=[_site("S1", level="critical")], amplicons=[], inclusivity=None,
    )  # fmt: skip
    assert h.verdict is Verdict.WARN
    assert len(h.new_sites) == 1 and h.new_sites[0].kind == "new"
    assert h.new_sites[0].level_after == "critical"
    (sc,) = [c for c in h.section_changes if c.changed]
    assert sc.key == "specificity"
    assert sc.verdict_before is Verdict.PASS
    assert sc.verdict_after is Verdict.FAIL


def test_a_site_that_disappeared_is_resolved_not_new():
    previous = _minimal_run(specificity=_spec(sites=[_site("Sold", level="critical")]))
    h = compute_history(
        previous, inputs_hash="h1", section_verdicts={}, section_titles={}, sites=[], amplicons=[],
        inclusivity=None,
    )  # fmt: skip
    assert h.new_sites == []
    assert len(h.resolved_sites) == 1 and h.resolved_sites[0].kind == "resolved"
    assert h.resolved_sites[0].level_before == "critical"


def test_a_site_at_the_same_position_with_a_different_mismatch_count_is_changed():
    previous = _minimal_run(specificity=_spec(sites=[_site("Sold", level="warning", n_mismatch=4)]))
    h = compute_history(
        previous, inputs_hash="h1", section_verdicts={}, section_titles={},
        sites=[_site("Snew", level="critical", n_mismatch=2)], amplicons=[], inclusivity=None,
    )  # fmt: skip
    assert h.new_sites == [] and h.resolved_sites == []
    (c,) = h.changed_sites
    assert (c.level_before, c.level_after) == ("warning", "critical")
    assert (c.n_mismatch_before, c.n_mismatch_after) == (4, 2)


def test_a_new_amplicon_warns():
    previous = _minimal_run(specificity=_spec(amplicons=[]))
    h = compute_history(
        previous, inputs_hash="h1", section_verdicts={}, section_titles={}, sites=[],
        amplicons=[_amplicon("A1")], inclusivity=None,
    )  # fmt: skip
    assert h.verdict is Verdict.WARN
    assert len(h.new_amplicons) == 1 and h.new_amplicons[0].kind == "new"


def test_inputs_changed_is_reported_independently_of_evidence_changes():
    previous = _minimal_run(inputs_hash="old-hash")
    h = compute_history(
        previous, inputs_hash="new-hash", section_verdicts={}, section_titles={}, sites=[],
        amplicons=[], inclusivity=None,
    )  # fmt: skip
    assert h.inputs_changed is True
    assert any("configuration changed" in line for line in h.rationale)


def test_inclusivity_regression_is_flagged_with_the_new_mismatch_position():
    prev_incl = _incl({"forward": [_window(2023, sample_size=10, n_perfect=10)]})
    curr_incl = _incl(
        {"forward": [_window(2023, sample_size=10, n_perfect=5, per_position=[1] + [0] * 19)]}
    )
    previous = _minimal_run(inclusivity=prev_incl)
    h = compute_history(
        previous, inputs_hash="h1", section_verdicts={}, section_titles={}, sites=[],
        amplicons=[], inclusivity=curr_incl,
    )  # fmt: skip
    assert h.verdict is Verdict.WARN
    (c,) = h.inclusivity_changes
    assert (c.percent_before, c.percent_after) == (100.0, 50.0)
    assert c.new_mismatch_positions == [1]


def test_inclusivity_improvement_alone_does_not_warn():
    prev_incl = _incl({"forward": [_window(2023, sample_size=10, n_perfect=5)]})
    curr_incl = _incl({"forward": [_window(2023, sample_size=10, n_perfect=10)]})
    previous = _minimal_run(inclusivity=prev_incl)
    h = compute_history(
        previous, inputs_hash="h1", section_verdicts={}, section_titles={}, sites=[],
        amplicons=[], inclusivity=curr_incl,
    )  # fmt: skip
    assert h.verdict is Verdict.PASS
    (c,) = h.inclusivity_changes
    assert (c.percent_before, c.percent_after) == (50.0, 100.0)


def test_more_records_at_the_same_rounded_rate_stays_out_of_the_summary():
    prev_incl = _incl({"forward": [_window(2026, sample_size=300, n_perfect=297)]})
    curr_incl = _incl({"forward": [_window(2026, sample_size=600, n_perfect=595)]})
    previous = _minimal_run(inclusivity=prev_incl)
    h = compute_history(
        previous, inputs_hash="h1", section_verdicts={}, section_titles={}, sites=[],
        amplicons=[], inclusivity=curr_incl,
    )  # fmt: skip
    (c,) = h.inclusivity_changes  # still in the table, with both sample sizes
    assert (c.sample_size_before, c.sample_size_after) == (300, 600)
    assert not any(line.startswith("Inclusivity, forward") for line in h.rationale)


def test_find_previous_run_picks_the_most_recently_generated_one(tmp_path):
    old = _minimal_run(run_id="a-old", generated_at="2024-01-01T00:00:00Z")
    new = _minimal_run(run_id="a-new", generated_at="2025-06-01T00:00:00Z")
    slug = old.assay.slug
    for r in (old, new):
        d = tmp_path / slug / r.run_id
        d.mkdir(parents=True)
        (d / "results.json").write_text(r.model_dump_json(), encoding="utf-8")
    found = find_previous_run(tmp_path, slug)
    assert found is not None and found.run_id == "a-new"


def test_find_previous_run_skips_a_corrupt_record(tmp_path):
    good = _minimal_run(run_id="good", generated_at="2025-01-01T00:00:00Z")
    slug = good.assay.slug
    good_dir = tmp_path / slug / good.run_id
    good_dir.mkdir(parents=True)
    (good_dir / "results.json").write_text(good.model_dump_json(), encoding="utf-8")
    broken_dir = tmp_path / slug / "broken"
    broken_dir.mkdir(parents=True)
    (broken_dir / "results.json").write_text("{not valid json", encoding="utf-8")
    found = find_previous_run(tmp_path, slug)
    assert found is not None and found.run_id == "good"


def test_find_previous_run_returns_none_for_a_first_run(tmp_path):
    assert find_previous_run(tmp_path, "never-run-before") is None
