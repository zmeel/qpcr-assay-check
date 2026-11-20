"""The report's inline-SVG figures (report review 2026-11-20): well-formed, honest about what
they leave out, deterministic, and never the only place a number lives."""

import re
import xml.etree.ElementTree as ET

from qpcr_assay_check.report import charts
from qpcr_assay_check.report.charts import Counts, SiteColumn, TmRow, YearRow

SVG = "{http://www.w3.org/2000/svg}"


def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ', 1))


def widths(root: ET.Element) -> list[float]:
    """The widths of the class segments."""
    return [
        float(r.get("width"))
        for r in root.iter(SVG + "rect")
        if r.get("fill", "").startswith(("#2F", "url(#q"))
    ]


def test_every_figure_is_well_formed_xml_with_a_text_label():
    figs = [
        charts.defs(),
        charts.window_meter(Counts(90, 5, 3, 1, 4), 95, 80),
        charts.coverage_steps([("listed", 618), ("assessed", 618), ("region found", 614)]),
        charts.tm_strip(
            [TmRow("F", 68.0, 72.5, "FAIL"), TmRow("P", 69.0, 69.0, "PASS", False)],
            (58, 66),
            (54, 70),
            60,
        ),  # fmt: skip
        charts.year_bars([YearRow("2024", Counts(10, 1, 0, 0, 2), True)]),
        charts.site_map("F", "ACGTACGTAC", 20, {3: SiteColumn({"tolerated": 4}, gaps=1)}, 5),
        charts.site_glyph("ACGTACGT", "ACCTNCGT", 5, "closest site"),
    ]
    for svg in figs:
        root = parse(svg)
        if svg is not figs[0]:
            assert root.get("role") == "img" and root.get("aria-label")
            assert root.find(SVG + "title") is not None


def test_the_window_meter_leaves_the_undetermined_out_and_says_how_many():
    svg = charts.window_meter(Counts(90, 5, 3, 2, 7), 95, 80, width=200)
    root = parse(svg)
    assert abs(sum(widths(root)) - 200) < 0.2  # the judged genomes fill the bar
    assert "7 undetermined" in root.get("aria-label") and "of 100 judged" in root.get("aria-label")
    assert root.get("aria-label").startswith("Status window: 90.0% detectable")


def test_a_zero_class_draws_no_segment_and_undetermined_is_never_hidden():
    root = parse(charts.year_bars([YearRow("2025", Counts(50, 0, 0, 0, 3))], width=600))
    titles = [t.text for t in root.iter(SVG + "title")]
    assert any("undetermined 3" in t for t in titles)
    assert not any("at risk 0" in t for t in titles)


def test_years_with_few_judged_genomes_are_pale_and_labelled_and_n_is_printed():
    svg = charts.year_bars([YearRow("2017", Counts(4), few=True), YearRow("2024", Counts(100, 7))])
    assert 'opacity="0.45"' in svg and "4 · few records" in svg and "107 · 7 at risk" in svg


def test_the_status_window_is_bracketed():
    svg = charts.year_bars([YearRow("2022", Counts(5)), YearRow("2023", Counts(5), True)])
    assert ">window</text>" in svg


def test_figures_are_deterministic():
    def make():
        return charts.year_bars([YearRow("2024", Counts(10, 1, 2, 0, 3), True)]) + charts.site_map(
            "R", "ACGTACGTACGT", 9, {0: SiteColumn({"at_risk": 2}), 11: SiteColumn(gaps=1)}, 5
        )

    assert make() == make()


def test_the_site_map_prints_the_count_above_each_column_and_marks_the_3_end():
    svg = charts.site_map("F", "ACGTACGTAC", 614, {0: SiteColumn({"tolerated": 613})}, 5)
    assert ">613</text>" in svg and ">3′</text>" in svg
    no_tail = charts.site_map("P", "ACGTACGTAC", 614, {}, 0)
    assert ">3′</text>" not in no_tail and "none" in parse(no_tail).get("aria-label")


def test_an_out_of_limit_tm_is_a_triangle_and_the_range_is_in_the_label():
    svg = charts.tm_strip([TmRow("FP", 68.0, 72.5, "FAIL")], (58, 66), (54, 70), 60)
    assert "<path" in svg and "outside the limit" in svg
    assert "FP 68.0–72.5" in parse(svg).get("aria-label")


def test_names_are_escaped():
    svg = charts.site_map("<x>", "ACGT", 1, {}, 0)
    assert "<x>" not in svg and "&lt;x&gt;" in svg


def test_no_figure_holds_a_number_the_report_text_lacks(n1):
    """Every count a year bar labels is in the per-year table of Part B too."""
    from datetime import UTC, datetime

    from qpcr_assay_check.config import load_config
    from qpcr_assay_check.inclusivity.models import FragmentYear, InclusivityResult
    from qpcr_assay_check.pipeline import evaluate
    from qpcr_assay_check.report.html import render_report

    years = [FragmentYear(year=2024, with_region=40, detectable=37, at_risk=2, likely_failure=1),
             FragmentYear(year=2025, with_region=60, detectable=59, undetermined=1)]  # fmt: skip
    inc = InclusivityResult(
        verdict="WARN", tier_searched=True, sample_scheme="Every genome assembly", oligos=[],
        exhaustive=True, fragment_years=years, rationale=[], limitations=[],
    )  # fmt: skip
    cfg = load_config()
    result = evaluate(n1, cfg, now=datetime(2026, 1, 2, tzinfo=UTC), inclusivity=inc)
    html = render_report(result, cfg)
    svg = re.search(r'<svg class="fig years".*?</svg>', html, re.S).group(0)
    table = html[html.index("<h4>Per year (whole fragment)</h4>") :]
    for n in re.findall(r"(\d+) · ", svg):
        assert f">{n}" in table or f"{n} " in table
