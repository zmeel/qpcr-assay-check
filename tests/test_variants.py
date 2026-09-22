"""Variant-summary lumping (per oligo and per whole fragment), tested on directly constructed
sites and amplicons -- mirrors tests/test_pairing.py's style."""

from qpcr_assay_check.specificity.models import AmpliconResult, SiteResult, SpecificityResult
from qpcr_assay_check.specificity.variants import build_variant_summary
from qpcr_assay_check.verdict import Verdict

from .conftest import make_assay

ASSAY = make_assay()
_n = 0


def mk_site(
    role,
    *,
    s_aln="AAAA",
    q_aln="AAAA",
    midline="||||",
    source="blast_full",
    tier="target",
    acc="X.1",
    org="Org",
    level="critical",
    mm=0,
    gap=0,
):
    global _n
    _n += 1
    return SiteResult(
        id=f"S{_n}", tier=tier, query=role, role=role, oligo=q_aln.replace("-", ""),
        accession=acc, taxid=1, organism=org, title="genomic", orientation="+",
        subject_start=1, subject_end=len(s_aln), source=source, q_aln=q_aln, s_aln=s_aln,
        midline=midline, n_match=len(s_aln) - mm - gap, n_mismatch=mm, n_gap=gap,
        n_ambiguous=0, defect_positions=[], mismatches_last5=0, mismatches_last3=0,
        terminal_defect=False, clean_3prime_nt=10, level=level,
    )  # fmt: skip


def mk_amp(left, right, probe=None, *, tier="target", acc="X.1"):
    return AmpliconResult(
        id=f"A{left.id}{right.id}", tier=tier, accession=acc, taxid=1, organism="Org",
        roles=f"{left.role}/{right.role}", left_site=left.id, right_site=right.id,
        start=1, end=100, length=100, probe_site=probe.id if probe else None,
        classification="likely_detected" if probe else "amplified_not_detected",
        record_type="genomic",
    )  # fmt: skip


def spec(sites=None, amplicons=None):
    return SpecificityResult(
        verdict=Verdict.PASS, verdict_sites=Verdict.PASS, verdict_amplicons=Verdict.PASS,
        rationale=[], findings=[], counts=[], n_sites={}, sites=sites or [],
        amplicons=amplicons or [],
    )  # fmt: skip


def test_identical_sites_lump_into_one_variant_at_100_percent():
    sites = [mk_site("forward"), mk_site("forward"), mk_site("forward")]
    summary = build_variant_summary(spec(sites), ASSAY)
    fwd = next(o for o in summary.oligos if o.role == "forward")
    assert fwd.total_measured == 3
    assert len(fwd.rows) == 1
    assert fwd.rows[0].count == 3
    assert fwd.rows[0].percent == 100.0


def test_a_different_alignment_is_a_separate_row_with_its_own_fraction():
    sites = [
        mk_site("forward", s_aln="AAAA", midline="||||", mm=0),
        mk_site("forward", s_aln="AAAA", midline="||||", mm=0),
        mk_site("forward", s_aln="AAAT", midline="||| ", mm=1),
    ]
    summary = build_variant_summary(spec(sites), ASSAY)
    fwd = next(o for o in summary.oligos if o.role == "forward")
    assert fwd.total_measured == 3
    assert [r.count for r in fwd.rows] == [2, 1]  # sorted, most common first
    assert [r.percent for r in fwd.rows] == [200 / 3, 100 / 3]


def test_worst_case_sites_are_excluded_from_the_table_and_counted_separately():
    sites = [
        mk_site("probe", source="blast_full"),
        mk_site("probe", source="blast_partial_worst_case"),
    ]
    summary = build_variant_summary(spec(sites), ASSAY)
    probe = next(o for o in summary.oligos if o.role == "probe")
    assert probe.total_measured == 1
    assert probe.n_excluded_unmeasured == 1
    assert sum(r.count for r in probe.rows) == 1


def test_non_target_tier_sites_are_ignored():
    sites = [mk_site("forward", tier="background"), mk_site("forward", tier="near_neighbours")]
    summary = build_variant_summary(spec(sites), ASSAY)
    fwd = next(o for o in summary.oligos if o.role == "forward")
    assert fwd.total_measured == 0
    assert fwd.rows == []


def test_a_complete_fragment_is_lumped_across_all_three_oligos():
    f, p, r = mk_site("forward"), mk_site("probe"), mk_site("reverse")
    amp = mk_amp(f, r, p)
    summary = build_variant_summary(spec([f, p, r], [amp]), ASSAY)
    assert summary.fragment_total == 1
    assert len(summary.fragments) == 1
    row = summary.fragments[0]
    assert row.count == 1 and row.percent == 100.0
    assert row.forward.s_aln == f.s_aln and row.reverse.s_aln == r.s_aln


def test_an_amplicon_without_a_probe_site_is_excluded_from_the_fragment_table():
    f, r = mk_site("forward"), mk_site("reverse")
    amp = mk_amp(f, r)  # no probe -> amplified_not_detected, no probe_site
    summary = build_variant_summary(spec([f, r], [amp]), ASSAY)
    assert summary.fragments == []
    assert summary.fragment_excluded_unmeasured == 1


def test_a_fragment_with_one_worst_case_site_is_excluded():
    f = mk_site("forward")
    p = mk_site("probe", source="blast_partial_worst_case")
    r = mk_site("reverse")
    amp = mk_amp(f, r, p)
    summary = build_variant_summary(spec([f, p, r], [amp]), ASSAY)
    assert summary.fragments == []
    assert summary.fragment_excluded_unmeasured == 1


def test_two_amplicons_with_the_same_three_variants_lump_together():
    def triple(mm_probe=0):
        f = mk_site("forward")
        p = mk_site("probe", s_aln="AAAA" if mm_probe == 0 else "AAAT", mm=mm_probe)
        r = mk_site("reverse")
        return f, p, r, mk_amp(f, r, p)

    f1, p1, r1, a1 = triple()
    f2, p2, r2, a2 = triple()
    f3, p3, r3, a3 = triple(mm_probe=1)
    summary = build_variant_summary(spec([f1, p1, r1, f2, p2, r2, f3, p3, r3], [a1, a2, a3]), ASSAY)
    assert summary.fragment_total == 3
    assert [f.count for f in summary.fragments] == [2, 1]


def test_fragment_level_is_the_worst_of_the_three_constituent_sites():
    f = mk_site("forward", level="critical")
    p = mk_site("probe", level="minor")
    r = mk_site("reverse", level="warning")
    amp = mk_amp(f, r, p)
    summary = build_variant_summary(spec([f, p, r], [amp]), ASSAY)
    assert summary.fragments[0].level == "critical"


def test_non_target_tier_amplicons_are_ignored():
    f, p, r = (
        mk_site("forward", tier="background"),
        mk_site("probe", tier="background"),
        mk_site("reverse", tier="background"),
    )
    amp = mk_amp(f, r, p, tier="background")
    summary = build_variant_summary(spec([f, p, r], [amp]), ASSAY)
    assert summary.fragment_total == 0
    assert summary.fragments == []
