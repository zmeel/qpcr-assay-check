"""The findings condensed (user, 2026-11-25): no "All findings behind the summary" list, the
specificity findings as one table per tier, QC messages only where they add to the cell."""

from __future__ import annotations

from qpcr_assay_check.config import load_config
from qpcr_assay_check.report.grouping import spec_overview
from qpcr_assay_check.report.html import (
    adds_to_cell,
    other_findings,
    render_report,
    tier_table,
)
from qpcr_assay_check.results import CheckResult, Status
from qpcr_assay_check.specificity.models import Finding

from .test_exclusivity import site
from .test_multi_copy import run_report_result


def _check(message: str, status: Status = Status.WARN) -> CheckResult:
    return CheckResult(id="FP.gc", subject="FP", name="Forward primer FP GC content",
                       status=status, display="68.2", message=message)  # fmt: skip


def test_a_qc_message_is_printed_only_where_it_adds_to_the_cell():
    assert not adds_to_cell(_check("GC content of 68.2% is outside the preferred range."))
    assert not adds_to_cell(_check("Tm of 72.5 °C is outside the limit (the worst of 8 variants)."))
    assert adds_to_cell(_check("4 G/C in the last 5 nt: the 3' end may be too stable."))
    assert adds_to_cell(
        _check("The FP oligo differs from the reference amplicon at 1 position(s).")
    )
    assert not adds_to_cell(_check(""))


def _spec(result, findings, sites=None):
    sites = sites if sites is not None else [
        site(1, "forward", "critical", tier="near_neighbours", site_id="S1"),
        site(1, "reverse", "warning", tier="near_neighbours", site_id="S2"),
    ]  # fmt: skip
    return result.specificity.model_copy(update={
        "sites": sites, "amplicons": [], "findings": findings,
        "scope": "Off-target tiers assessed: near_neighbours.",
        "searches": [{"tier": "near_neighbours", "taxids": [1, 2], "rid": None, "n_hits": {},
                      "saturation": [], "restriction": None}],
    })  # fmt: skip


FINDINGS = [
    Finding(severity="INFO", topic="search", message="Off-target tiers assessed: near_neighbours."),
    Finding(severity="WARN", topic="sites", tier="near_neighbours", kind="primer_warning",
            count=820, site="S2", message="Tier 'near_neighbours': 820 warning primer site(s)."),
    Finding(severity="WARN", topic="sites", tier="near_neighbours",
            kind="primer_critical_no_product", count=8607, site="S1",
            message="Tier 'near_neighbours': 8607 critical primer site(s) forming no product."),
    Finding(severity="INCOMPLETE", topic="amplicons", tier="near_neighbours",
            short="product list cut at max_amplicons, not bounded",
            message="Tier 'near_neighbours': the list was cut; not bounded: a gapped probe site."),
    Finding(severity="INCOMPLETE", topic="amplicons",
            short="Partner scan incomplete: 485 primer site(s) not scanned",
            message="Partner scan incomplete: 485 primer site(s) beyond the limit were not "
                    "scanned. A product whose second primer BLAST did not report can be missing."),
    Finding(severity="INFO", topic="search", message="Tier 'near_neighbours': 3 hit record(s) set "
            "aside, their organism being outside the taxa this tier searched."),
]  # fmt: skip


def test_the_specificity_findings_become_one_row_per_tier(tmp_path):
    result = run_report_result(tmp_path)
    spec = _spec(result, FINDINGS)
    overview = spec_overview(spec, result.assay, spec.searches and [
        {"tier": "near_neighbours", "taxids": [1, 2], "saturated": []}])  # fmt: skip
    t = tier_table(spec, overview, {s.id: s for s in spec.sites})
    (row,) = t["rows"]
    assert row["warning"] == {"n": 820, "severity": "WARN"}
    assert row["critical_no_product"] == {"n": 8607, "severity": "WARN"}
    assert row["critical_product"] == {"n": 0, "severity": None}
    assert row["status"] == "INCOMPLETE"
    assert [g["text"] for g in row["gaps"]] == ["product list cut at max_amplicons, not bounded"]
    assert [g["text"] for g in t["all_tiers"]] == [
        "Partner scan incomplete: 485 primer site(s) not scanned"
    ]
    # notes numbered in table order: the tier's gap first, then the gaps of all tiers
    assert [g["note"] for g in row["gaps"]] == [1] and t["all_tiers"][0]["note"] == 2
    assert len(t["notes"]) == 2 and "second primer BLAST" in t["notes"][1]
    assert row["closest"].id == "S1"  # critical forward, 0 mismatches, before the reverse
    # the scope has its own line; what fits no column stays a list
    assert [f.message[:30] for f in t["other"]] == ["Tier 'near_neighbours': 3 hit "]

    html = render_report(result.model_copy(update={"specificity": spec}), load_config())
    i = html.index('<table class="tiers">')
    table = html[i : html.index("</table>", i)]
    assert '<span class="chip s-WARN">8,607</span>' in table and "All tiers" in table
    assert "<h3>Findings</h3>" not in html  # the sentences are gone ...
    assert "second primer BLAST did not report" in html  # ... but each gap keeps its note
    assert "<h3>Other specificity findings</h3>" in html


def test_a_record_without_the_structured_fields_keeps_the_findings_list(tmp_path):
    result = run_report_result(tmp_path)
    old = [f.model_copy(update={"kind": "", "count": 0, "site": "", "short": "", "tier": ""})
           for f in FINDINGS]  # fmt: skip
    spec = _spec(result, old)
    html = render_report(result.model_copy(update={"specificity": spec}), load_config())
    assert '<table class="tiers">' not in html and "<h3>Findings</h3>" in html


def test_findings_shown_elsewhere_are_not_listed_again(tmp_path):
    result = run_report_result(tmp_path)
    extra = "Human background: no search in this run covered human (taxid 9606)."
    qc_line = next(f"{c.name}: {c.message}" for c in result.oligo_qc.checks if c.message)
    result = result.model_copy(update={"specificity": _spec(result, FINDINGS)})
    spec_line = f"Specificity: {FINDINGS[1].message}"
    overall = result.overall.model_copy(update={"rationale": [qc_line, spec_line, extra]})
    result = result.model_copy(update={"overall": overall})
    assert other_findings(result) == [extra]
    html = render_report(result, load_config())
    assert '<h2 id="findings">Other findings</h2>' in html and extra in html


def test_the_closest_primer_site_is_one_that_can_prime(tmp_path):
    """HSV-1, 2026-11-25: a minor reverse site (2 mismatches, 2 clean 3' nt) was shown as the
    clinical list's closest, while the row counts only warning and critical sites."""
    from qpcr_assay_check.report.figures import closest_by_tier

    result = run_report_result(tmp_path)
    minor = site(1, "reverse", "minor", tier="exclusivity", site_id="M").model_copy(
        update={"n_mismatch": 2, "clean_3prime_nt": 2}
    )
    warn = site(1, "reverse", "warning", tier="exclusivity", site_id="W").model_copy(
        update={"n_mismatch": 4, "clean_3prime_nt": 18}
    )
    spec = result.specificity.model_copy(update={"sites": [minor, warn]})
    rows = [{"tier": "exclusivity", "taxids": [1], "saturated": []}]
    (t,) = spec_overview(spec, result.assay, rows)
    assert t.closest["reverse"].id == "W"
    assert closest_by_tier([minor, warn])["exclusivity"].id == "W"
    assert "exclusivity" not in closest_by_tier([minor])


def test_summary_findings_said_in_the_products_paragraph_are_not_listed_again(tmp_path):
    result = run_report_result(tmp_path)
    said = [
        Finding(severity="INFO", topic="amplicons", kind="primer_only_summary",
                message="2174 primer site(s) at warning or critical level formed no product."),
        Finding(severity="INFO", topic="amplicons", kind="partner_scan_summary",
                message="Partner scan: 1000 window(s) next to 1485 unpaired sites."),
    ]  # fmt: skip
    spec = _spec(result, [*FINDINGS, *said]).model_copy(update={"n_primer_only": 2174})
    html = render_report(result.model_copy(update={"specificity": spec}), load_config())
    assert "2174 primer site(s) at warning or critical level" not in html
    assert "2174 primer site(s) that can prime formed no product." in html  # the paragraph


def test_the_product_table_names_the_tier_and_the_probe_signal_in_words():
    from qpcr_assay_check.report.html import _environment

    env = _environment()
    assert env.filters["tier_name"]("near_neighbours") == "Near neighbours"
    assert env.filters["tier_name"]("custom") == "custom"
    src = env.loader.get_source(env, "report.html.j2")[0]
    assert "'amplified_not_detected': 'amplified, not detected'" in src
    assert "<td>{{ g.tier | tier_name }}</td>" in src


def test_the_table_and_the_part_a_glyph_pick_the_same_site_on_a_tie(tmp_path):
    """HSV-1, 2026-11-25: forward and reverse tied (0 mismatches, 22 clean 3' nt); the glyph
    showed the reverse, the table the forward."""
    from qpcr_assay_check.report.figures import closest_by_tier

    result = run_report_result(tmp_path)
    fwd = site(1, "forward", "critical", tier="near_neighbours", site_id="S9")
    rev = site(1, "reverse", "critical", tier="near_neighbours", site_id="S2")
    spec = _spec(result, FINDINGS, sites=[fwd, rev])
    rows = [{"tier": "near_neighbours", "taxids": [1, 2], "saturated": []}]
    overview = spec_overview(spec, result.assay, rows)
    (row,) = tier_table(spec, overview, {s.id: s for s in spec.sites})["rows"]
    assert row["closest"] is closest_by_tier(spec.sites)["near_neighbours"]
    assert row["closest"].id == "S2"  # a tie goes to the lower site id, in both places
