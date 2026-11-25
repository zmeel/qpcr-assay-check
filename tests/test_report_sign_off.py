"""The sign-off (Part A) on two printed pages, and the oligos in their order on the amplicon
(user, 2026-11-20, on the HSV-1 report: the long Incomplete lines pushed the decision box to a
third page, and the site maps put the probe last where everything else ends with the reverse
primer)."""

from __future__ import annotations

import re

from qpcr_assay_check.config import load_config
from qpcr_assay_check.report.html import decision_lines, render_report
from qpcr_assay_check.results import Status
from qpcr_assay_check.specificity.models import Finding

from .test_multi_copy import run_report_result


def _with_findings(result, findings):
    spec = result.specificity.model_copy(update={"findings": findings})
    return result.model_copy(update={"specificity": spec})


def test_gaps_of_one_kind_in_one_tier_make_one_short_sign_off_line(tmp_path):
    result = _with_findings(run_report_result(tmp_path), [
        Finding(severity="INCOMPLETE", topic="search", tier="background", about="FP_v8",
                short="relevant alignments cut at max_sites_per_query",
                message="Tier 'background', FP_v8: 2185 relevant alignments, only the 2000 "
                        "strongest were assessed (max_sites_per_query)."),
        Finding(severity="INCOMPLETE", topic="search", tier="background", about="P",
                short="relevant alignments cut at max_sites_per_query",
                message="Tier 'background', P: 5007 relevant alignments, only the 2000 "
                        "strongest were assessed (max_sites_per_query)."),
        Finding(severity="INCOMPLETE", topic="amplicons", tier="near_neighbours",
                short="product list cut at max_amplicons, not bounded",
                message="Tier 'near_neighbours': the list of predicted products was cut at "
                        "max_amplicons (per tier); not bounded: a probe site with a gap can "
                        "bind in this tier, and BLAST need not report one."),
        Finding(severity="INCOMPLETE", topic="search", message="An older finding, no short."),
        Finding(severity="WARN", topic="sites", message="Not on the sign-off."),
    ])  # fmt: skip
    spec = [text for _sev, text in decision_lines(result, []) if text.startswith("Specificity")]
    assert spec == [
        "Specificity, Background: relevant alignments cut at max_sites_per_query (FP_v8, P)",
        "Specificity, Near neighbours: product list cut at max_amplicons, not bounded",
        "Specificity: An older finding, no short.",
    ]
    html = render_report(result, load_config())
    part_b = html[html.index('<div class="part-b">') :]
    assert "5007 relevant alignments" in part_b  # the full wording stays in Part B
    assert "5007 relevant alignments" not in html[: html.index('<div class="part-b">')]


def test_an_oligo_check_beyond_its_limit_names_the_oligo_on_the_sign_off(tmp_path):
    result = run_report_result(tmp_path)
    qc = result.oligo_qc
    check = next(c for c in qc.checks if c.id.endswith(".tm"))
    failed = check.model_copy(update={"status": Status.FAIL, "message": "Tm of 72.5 °C is outside"})
    checks = [failed if c is check else c for c in qc.checks]
    result = result.model_copy(update={"oligo_qc": qc.model_copy(update={"checks": checks})})
    lines = [text for sev, text in decision_lines(result, []) if sev == "FAIL"]
    who = next(o for o in qc.oligos if (o.name or o.role) == check.subject)
    named = who.name if who.name and who.name != who.role else "Forward primer"
    assert f"{named}: Tm of 72.5 °C is outside" in lines


def test_the_decision_box_keeps_its_note_and_the_ncbi_line_is_in_the_header(tmp_path):
    html = render_report(run_report_result(tmp_path), load_config())
    box = html[html.index('<div class="review">') : html.index('<div class="part-b">')]
    assert "Reviewer's decision" in box and "The tool never fills it in." in box
    head = html[html.index("<header>") : html.index("</header>")]
    assert "NCBI" in head
    css = html[html.index("@media print") : html.index("</style>")]
    assert "svg.fig.years" in css and "td.write" in css


def test_site_maps_open_part_b_in_amplicon_order_and_part_a_keeps_the_totals(tmp_path):
    result, cfg = run_report_result(tmp_path), load_config()
    cfg.report.include_charts = True
    html = render_report(result, cfg)
    part_b = html.index('<div class="part-b">')
    maps = html.index('<div class="maps">')
    assert maps > part_b and html.index('id="site-maps"') > part_b
    assert 'href="#site-maps"' in html[:part_b]  # Part A points to them
    roles = {o.name: o.role for o in result.assay.oligo_list}
    shown = re.findall(r'<svg class="fig sitemap"[^>]*aria-label="([^"]*)"', html[maps:])
    order = [next(r for n, r in roles.items() if label.startswith(n)) for label in shown]
    rank = {"forward": 0, "probe": 1, "reverse": 2}
    assert order == sorted(order, key=rank.__getitem__) and order


def test_the_report_lists_oligos_forward_probe_reverse(tmp_path):
    result, cfg = run_report_result(tmp_path), load_config()
    roles = [o.role for o in result.assay.amplicon_list]
    assert list(dict.fromkeys(roles)) == ["forward", "probe", "reverse"]
    html = render_report(result, cfg)
    i = html.index("<h2>Assay as evaluated</h2>")
    assay = html[i : html.index("</table>", i)]
    assert assay.index("Forward primer") < assay.index("Probe") < assay.index("Reverse primer")
    i = html.index('<h3 id="oligo-qc">')
    qc = html[i : html.index("</thead>", i)]
    assert qc.index("Forward") < qc.index("Probe") < qc.index("Reverse")


def test_cut_lists_and_saturated_hit_lists_carry_the_short_wording():
    from qpcr_assay_check.specificity.findings import build_findings
    from qpcr_assay_check.specificity.models import TierCount

    cfg = load_config()
    counts = [TierCount(tier="background", query=q, blast_hits=5000, hsps_relevant=5007,
                        sites_assessed=2000, truncated=True) for q in ("FP_v8", "P")]  # fmt: skip
    found = build_findings(
        sites=[], amplicons=[], site_by_id={}, counts=counts,
        saturated=[("exclusivity", "RP", "")], off_tiers_seen=["background", "exclusivity"],
        intended_target={}, target_searched=False, n_primer_only=0, n_fetch_failed=0,
        amplicons_truncated={"near_neighbours"}, rules=cfg.specificity,
    )  # fmt: skip
    short = {(f.tier, f.short, f.about) for f in found if f.short}
    assert (
        "background",
        "Only the 2,000 strongest alignments checked for {about} "
        "(max_sites_per_query); weaker ones not assessed",
        "P",
    ) in short
    assert (
        "exclusivity",
        "BLAST hit list full for {about}; relevant hits may be missing (search.hitlist_size)",
        "RP",
    ) in short
    assert ("near_neighbours", "Amplicon list stopped at 500 (max_amplicons)", "") in short
