"""The listing rule of the Needs-attention table and the Part A layout fixes (user and advisor,
2026-11-27, on the influenza A report: 272 combinations, 30 listed, most under 0.1% of the
176,383 records; "Nobody is going to look in those")."""

from __future__ import annotations

from types import SimpleNamespace as NS

import pytest
from openpyxl import load_workbook
from pydantic import ValidationError

from qpcr_assay_check.config import NeedsAttention, load_config
from qpcr_assay_check.report.grouping import fragment_view, share, strains
from qpcr_assay_check.report.html import render_report

from .test_multi_copy import run_report_result


def _site(grade):
    return NS(grade=grade, n_mismatch=0, grade_rule="", note="")


def _frag(outcome_site, count, org="Influenza A virus"):
    ok = _site("perfect")
    return NS(forward=outcome_site, probe=ok, reverse=ok, count=count, organisms=[(org, count)])


def test_the_defaults_are_the_advised_bar():
    na = load_config().report.needs_attention
    assert (na.min_percent, na.likely_failure_min_percent, na.min_records) == (0.1, 0.01, 2)
    assert (na.top_per_outcome, na.max_rows) == (3, 20)


@pytest.mark.parametrize(
    "bad",
    [
        {"likely_failure_min_percent": 0.5},  # above min_percent
        {"min_percent": 101, "likely_failure_min_percent": 0.01},
        {"top_per_outcome": 0},
        {"min_records": 0},
        {"max_rows": 11},  # fewer than one top group per outcome
    ],
)
def test_settings_that_cannot_work_are_refused(bad):
    with pytest.raises(ValidationError):
        NeedsAttention(**bad)


def test_a_combination_is_listed_by_top_bar_or_likely_failure_bar():
    risk, fail = _site("at_risk"), _site("likely_failure")
    frags = [_frag(_site("perfect"), 9_000)]
    frags += [_frag(risk, n) for n in (300, 40, 30, 20, 9, 1)]  # bar: 0.1% of 10,000 = 10
    frags += [_frag(fail, n) for n in (50, 6, 5, 3, 1, 1)]  # likely-failure bar: 1 record
    total = 10_000
    v = fragment_view(frags, total)
    listed = [(o, f.count) for f, o, _p in v.attention]
    assert listed == [
        ("likely failure", 50), ("likely failure", 6), ("likely failure", 5),
        ("likely failure", 3),  # at or above the likely-failure bar, 2 records or more
        ("at risk", 300), ("at risk", 40), ("at risk", 30), ("at risk", 20),
    ]  # fmt: skip
    by_count = {f.count: v.listing[id(f)] for f in frags[1:]}
    assert by_count[300].startswith("yes: one of the 3 most frequent")
    assert by_count[20] == "yes: at or above the bar"
    assert by_count[9] == "no: below the bar" and by_count[1] == "no: below the bar"
    risk_row, fail_row = (
        next(g for g in v.attention_grouped if g.outcome == o)
        for o in ("at risk", "likely failure")
    )
    assert (risk_row.n, risk_row.records, risk_row.largest, risk_row.over_cap) == (2, 10, 9, 0)
    assert (fail_row.n, fail_row.records, fail_row.largest) == (2, 2, 1)


def test_the_report_states_the_rule_and_lists_it_under_limits_applied(tmp_path):
    result, cfg = run_report_result(tmp_path), load_config()
    vs = result.variant_summary
    assert vs is not None and vs.fragments
    html = render_report(result, cfg)
    assert 'column "Listed in the report"' in html
    assert "at most 20 rows (<code>report.needs_attention</code>, Part C)" in html
    limits = html[html.index('<h3 id="limits">') :]
    assert "Report listing (display only; no status depends on it)" in limits[:20_000]


def test_the_workbook_says_whether_and_why_a_combination_is_listed(tmp_path):
    from qpcr_assay_check.report.xlsx import write_workbook

    result = run_report_result(tmp_path)
    write_workbook(result, tmp_path / "r.xlsx", load_config())
    ws = load_workbook(tmp_path / "r.xlsx")["Fragment variants"]
    head = [c.value for c in ws[1]]
    col = head.index("Listed in the report")
    values = [row[col].value for row in ws.iter_rows(min_row=2)]
    assert values and all(v and v.split(":")[0] in ("yes", "no") for v in values)


def test_shares_below_one_percent_keep_two_significant_digits():
    # 154 of 176,383 records printed as "0.1%" sat below a 0.1% bar
    assert share(100.0 * 154 / 176_383) == "0.087%"
    assert share(0.0245) == "0.025%" and share(0.45) == "0.45%" and share(99.46) == "99.5%"
    assert share(0) == "0%" and share(0.0004) == "<0.001%"


def test_strain_names_are_grouped_under_their_organism():
    orgs = [
        ("Influenza A virus (A/swine/Oklahoma/A01798209/2015(H1N1))", 1),
        ("Influenza A virus (A/swine/Holguin/121/2010(H1N1))", 2),
        ("Influenza A virus", 9),
        ("Human alphaherpesvirus 1", 3),
    ]
    assert strains(orgs) == [("Influenza A virus", 12, 2), ("Human alphaherpesvirus 1", 3, 0)]
    assert strains(strains(orgs)) == strains(orgs)  # an already merged list passes through
    # NCBI writes some without a space before the bracket, and some "Virus" (influenza A,
    # 2026-11-27): the same organism
    odd = [("Influenza A virus(A/Penza/55/2008(H3N2))", 1), ("Influenza A Virus (A/x/1/2000)", 2),
           ("Influenza A virus", 5)]  # fmt: skip
    assert strains(odd) == [("Influenza A virus", 8, 2)]


def test_the_variant_table_fits_the_page_without_splitting_organism_names(tmp_path):
    # the influenza A table was 26 px wider than A4, so the browser printed the whole record
    # 3.6% smaller, and "Influenza" broke as "Influen za" (2026-11-27)
    html = render_report(run_report_result(tmp_path), load_config())
    css = html[html.index("@media print") : html.index("</style>")]
    assert "td.types { hyphens: manual; } table.frag td.types { min-width: 5rem; }" in css
    assert "table.frag td.types { min-width: 0; }" not in css
    assert "table.frag td:first-child .chip { white-space: normal; }" in css
    # labels break between words only, at the table's size (influenza A, 2026-11-27 09:20Z)
    assert "table.frag td:first-child .chip { overflow-wrap: normal; word-break: keep-all; }" in css
    assert "table.frag .chip { font-size: 6.5pt;" in css


def test_a_long_oligo_design_list_moves_to_the_sign_off(tmp_path):
    from qpcr_assay_check.report.grouping import spec_overview
    from qpcr_assay_check.report.html import decision_lines
    from qpcr_assay_check.report.summary import summary_rows
    from qpcr_assay_check.results import Status

    result = run_report_result(tmp_path)
    qc = result.oligo_qc
    checks = [c.model_copy(update={"status": Status.WARN if i < 5 else Status.PASS})
              for i, c in enumerate(qc.checks)]  # fmt: skip
    result = result.model_copy(update={"oligo_qc": qc.model_copy(update={"checks": checks})})
    spec = result.specificity
    rows = summary_rows(result, load_config(), spec_overview(spec, result.assay, []))
    (row,) = [r for r in rows if r.anchor == "oligo-qc"]
    assert row.reason == (
        "5 checks outside the preferred range, named under Findings that need a decision"
    )
    (line,) = [t for sev, t in decision_lines(result, rows) if t.startswith("Oligo design")]
    # each check once, with its oligos (user, 2026-11-27)
    assert line == (
        "Oligo design, outside the preferred range: length (forward); GC content (forward); "
        "Tm (forward); G/C in last 5 nt (3' end) (forward); 3' end stability (last 5 nt, "
        "nearest-neighbour ΔG°37) (forward)"
    )


def test_checks_are_named_once_with_their_oligos():
    from qpcr_assay_check.report.summary import grouped_checks

    qc = NS(
        oligos=[
            NS(name="infa_fwd", role="forward"),
            NS(name="infa_rev2", role="reverse"),
            NS(name="infa_probe1", role="probe"),
            NS(name="infa_probe2", role="probe"),
        ]
    )
    checks = [NS(subject=s, name=n) for s, n in [
        ("infa_fwd", "Forward primer infa_fwd Tm"),
        ("infa_probe1", "Probe infa_probe1 longest single-base run"),
        ("infa_probe2", "Probe infa_probe2 longest single-base run"),
        ("pair", "Primer Tm difference (forward vs reverse)"),
        ("infa_rev2", "Reverse infa_rev2 site in reference amplicon"),
        ("infa_probe2", "Probe infa_probe2 site in reference amplicon"),
    ]]  # fmt: skip
    assert grouped_checks(qc, checks) == (
        "Tm (infa_fwd); longest single-base run (infa_probe1, infa_probe2); Primer Tm difference "
        "(forward vs reverse); site in reference amplicon (infa_rev2, infa_probe2)"
    )


def test_an_amplicon_finding_is_one_short_line_on_the_sign_off(tmp_path):
    from qpcr_assay_check.report.html import decision_lines
    from qpcr_assay_check.specificity.models import Finding

    result = run_report_result(tmp_path)
    amp = NS(tier="exclusivity", classification="likely_detected", length=141,
             accession="ON845595.1", organism="Influenza B virus")  # fmt: skip
    finding = Finding(severity="FAIL", topic="amplicons", tier="exclusivity",
                      kind="products_detected", count=1,
                      message="Tier 'exclusivity': 1 predicted off-target amplicon(s) that "
                              "both primers and the probe should give signal for.")  # fmt: skip
    spec = result.specificity.model_construct(
        **{**dict(result.specificity), "amplicons": [amp], "findings": [finding]}
    )
    result = result.model_copy(update={"specificity": spec})
    lines = [t for sev, t in decision_lines(result, []) if sev == "FAIL"]
    assert (
        "Specificity, Clinical organism list: 1 amplicon detected by the probe (141 bp on "
        "ON845595.1, Influenza B virus)" in lines
    )
    assert not any("Tier 'exclusivity'" in t for t in lines)


def test_part_a_shows_two_needs_attention_rows():
    from qpcr_assay_check.report.html import ATTENTION_ON_PAGE_ONE

    assert ATTENTION_ON_PAGE_ONE == 2  # user, 2026-11-27: all of them stay in Part B


def test_part_a_shares_print_the_count_below_one_percent():
    from qpcr_assay_check.report.summary import _share_of

    assert _share_of(18, 73_327) == "0.025% (18)"  # was "0.0% likely failure"
    assert _share_of(0, 73_327) == "0%" and _share_of(7_333, 73_327) == "10.0%"


def test_the_folded_row_names_the_records_the_largest_and_where_they_fail(tmp_path):
    from qpcr_assay_check.report.grouping import fragment_outcome

    result, cfg = run_report_result(tmp_path), load_config()
    vs = result.variant_summary
    bad = next(f for f in vs.fragments if fragment_outcome(f)[0] != "detectable")
    extra = [bad.model_copy(update={"count": 1}) for _ in range(3)]  # SYNTHETIC copies
    vs = vs.model_copy(update={"fragments": [*vs.fragments, *extra]})
    result = result.model_copy(update={"variant_summary": vs})
    cfg.report.needs_attention = NeedsAttention(  # the top row only; the rest folded
        min_percent=100.0, likely_failure_min_percent=100.0, top_per_outcome=1, max_rows=4
    )
    part_b = render_report(result, cfg).split('<div class="part-b">', 1)[1]
    assert "not listed</strong>" in part_b and "the largest 1 record (" in part_b
    assert "Where they fail (records whose site is not detectable" in part_b
