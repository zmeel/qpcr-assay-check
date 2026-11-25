import re
from datetime import UTC, datetime
from html.parser import HTMLParser

from openpyxl import load_workbook

from qpcr_assay_check.config import load_config
from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.report.xlsx import write_workbook

from .conftest import make_assay

NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC)


def render(assay, charts=False, qc_only=True):
    cfg = load_config()
    cfg.report.include_charts = charts
    return render_report(evaluate(assay, cfg, qc_only=qc_only, now=NOW), cfg)


def test_report_states_the_required_disclaimers(n1):
    html = render(n1)
    assert "does not replace experimental validation" in html
    assert "responsible for verifying this software within its own quality system" in html
    assert "no data was sent to NCBI" in html


def test_report_is_a_timestamped_version_stamped_record(n1):
    html = render(n1)
    assert "2026-09-20T12:00:00Z" in html
    assert "qpcr-assay-check v" in html
    assert re.search(r"[0-9a-f]{64}", html)  # full inputs hash


def test_full_run_report_says_incomplete_is_not_a_pass(n1):
    html = render(n1, qc_only=False)
    # no verdict word: a summary table with a status per check (user, 2026-09-27)
    assert (
        '<span class="chip s-INCOMPLETE status-INCOMPLETE"><span class="ico" aria-hidden="true">'
        "◌</span>Incomplete</span>" in html
    )
    # QC rules in the report's own words, and "No flags" drawn neutral, not as "passed"
    assert "preferred 18–30 nt; limit 15–40 nt" in html and "PASS 18" not in html
    assert ".chip.status-PASS { background: var(--info-bg)" in html
    assert "it is not a pass or fail of the assay" in html
    assert "never counts as no flags" in html and "Not assessed" in html
    assert "Not evaluated" in html  # the findings behind the summary
    assert "Reviewer's decision" in html and "Overall verdict" not in html


def test_user_supplied_text_is_html_escaped():
    html = render(
        make_assay(assay_name="<script>alert(1)</script> & co", notes="<img src=x onerror=1>")
    )
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x" not in html


class _RefCollector(HTMLParser):
    """Collect attributes of real HTML tags that would make the browser fetch something."""

    def __init__(self) -> None:
        super().__init__()
        self.refs: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"src", "href", "action", "data", "poster", "srcset"} and value:
                self.refs.append((tag, key, value))


def test_report_with_charts_is_self_contained(n1):
    """No tag may make the browser load another file or host (links to NCBI pages are allowed).
    The Tm chart is inline SVG: no script at all, and the report stays small (it was about 5 MB
    with the inlined Plotly bundle; user, 2026-09-25)."""
    html = render(n1, charts=True)
    assert '<svg class="fig' in html and "<script" not in html
    assert len(html.encode()) < 500_000
    parser = _RefCollector()
    parser.feed(html)
    # only plain links to NCBI record pages, which load nothing until clicked, and to sections
    assert all(
        tag == "a"
        and key == "href"
        and (value.startswith("https://www.ncbi.nlm.nih.gov/") or value.startswith("#"))
        for tag, key, value in parser.refs
    ), parser.refs
    assert "<link " not in html


def test_three_prime_end_is_marked(n1):
    assert '<b class="tail">' in render(n1)


def test_degenerate_and_modified_probe_are_explained():
    html = render(make_assay(forward="GACCCCAAAATCAGCGAAAW", probe_modifications=["MGB"]))
    assert "2 variants" in html
    assert "Tm reliability" in html


def test_workbook_has_expected_sheets(n1, tmp_path):
    cfg = load_config()
    result = evaluate(n1, cfg, qc_only=True, now=NOW)
    path = tmp_path / "r.xlsx"
    write_workbook(result, path, cfg)
    wb = load_workbook(path)
    assert wb.sheetnames == [
        "Summary", "Inputs", "Oligo QC", "Structures", "Configuration", "Sections", "Checks",
        "Findings",
    ]  # fmt: skip
    # the full configuration lives in the workbook (report review 2026-11-20, second round)
    config = {row[0].value: row[1].value for row in wb["Configuration"].iter_rows(min_row=2)}
    assert config["inclusivity.warn_below_percent"] == "95.0"
    checks = [row[0].value for row in wb["Checks"].iter_rows(min_row=2)]
    assert checks == ["Oligo design (Tm, GC, runs, hairpins, dimers)"]  # --qc-only
    summary = {row[0].value: row[1].value for row in wb["Summary"].iter_rows(min_row=2)}
    assert summary["Assay"] == "CDC N1"
    assert summary["Review status"] == "Review"
    assert wb["Oligo QC"].max_row == len(result.oligo_qc.checks) + 1


def test_oligo_quality_control_is_evidence_at_the_end_of_part_b_and_prints(n1):
    """User 2026-09-25: the oligo checks do not change between runs and matter mainly when
    designing the PCR, so they sit near the end; report review 2026-11-20: folded in a closed
    <details> they did not print, so the record lacked them. Now the last part of the evidence,
    not folded, flagged checks first."""
    html = render(n1)
    qc = html.index('<h3 id="oligo-qc">Oligo quality control</h3>')
    assert html.index("<h2>Assay as evaluated</h2>") < qc < html.index('<h2 id="appendix">')
    assert '<details class="qc">' not in html and "<h3>Hairpins and dimers</h3>" in html
    assert "<h2>Hairpins and dimers</h2>" not in html


def test_the_sign_off_part_states_the_limits_of_the_record_and_nothing_of_it_is_folded(n1):
    """Report review 2026-11-20: the required statements appeared only at the end, and closed
    <details> sections (oligo QC, findings, configuration) did not print."""
    html = render(n1, qc_only=False)
    first = html.index('<h2 id="summary"')
    assert html.index("does not replace experimental validation") < first
    assert html.index("verifies this software within its own quality system") < first
    assert html.index("Reviewer's decision") < html.index('<div class="part-b">')
    # what folds on screen is only a variant's three-line alignment; the record itself does not
    assert set(re.findall(r'<details(?: class="([^"]*)")?', html)) <= {"changes", "more"}
    assert "details::details-content" in html  # and the browser opens even that for print
    # the status sentence names the categories instead of "N of M checks flagged for review"
    assert "flagged for review" not in html


def test_tables_wrap_in_print_instead_of_being_cut_off(n1):
    """Report review 2026-11-20, second round: wide tables scrolled, so on paper their right
    edge (a reverse primer's 3' end among it) was cut off."""
    html = render(n1, qc_only=False)
    css = html[html.index("@media print") : html.index("</style>")]
    assert ".scroll { overflow: visible; }" in css and "white-space: normal" in css


def test_the_sign_off_lists_limits_and_gaps_in_full_and_review_once_per_check(n1):
    """Report review 2026-11-20, second round: the full findings list pushed the decision box
    to a third page."""
    from qpcr_assay_check.report.html import decision_lines
    from qpcr_assay_check.report.summary import summary_rows

    cfg = load_config()
    from .test_report_exclusivity import _specificity_with_exclusivity

    result = evaluate(n1, cfg, now=NOW, specificity=_specificity_with_exclusivity())
    rows = summary_rows(result, cfg, [])
    lines = decision_lines(result, rows)
    warn_rows = [r for r in rows if r.css == "WARN"]
    assert len([x for x in lines if x[0] == "WARN"]) == len(warn_rows)
    spec_fail = [f for f in result.specificity.findings if f.severity in ("FAIL", "INCOMPLETE")]
    assert len([x for x in lines if x[1].startswith("Specificity: ")]) == len(spec_fail)
    html = render_report(result, cfg)
    assert html.index("<h3>Findings that need a decision</h3>") < html.index("Reviewer's decision")
    # the full list is the workbook's; each finding stands in its own section (user, 2026-11-25)
    assert "All findings behind the summary" not in html
    assert 'workbook sheet "Findings"' in html[: html.index('<div class="part-b">')]
