"""The exclusivity report: grouping already-assessed sites/amplicons by organism-list entry."""

from __future__ import annotations

from qpcr_assay_check.config import load_config
from qpcr_assay_check.specificity.models import AmpliconResult, SiteResult
from qpcr_assay_check.taxonomy.exclusivity import build_exclusivity
from qpcr_assay_check.taxonomy.plan import OrganismListResolution
from qpcr_assay_check.taxonomy.resolve import Resolution
from qpcr_assay_check.verdict import Verdict

SEV = load_config().specificity.severity

CT, NG = 813, 485  # Chlamydia trachomatis, Neisseria gonorrhoeae


def site(
    taxid: int, role: str, level: str, tier: str = "exclusivity", site_id: str = "S1"
) -> SiteResult:
    return SiteResult(
        id=site_id, tier=tier, query=role, role=role, oligo="A" * 20, accession="AB000001.1",
        taxid=taxid, organism="Test organism", orientation="+", subject_start=1, subject_end=20,
        source="blast_full", q_aln="A" * 20, s_aln="A" * 20, midline="|" * 20, n_match=20,
        n_mismatch=0, n_gap=0, n_ambiguous=0, defect_positions=[], mismatches_last5=0,
        mismatches_last3=0, terminal_defect=False, clean_3prime_nt=20, level=level,
    )  # fmt: skip


def amplicon(taxid: int, classification: str, tier: str = "exclusivity") -> AmpliconResult:
    return AmpliconResult(
        id="A1", tier=tier, accession="AB000001.1", taxid=taxid, organism="Test organism",
        roles="forward/reverse", left_site="S1", right_site="S2", start=1, end=100, length=100,
        classification=classification, record_type="genomic",
    )  # fmt: skip


def resolution(*rows: Resolution) -> OrganismListResolution:
    return OrganismListResolution(resolutions=list(rows))


def test_an_organism_with_a_critical_site_fails_and_shows_up_as_the_best_site():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    sites = [site(CT, "forward", "critical")]
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True)
    assert out.verdict is Verdict.FAIL  # primer_site_critical defaults to FAIL
    (row,) = out.rows
    assert row.organism == "Chlamydia trachomatis" and row.taxid == CT
    assert row.n_sites == 1 and row.best_site_level == "critical" and row.best_site_id == "S1"


def test_an_organism_with_zero_hits_is_still_a_row():
    res = resolution(Resolution(name="Neisseria gonorrhoeae", status="resolved", taxid=NG))
    out = build_exclusivity(res, [], [], SEV, tier_searched=True)
    (row,) = out.rows
    assert row.n_sites == 0 and row.best_site_level is None and row.best_site_id is None
    assert out.verdict is Verdict.PASS


def test_an_unresolved_name_is_reported_not_silently_dropped():
    res = resolution(
        Resolution(name="Mycoplasma pneumoniae", status="unresolved"),
        Resolution(name="Some genus sp.", status="ambiguous", candidates=[1, 2]),
    )
    out = build_exclusivity(res, [], [], SEV, tier_searched=True)
    assert out.n_organisms == 2 and out.n_resolved == 0
    assert {r.name for r in out.unresolved} == {"Mycoplasma pneumoniae", "Some genus sp."}
    assert {row.resolution for row in out.rows} == {"unresolved", "ambiguous"}
    assert all(row.taxid is None and row.n_sites == 0 for row in out.rows)


def test_the_best_site_is_the_most_severe_not_the_first():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    sites = [
        site(CT, "forward", "minor", site_id="S1"),
        site(CT, "reverse", "critical", site_id="S2"),
        site(CT, "probe", "warning", site_id="S3"),
    ]
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True)
    (row,) = out.rows
    assert row.n_sites == 3 and row.best_site_level == "critical" and row.best_site_id == "S2"


def test_a_predicted_amplicon_is_reflected_on_its_organisms_row():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    amps = [amplicon(CT, "likely_detected")]
    out = build_exclusivity(res, [], amps, SEV, tier_searched=True)
    (row,) = out.rows
    assert row.amplicon_predicted and row.amplicon_classification == "likely_detected"
    assert out.verdict is Verdict.FAIL  # amplicon_likely_detected defaults to FAIL


def test_hits_outside_the_exclusivity_tier_are_ignored():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    sites = [site(CT, "forward", "critical", tier="background")]
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True)
    (row,) = out.rows
    assert row.n_sites == 0 and out.verdict is Verdict.PASS


def test_a_tier_that_was_never_searched_is_incomplete_not_a_pass():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    out = build_exclusivity(res, [], [], SEV, tier_searched=False)
    assert out.verdict is Verdict.INCOMPLETE


def test_no_resolution_at_all_is_an_empty_incomplete_report():
    out = build_exclusivity(None, [], [], SEV, tier_searched=False)
    assert out.rows == [] and out.n_organisms == 0 and out.verdict is Verdict.INCOMPLETE
