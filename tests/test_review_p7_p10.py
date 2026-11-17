"""Whole-project review of 2026-11-17: P7 (core_nt), P8 (window end), P9 (RNA reverse primer),
P10 (2 + 2 primer pairs)."""

from __future__ import annotations

from qpcr_assay_check.config import load_config
from qpcr_assay_check.inclusivity.models import FragmentWindow
from qpcr_assay_check.oligo import grade as g
from qpcr_assay_check.specificity.assess import LIMITATIONS
from qpcr_assay_check.specificity.models import SiteResult
from qpcr_assay_check.variants.exhaustive import _pair_lines, exhaustive_inclusivity
from qpcr_assay_check.variants.models import YearCoverage

from .conftest import make_assay

FWD = "GACCCCAAAATCAGCGAAAT"
REV = "TCTGGTTACTGCCAGTTGAATCTG"
PRB = "ACCCCGCATTACGTTTGGTGGACC"


def _site(role, q, s, acc):
    grade = g.grade_fields(q, s, role, mgb=False)
    return SiteResult(
        id=f"S{abs(hash((role, acc))) % 10**6}", tier="target", query=role, role=role, oligo=q,
        accession=acc, taxid=1, organism="o", title="t", orientation="+", subject_start=1,
        subject_end=len(q), source="blast_full", q_aln=q, s_aln=s, midline="",
        n_match=len(q), n_mismatch=sum(a != b for a, b in zip(q, s, strict=True)), n_gap=0,
        n_ambiguous=0, defect_positions=[], mismatches_last5=0, mismatches_last3=0,
        terminal_defect=False, clean_3prime_nt=5, level="critical", **grade,
    )  # fmt: skip


def _swap(seq, *from_3):
    s = list(seq)
    for k in from_3:
        s[-k] = "A" if s[-k] != "A" else "C"
    return "".join(s)


def _window(n, det):
    return FragmentWindow(first=2023, last=2026, years=[], with_region=n, undetermined=0,
                          detectable=det, at_risk=n - det, likely_failure=0)  # fmt: skip


def test_the_report_says_what_core_nt_leaves_out():
    text = " ".join(LIMITATIONS)
    assert "whole-genome-shotgun (WGS) draft assemblies" in text and "core_nt" in text


def test_the_status_window_ends_at_the_run_year_without_records_in_it():
    cfg = load_config()
    years = [YearCoverage(year=y, listed=5, assessed=5) for y in (2022, 2023, 2024)]
    inc = exhaustive_inclusivity([], [], years, make_assay(), cfg, current_year=2026)
    assert [y.year for y in inc.fragment_years][-1] == 2026
    assert exhaustive_inclusivity([], [], years, make_assay(), cfg).fragment_years[-1].year == 2024


def test_a_two_plus_two_primer_pair_is_flagged_not_reclassified():
    sites = [
        _site("forward", FWD, _swap(FWD, 8, 12), "A.1"),
        _site("reverse", REV, _swap(REV, 9, 14), "A.1"),
        _site("probe", PRB, PRB, "A.1"),
    ]
    assert {s.grade for s in sites if s.role != "probe"} == {"at_risk"}
    lines = _pair_lines(sites, {"A.1": 2025}, _window(1, 0), set(), set(), rna=False,
                        unit="records")  # fmt: skip
    assert len(lines) == 1 and "2 mismatches in each primer" in lines[0]
    assert "about 15 dCq" in lines[0]


def test_an_rna_assay_names_failures_through_the_reverse_primer_alone():
    sites = [
        _site("forward", FWD, FWD, "B.1"),
        _site("reverse", REV, REV[:-1] + "C", "B.1"),  # terminal G1 mismatch: likely failure
        _site("probe", PRB, PRB, "B.1"),
    ]
    assert sites[1].grade not in g.DETECTABLE
    w = _window(10, 9)
    rna = _pair_lines(sites, {"B.1": 2025}, w, set(), set(), rna=True, unit="records")
    assert any("reverse primer alone" in x and "100.0% would be detectable instead of 90.0%" in x
               for x in rna)  # fmt: skip
    assert _pair_lines(sites, {"B.1": 2025}, w, set(), set(), rna=False, unit="records") == []
