"""Part C rebuilt after the advisor's review of 2026-11-27 (user: "Yes build all"): numbered
blocks C1-C7, tables at the full width, each point once, and nine corrections to the text."""

from __future__ import annotations

import re

from qpcr_assay_check.config import load_config
from qpcr_assay_check.report.html import _by_group, _plain, blast_split, render_report
from qpcr_assay_check.specificity.assess import LIMITATIONS

from .test_multi_copy import run_report_result


def _part_c(html: str) -> str:
    return html[html.index('<div class="part-c">') : html.index("<footer")]


def test_part_c_is_seven_numbered_blocks_without_the_old_prose(tmp_path):
    html = render_report(run_report_result(tmp_path), load_config())
    c = _part_c(html)
    blocks = ("C1 Terms and counting rules", "C2 Mismatch classes", "C4 Methods",
              "C5 Limits and settings", "C6 Other limitations",
              "C7 Required statements")  # fmt: skip
    for block in blocks:
        assert block + "</h3>" in c
    assert '<p class="toc">C1 Terms and counting rules' in c
    for gone in ("<h3>Rules applied</h3>", "<h3>Limitations</h3>", "What the search cannot find."):
        assert gone not in c
    # both required statements, word for word
    assert "In silico analysis does not replace experimental validation." in c
    assert "The laboratory is responsible for verifying this software within its own" in c


def test_the_text_corrections_of_the_review(tmp_path):
    c = _part_c(render_report(run_report_result(tmp_path), load_config()))
    # 5.1: a single MGB mismatch is indeterminate only outside the 3'-most 7 nt
    assert "a single mismatch in an MGB probe outside its 3′-most 7 nt" in c
    # 5.2: a gap is not detectable, its outcome at risk
    assert "A gap (R5): not detectable (outcome at risk)" in c
    # 5.3: the rules without a published basis say so
    assert c.count("expert judgement") >= 3 and "no published rule" in c
    # 5.4 and 5.5
    assert "(read from the figure)" in c and "≥3 + ≥2, or ≥4 + ≥1" in c
    assert "3 + &ge;2 or 4 + 1" not in c
    # 5.6: the classes grade MGB probes; the Tm and structures do not model modifications
    assert "Modified probes (MGB, LNA, ZEN and similar) are not modelled." not in c
    assert "The mismatch classes do grade MGB probes (C2, R9)." in c
    # 5.7: no cross-reference to nowhere
    for dead in ("under 'search'", "The inputs hash above", "see Rationale below"):
        assert dead not in html_of(tmp_path)
    assert "The inputs hash (Part A)" in c


def html_of(tmp_path):
    return render_report(run_report_result(tmp_path), load_config())


def test_an_empty_setting_reads_none_and_a_changed_limit_is_tagged():
    assert _plain({}) == "none" and _plain([]) == "none"
    groups = _by_group(
        [("Inclusivity", "inclusivity.status_axis", "release"),
         ("Off-target sites", "specificity.primer_site", "critical ...")],
        ["inclusivity.status_axis", "specificity.primer_site.critical.max_mismatches"],
    )  # fmt: skip
    assert groups == [
        ("Inclusivity", [("status_axis", "release", True)]),
        ("Off-target sites", [("primer_site", "critical ...", True)]),
    ]


def test_the_blast_row_parts_what_ncbi_received_from_the_tools_own_settings():
    sent, tool = blast_split({
        "search": {"program": "blastn", "database": "core_nt", "word_size": 7, "expect": 1000.0,
                   "hitlist_size": 5000, "max_taxids_per_search": 20, "background_taxids": [9606]},
        "relevance": {"min_identical_bases": 14}, "blast_versions": ["BLASTN 2.17.0+"],
    })  # fmt: skip
    assert sent == [("program", "blastn"), ("word_size", "7"), ("expect", "1000.0"),
                    ("hitlist_size", "5000")]  # fmt: skip
    assert tool == [("max_taxids_per_search", "20"), ("background_taxids", "9606"),
                    ("relevance", "min_identical_bases 14")]  # fmt: skip


def test_the_variant_search_s_own_blast_is_in_the_methods_when_it_ran(tmp_path):
    result = run_report_result(tmp_path)
    c = _part_c(render_report(result, load_config()))
    assert "Variant search</th>" not in c  # the fixture reads genome assemblies
    config = {**result.config, "variants": {**result.config["variants"],
              "source": "blast_partitioned", "direct_scan_max_length": 50000,
              "blast_records_per_search": 100}}  # fmt: skip
    c = _part_c(render_report(result.model_copy(update={"config": config}), load_config()))
    assert "Variant search</th>" in c
    assert "word_size 11 · expect 10 · hitlist_size at least 500" in c and "50,000 bases" in c


def test_search_limits_are_rows_and_an_unknown_old_text_is_kept(tmp_path):
    result = run_report_result(tmp_path)
    spec = result.specificity
    if spec is None:
        return
    old = "A limitation of an older version, worded differently."
    spec = spec.model_copy(update={"limitations": [*LIMITATIONS, old]})
    c = _part_c(render_report(result.model_copy(update={"specificity": spec}), load_config()))
    assert "C3 What the search could and could not find</h3>" in c
    for label in ("Word size", "E-value cut-off", "Partial hits", "Merged records",
                  "One primer, both strands", "Tiers", "Database"):  # fmt: skip
        assert re.search(rf'<th scope="row">{label}', c), label
    assert "Further limitation</th><td>" + old in c


def test_text_and_tables_use_the_page_width_on_screen(tmp_path):
    # user, 2026-11-27: "All text fields/tables should be page wide"
    html = render_report(run_report_result(tmp_path), load_config())
    css = html[html.index("<style>") : html.index("@media print")]
    assert "max-width: 46rem" not in css and "margin: .5rem 0 1rem; max-width" not in css
    assert "max-width: 52rem" not in css and "max-width: 600px" not in css
    assert ".year-panels svg.fig.years { width: 100%; height: auto; }" in css


def test_a_long_count_line_beside_a_year_bar_is_not_cut_off():
    from qpcr_assay_check.report import charts

    row = charts.YearRow("2019", charts.Counts(detectable=11_869, at_risk=88, likely_failure=1,
                                               undetermined=2))  # fmt: skip
    svg = charts.year_bars([row], width=600)
    width = float(re.search(r'viewBox="0 0 ([\d.]+)', svg).group(1))
    text = re.search(r'<text x="([\d.]+)"[^>]*>(11,9[^<]*)</text>', svg)
    assert width >= float(text.group(1)) + 6.0 * len(text.group(2))
