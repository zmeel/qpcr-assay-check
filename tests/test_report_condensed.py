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


def _site(grade, mm=0, rule="", note=""):
    return NS(grade=grade, n_mismatch=mm, grade_rule=rule, note=note)


def _frag(f, p, r, count, org="EV-A71"):
    return NS(forward=f, probe=p, reverse=r, count=count, organisms=[(org, count)])


def test_fragment_outcome_is_the_worst_site_and_the_pair_rule():
    from qpcr_assay_check.report.grouping import fragment_outcome

    ok, tol = _site("perfect"), _site("tolerated", 1)
    assert fragment_outcome(_frag(ok, ok, tol, 1)) == ("detectable", False)
    assert fragment_outcome(_frag(_site("likely_failure", 1), ok, ok, 1))[0] == "likely failure"
    assert fragment_outcome(_frag(ok, _site("indeterminate", 1, "R9"), ok, 1))[0] == "undetermined"
    bulge = _site("indeterminate", 0, "R5", note="poly-A run 7->8")
    assert fragment_outcome(_frag(bulge, ok, ok, 1))[0] == "at risk"  # strict
    assert fragment_outcome(_frag(bulge, ok, ok, 1), bulges=True)[0] == "detectable"
    # 3 + 2 tolerated-looking mismatches: the primer-pair rule decides (Lefever 2013)
    three, two = _site("at_risk", 3), _site("at_risk", 2)
    assert fragment_outcome(_frag(three, ok, two, 1)) == ("likely failure", True)


def test_fragment_view_lists_every_problem_and_lumps_only_detectable():
    from qpcr_assay_check.report.grouping import fragment_view

    ok, bad = _site("perfect"), _site("likely_failure", 1)
    frags = [_frag(ok, ok, ok, 100 - i, org=f"T{i}") for i in range(15)]
    frags += [_frag(bad, ok, ok, 2, org="EV-D68") for _ in range(35)]
    total = sum(f.count for f in frags)
    v = fragment_view(frags, total)
    assert len(v.attention) == 30 and v.attention_grouped == [("likely failure", "EV-D68", 5, 10)]
    assert len(v.detectable_top) == 10 and v.detectable_rest == 5
    assert v.records["likely failure"] == 70 and v.records["detectable"] == total - 70


def test_ungraded_combinations_are_never_shown_as_detectable():
    """Review finding: rows without a class ('') were lumped into 'Detectable'."""
    from qpcr_assay_check.report.grouping import fragment_view

    ungraded = _site(None, 1)
    v = fragment_view([_frag(ungraded, ungraded, ungraded, 5)], 5)
    assert not v.detectable_top and v.detectable_rest == 0
    assert [o for _f, o, _p in v.attention] == [""] and v.records["not classified"] == 5


def test_rows_that_can_fail_are_always_shown():
    """Review finding: products the probe would detect beyond 15 rows were only in the workbook."""
    from qpcr_assay_check.report.grouping import shown_rows

    groups = [NS(tier="background", n_detected=0, name=i) for i in range(20)]
    groups += [NS(tier="exclusivity", n_detected=1, name=f"D{i}") for i in range(5)]
    groups += [NS(tier="out_of_scope", n_detected=3, name="O")]
    shown, hidden = shown_rows(groups, "n_detected", 15)
    assert hidden == 5 and len(shown) == 20
    assert all(g in shown for g in groups[20:25]) and groups[-1] not in shown
