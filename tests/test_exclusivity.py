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


def test_an_organism_with_a_critical_site_warns_and_shows_up_as_the_best_site():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    sites = [site(CT, "forward", "critical")]
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True)
    assert out.verdict is Verdict.WARN  # no product: primer_site_critical_no_product (WARN)
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
    # nothing was searched for them: missing evidence, never a pass (review 2026-11-17, P2)
    assert out.verdict is Verdict.INCOMPLETE


def test_one_unresolved_name_among_clean_rows_is_incomplete_not_a_pass():
    res = resolution(
        Resolution(name="Neisseria gonorrhoeae", status="resolved", taxid=NG),
        Resolution(name="Mycoplasma pneumoniae", status="unresolved"),
    )
    assert build_exclusivity(res, [], [], SEV, tier_searched=True).verdict is Verdict.INCOMPLETE
    found = build_exclusivity(res, [site(NG, "forward", "critical")], [], SEV, tier_searched=True)
    # missing evidence outranks Review (tiers review 2026-11-20, F7); only Exceeds limit beats it
    assert found.verdict is Verdict.INCOMPLETE
    sev_fail = SEV.model_copy(update={"primer_site_critical_no_product": "FAIL"})
    failed = build_exclusivity(
        res, [site(NG, "forward", "critical")], [], sev_fail, tier_searched=True
    )
    assert failed.verdict is Verdict.FAIL


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


TARGET = 2697049  # e.g. SARS-CoV-2: a common organism-list entry that can also be the target


def test_the_assay_s_own_target_is_flagged_not_treated_as_an_off_target_hit():
    """A live run found: when the target organism is also in the clinical organism list (a
    respiratory panel listing SARS-CoV-2 alongside a SARS-CoV-2 assay's other targets), its own
    perfect, intended match was reported as a critical off-target site -- a false FAIL. The row
    must still appear (never silently dropped), but flagged and excluded from the verdict."""
    res = resolution(
        Resolution(
            name="Severe acute respiratory syndrome coronavirus 2",
            status="resolved",
            taxid=TARGET,
        ),
        Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT),
    )
    # even if evidence for the target taxid were somehow present (defence in depth -- the real
    # fix is that search/execute.py never searches for it), it must not count.
    sites = [site(TARGET, "forward", "critical"), site(CT, "forward", "critical")]
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True, target_taxid=TARGET)
    by_name = {row.organism: row for row in out.rows}
    target_row = by_name["Severe acute respiratory syndrome coronavirus 2"]
    assert target_row.is_target is True
    assert target_row.n_sites == 0
    assert target_row.best_site_level is None
    assert by_name["Chlamydia trachomatis"].is_target is False
    assert by_name["Chlamydia trachomatis"].n_sites == 1


def test_without_a_target_taxid_no_row_is_flagged():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    out = build_exclusivity(res, [], [], SEV, tier_searched=True, target_taxid=None)
    assert all(not row.is_target for row in out.rows)


def test_the_resolution_s_source_is_carried_onto_the_result():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    res.source = "assay"
    out = build_exclusivity(res, [], [], SEV, tier_searched=True)
    assert out.source == "assay"


def test_source_defaults_to_global_when_the_resolution_does_not_say():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    out = build_exclusivity(res, [], [], SEV, tier_searched=True)
    assert out.source == "global"


def test_no_resolution_has_no_source_either():
    out = build_exclusivity(None, [], [], SEV, tier_searched=False)
    assert out.source is None


# --------------------------------------------------------------- species-level grouping
# A BLAST hit's own taxid can be a strain-level descendant of an organism-list entry's own
# (coarser) resolved taxid -- confirmed live for Influenza A (~10% of hits under a
# species-restricted search carried a distinct, more specific taxid). Without taxon_species,
# such a hit's evidence would silently never match any row.

FLU, FLU_STRAIN = 11320, 999001  # Influenza A virus; a made-up specific-strain descendant


def test_a_hit_on_a_more_specific_descendant_taxid_still_counts_toward_its_species_row():
    res = resolution(Resolution(name="Influenza A virus", status="resolved", taxid=FLU))
    sites = [site(FLU_STRAIN, "forward", "critical")]
    species = {FLU: "Influenza A virus", FLU_STRAIN: "Influenza A virus"}
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True, taxon_species=species)
    (row,) = out.rows
    assert row.n_sites == 1 and row.best_site_level == "critical"


def test_without_taxon_species_a_descendant_taxid_hit_is_missed():
    """The pre-fix behaviour: exact taxid equality only. Documents the gap this fix closes."""
    res = resolution(Resolution(name="Influenza A virus", status="resolved", taxid=FLU))
    sites = [site(FLU_STRAIN, "forward", "critical")]
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True)
    (row,) = out.rows
    assert row.n_sites == 0


def test_a_hit_with_no_known_species_falls_back_to_exact_taxid_matching():
    res = resolution(Resolution(name="Influenza A virus", status="resolved", taxid=FLU))
    sites = [site(FLU_STRAIN, "forward", "critical")]
    species = {FLU: "Influenza A virus"}  # the hit's own taxid is missing from the map
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True, taxon_species=species)
    (row,) = out.rows
    assert row.n_sites == 0  # never guessed into matching


def test_exact_taxid_matches_still_work_with_taxon_species_supplied():
    res = resolution(Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT))
    sites = [site(CT, "forward", "critical")]
    species = {CT: "Chlamydia trachomatis"}
    out = build_exclusivity(res, sites, [], SEV, tier_searched=True, taxon_species=species)
    (row,) = out.rows
    assert row.n_sites == 1


def test_amplicons_are_grouped_by_species_too():
    res = resolution(Resolution(name="Influenza A virus", status="resolved", taxid=FLU))
    amps = [amplicon(FLU_STRAIN, "likely_detected")]
    species = {FLU: "Influenza A virus", FLU_STRAIN: "Influenza A virus"}
    out = build_exclusivity(res, [], amps, SEV, tier_searched=True, taxon_species=species)
    (row,) = out.rows
    assert row.amplicon_predicted and row.amplicon_classification == "likely_detected"


def test_a_hit_belongs_to_the_most_specific_row_among_its_ancestors():
    """Tiers review 2026-11-20, F5: a row resolved to a genus collected none of its species'
    hits (grouping by species name or exact taxid)."""
    genus, species, strain, other = 10, 11, 12, 20
    anc = {genus: {genus, 1}, species: {species, genus, 1}, strain: {strain, species, genus, 1},
           other: {other, genus, 1}}  # fmt: skip
    res = resolution(
        Resolution(name="Parechovirus", status="resolved", taxid=genus),
        Resolution(name="Parechovirus A", status="resolved", taxid=species),
    )
    out = build_exclusivity(
        res, [site(strain, "forward", "critical"), site(other, "reverse", "warning")], [], SEV,
        tier_searched=True, taxon_ancestors=anc,
    )  # fmt: skip
    rows = {r.organism: r for r in out.rows}
    assert rows["Parechovirus A"].n_sites == 1  # the strain: the species row, not the genus
    assert rows["Parechovirus"].n_sites == 1  # another species of the genus
    # without lineages: by species name or exact taxid, as before
    plain = build_exclusivity(
        res, [site(strain, "forward", "critical")], [], SEV, tier_searched=True
    )
    assert all(r.n_sites == 0 for r in plain.rows)


def test_a_row_searched_in_another_tier_says_so_and_shows_that_tier_s_evidence():
    res = resolution(Resolution(name="Homo sapiens", status="resolved", taxid=9606))
    human = site(9606, "forward", "critical").model_copy(update={"tier": "background"})
    out = build_exclusivity(res, [human], [], SEV, tier_searched=True, tier_of={9606: "background"})
    (row,) = out.rows
    assert row.searched_in == "background" and row.n_sites == 1
    assert out.verdict is Verdict.PASS  # counted in the background tier, not twice
