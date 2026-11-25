"""The third report review (2026-11-25), built at the user's request ("Build everything except
M3"): print flow, sign-off corrections, cuts, and figures instead of tables."""

from __future__ import annotations

import re

from qpcr_assay_check.config import load_config
from qpcr_assay_check.report import charts
from qpcr_assay_check.report.grouping import gap_text, plain_tiers, tier_name
from qpcr_assay_check.report.html import floor_summary, render_report

from .test_exclusivity import site
from .test_multi_copy import run_report_result

ZONES = charts.Zones(crit_mm=3, crit_gaps=0, crit_clean=5, warn_mm=5, warn_gaps=1, warn_clean=3)


def test_tables_break_between_rows_and_headings_stay_with_what_follows(tmp_path):
    html = render_report(run_report_result(tmp_path), load_config())
    css = html[html.index("@media print") : html.index("</style>")]
    assert (
        "table { break-inside: auto; }" in css and "thead { display: table-header-group; }" in css
    )
    assert "h2, h3, h4 { break-after: avoid; }" in css
    assert "table.summary, table.review-box, table.tiers { break-inside: avoid; }" in css


def test_the_tm_mark_sits_at_the_worst_variant_and_the_bands_are_named():
    rows = [charts.TmRow("FP", 68.0, 72.5, "FAIL"), charts.TmRow("P", 65.0, 65.0, "PASS", False)]
    svg = charts.tm_strip(rows, (58, 66), (54, 70), 60)
    assert "worst variant 72.5 °C" in svg and "preferred 58–66" in svg and ">limit<" in svg


def test_the_coverage_steps_draw_the_window_apart():
    svg = charts.coverage_steps(
        [("listed", 618), ("region found", 614)], ("released 2023–2026", 223)
    )
    assert "223 released 2023–2026" in svg and "url(#q-risk)" in svg and "judged, window" not in svg


def test_plain_tier_names_replace_configuration_keys():
    assert tier_name("near_neighbours") == "Near neighbours" and tier_name("target") == "Target"
    text = "Off-target tiers assessed: near_neighbours, background. Tier 'exclusivity': 3 sites."
    assert plain_tiers(text) == (
        "Off-target tiers assessed: Near neighbours, Background. Clinical organism list: 3 sites."
    )
    assert gap_text("configured tier(s) not searched", ["near_neighbours"]) == (
        "configured tier(s) not searched (Near neighbours)"
    )


def test_identical_floor_rows_become_one_sentence_and_the_rest_a_table():
    def row(tier, oligo, mm="2", full=False):
        return {"tier": tier, "oligo": oligo, "length": 22, "scores": [14], "mismatches": mm,
                "list_full": full, "source": "from hits", "unknown": 0, "score": "14"}  # fmt: skip

    floors = [row("background", "FP"), row("background", "P"), row("exclusivity", "RP", full=True)]
    s = floor_summary(floors)
    assert (s["n"], s["total"], s["mismatches"], s["list_full"]) == (2, 3, "2", False)
    assert [r["oligo"] for r in s["exceptions"]] == ["RP"]
    assert floor_summary([]) is None


def test_the_site_level_map_places_one_mark_per_organism_with_its_level():
    pts = [
        charts.MapPoint("HSV-2", "near_neighbours", 0, 22, 0, "critical", "t1"),
        charts.MapPoint("T. pallidum", "exclusivity", 4, 18, 0, "warning", "t2"),
        charts.MapPoint("H. ducreyi", "exclusivity", 0, 5, 4, "minor", "t3"),
        charts.MapPoint("N. meningitidis", "exclusivity", 5, 0, 0, "minor", "t4"),
    ]
    svg = charts.site_level_map(pts, ZONES, 22)
    assert "url(#z-crit)" in svg and "url(#z-warn)" in svg and "&gt;1 gap" in svg
    assert "H. ducreyi (4 gaps)" in svg and "N. meningitidis (0 clean 3′)" in svg
    assert svg.count(charts.LEVEL_FILL["critical"]) >= 2  # the HSV-2 mark and the key
    dot = charts.site_dot(pts[0], ZONES, 22)
    assert "0 mm" in dot and "22 clean 3′" in dot


def test_the_structure_strip_keeps_none_and_below_zero_out_of_the_axis():
    rows = [
        charts.StructRow("hairpin", "RP", 56.5, "WARN"),
        charts.StructRow("hairpin", "P", None, "PASS", found=False),
        charts.StructRow("dimer", "FP / RP", -3.0, "PASS"),
        charts.StructRow("dimer", "FP / P", 14.8, "PASS"),
    ]
    svg = charts.structure_strip(rows, 47.0, 60.0)
    assert ">none<" in svg and "&lt;0<" in svg and "56.5" in svg and "flagged" in svg
    assert "≥47 °C review" in svg and "≥60 °C" in svg


def test_the_accounting_figure_prints_every_count():
    bars = [
        charts.AcctBar("618 assemblies listed", [("#5B7C99", 614, "found"),
                                                 ("url(#q-del)", 2, "not found")],
                       "614 region found; 2 not found"),
        charts.AcctBar("forward", [("#2F6FA8", 594, "detectable copy"),
                                   ("url(#q-risk)", 20, "none")], "594 · 20 without", True),
    ]  # fmt: skip
    svg = charts.accounting(bars)
    assert "614 region found; 2 not found" in svg and "594 · 20 without" in svg
    assert charts.accounting([charts.AcctBar("x", [("#000", 0, "none")], "")]) == ""


def test_the_report_shows_the_new_figures_and_drops_the_repeats(tmp_path):
    result, cfg = run_report_result(tmp_path), load_config()
    cfg.report.include_charts = True
    html = render_report(result, cfg)
    part_b = html[html.index('<div class="part-b">') :]
    assert 'class="fig structs"' in part_b and 'class="fig acct"' in part_b
    assert 'class="fig tm"' not in part_b  # the Tm figure stands in Part A only
    assert "Settings from the assay file" not in html
    assert not re.search(r"<p>\S*chip[^<]*</span> off-target primer and probe sites", html)
    limits = html[
        html.index('<h3 id="limits">') : html.index("</table>", html.index('id="limits"'))
    ]
    assert " · " in limits  # one row per group


def test_an_incomplete_tier_row_names_its_gap_and_a_review_row_its_closest_site(tmp_path):
    from qpcr_assay_check.report.grouping import spec_overview
    from qpcr_assay_check.report.summary import summary_rows
    from qpcr_assay_check.specificity.models import Finding

    result = run_report_result(tmp_path)
    warn = site(1, "reverse", "warning", tier="exclusivity", site_id="W").model_copy(
        update={"n_mismatch": 4, "clean_3prime_nt": 18, "organism": "Treponema pallidum"}
    )
    findings = [
        Finding(severity="WARN", topic="sites", tier="exclusivity",
                kind="primer_warning_no_product", count=577, site="W", message="x"),
        Finding(severity="INCOMPLETE", topic="search", tier="background", about="P",
                short="Only the 2,000 strongest alignments checked for {about} "
                "(max_sites_per_query); weaker ones not assessed", message="Tier 'background': y"),
    ]  # fmt: skip
    spec = result.specificity.model_copy(update={
        "sites": [warn, site(2, "forward", "critical", tier="background", site_id="B")],
        "amplicons": [], "findings": findings,
        "searches": [{"tier": t, "taxids": [1], "rid": None, "n_hits": {}, "saturation": [],
                      "restriction": None} for t in ("exclusivity", "background")],
    })  # fmt: skip
    result = result.model_copy(update={"specificity": spec})
    rows_in = [{"tier": t, "taxids": [1], "saturated": []} for t in ("exclusivity", "background")]
    rows = summary_rows(result, load_config(), spec_overview(spec, result.assay, rows_in))
    (excl,) = [r for r in rows if r.figure == "tier:exclusivity"]
    assert excl.result == "no amplicon; 0 critical / 577 warning primer sites without amplicon"
    assert excl.reason == "closest primer site: reverse, 4 mm, 18 clean 3′ (Treponema pallidum)"
    (bg,) = [r for r in rows if r.figure == "tier:background"]
    assert bg.reason.startswith("Only the 2,000 strongest alignments checked for P")
