"""Condensed report tables (user request 2026-09-25: the report was too long to read).

All records, taxids and alignments below are SYNTHETIC."""

from __future__ import annotations

from types import SimpleNamespace as NS

from qpcr_assay_check.report.grouping import group_products, group_sites, species_of
from qpcr_assay_check.specificity.models import AmpliconResult

from .test_exclusivity import site


def product(pid, tier, acc, taxid, organism, cls="likely_detected", start=10, roles="F/R"):
    return AmpliconResult(id=pid, tier=tier, accession=acc, taxid=taxid, organism=organism,
                          roles=roles, left_site="L", right_site="R", start=start,
                          end=start + 73, length=74, classification=cls,
                          record_type="genomic")  # fmt: skip


def test_products_are_counted_once_and_grouped_per_tier_and_species():
    species = species_of([NS(taxid=11, species="Enterovirus G", scientific_name="EV-G 1"),
                          NS(taxid=12, species="Enterovirus G", scientific_name="EV-G 2"),
                          NS(taxid=21, species=None, scientific_name="Rhinovirus B")])  # fmt: skip
    amps = [
        product("A1", "out_of_scope", "X1", 11, "EV-G 1"),
        product("A2", "out_of_scope", "X1", 11, "EV-G 1"),  # the same product again (_v2)
        product("A3", "out_of_scope", "X2", 12, "EV-G 2"),
        product("A4", "near_neighbours", "R1", 21, "Rhinovirus B", cls="amplified_not_detected"),
    ]
    sites = {"L": site(11, "forward", "critical"), "R": site(11, "reverse", "critical")}
    groups = group_products(amps, sites, species)
    assert [(g.tier, g.species, g.n_products, g.n_records) for g in groups] == [
        ("near_neighbours", "Rhinovirus B", 1, 1),  # must-not-detect first
        ("out_of_scope", "Enterovirus G", 2, 2),  # two taxa, one species; duplicate dropped
    ]
    assert groups[1].names == {"EV-G 1": 1, "EV-G 2": 1}


def test_sites_are_grouped_per_species_closest_first():
    s1 = site(21, "reverse", "critical", tier="near_neighbours", site_id="S1")
    s2 = site(21, "probe", "warning", tier="near_neighbours", site_id="S2").model_copy(
        update={"n_mismatch": 2}
    )
    s3 = site(9606, "reverse", "minor", tier="background", site_id="S3")  # minor: not shown
    groups = group_sites([s2, s1, s3], {21: "Rhinovirus B"})
    (g,) = groups
    assert (g.species, g.n_sites, g.levels["critical"], g.best.id) == ("Rhinovirus B", 2, 1, "S1")


def test_rare_safe_variants_are_one_row_but_rare_risky_ones_stay(tmp_path):
    """Lump variants < 0.1 % only when perfect or tolerated (advisor): a rare variant with a
    3'-end problem is exactly what the yearly re-evaluation should show."""
    from qpcr_assay_check.config import load_config
    from qpcr_assay_check.report.html import render_report

    from .test_multi_copy import run_report_result

    result, cfg = run_report_result(tmp_path), load_config()
    vs = result.variant_summary
    fwd = vs.oligos[0]
    base = fwd.rows[0]
    extra = [base.model_copy(update={"percent": 0.05, "count": 1, "grade": g,
                                     "example_accession": f"RARE{i}.1"})
             for i, g in enumerate(["tolerated", "tolerated", "likely_failure"])]  # fmt: skip
    oligos = [fwd.model_copy(update={"rows": [*fwd.rows, *extra]}), *vs.oligos[1:]]
    result = result.model_copy(update={"variant_summary": vs.model_copy(update={"oligos": oligos})})
    html = render_report(result, cfg)
    assert "2 other variants" in html and "RARE2.1" in html
    assert "RARE0.1" not in html and "RARE1.1" not in html
