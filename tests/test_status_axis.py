"""The status by collection year (inclusivity.status_axis) and distinct site patterns (theory
reviews 2026-10-01, user 2026-10-02)."""

from qpcr_assay_check.config import load_config
from qpcr_assay_check.inclusivity.models import FragmentYear, fragment_window, status_years
from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.report.summary import summary_rows
from qpcr_assay_check.variants.exhaustive import fragment_verdict
from qpcr_assay_check.verdict import Verdict

from .fake_datasets import FakeAssembly, FakeDatasets
from .test_collection_dates import _dated
from .test_variants_exhaustive import NOW, _empty_specificity, genome, run, setup


def _run(tmp_path, axis: str, items=None):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(items or _dated()))
    cfg.inclusivity.min_genomes_for_verdict = 1
    cfg.inclusivity.status_axis = axis
    return cfg, assay, run(tmp_path, cfg, client, assay)


def test_the_default_axis_is_the_release_year():
    assert load_config().inclusivity.status_axis == "release"


def test_the_status_counts_collection_years_when_asked(tmp_path):
    _, _, rel = _run(tmp_path / "r", "release")
    cfg, _, col = _run(tmp_path / "c", "collection")
    assert rel.inclusivity.status_axis == "release" and col.inclusivity.status_axis == "collection"
    # by release year: GCF_1, GCF_2 and the variant GCA_3 (a likely failure), 2024-2026
    assert rel.inclusivity.verdict is Verdict.FAIL
    assert rel.inclusivity.rationale[0].startswith("Whole fragment, genomes released 2024-2026")
    # by collection year only GCF_1 (2024) is placed; GCF_2 was collected in 2012, GCA_3 has
    # 'missing', GCA_5 (cut) no BioSample: left out, and said so
    lines = col.inclusivity.rationale
    assert col.inclusivity.verdict is Verdict.PASS
    assert lines[0].startswith("Whole fragment, genomes collected 2024-2024: 100.0% detectable")
    assert any(x.startswith("By release year (information only; the status uses the "
                            "collection year): 66.7% detectable of 3") for x in lines)  # fmt: skip
    apart = next(x for x in lines if x.startswith("Left out of the status by collection year"))
    assert "2 of 4 assemblies released 2024-2026 with the region (50.0%)" in apart
    assert not any(x.startswith("By collection date (information only") for x in lines)
    # the release-year table is still there, unchanged
    assert rel.inclusivity.fragment_years == col.inclusivity.fragment_years
    w = fragment_window(status_years(col.inclusivity), cfg.inclusivity.verdict_window_years)
    assert (w.first, w.last, w.n) == (2024, 2024, 1)


def test_a_collection_year_below_the_limit_names_the_collection_year():
    rules = load_config().inclusivity

    def year(y, det, fail=0):
        return FragmentYear(year=y, with_region=det + fail, detectable=det, likely_failure=fail)

    drop = [year(y, 400) for y in range(2023, 2026)] + [year(2026, 20, fail=30)]
    verdict, lines = fragment_verdict(drop, rules, "collection")
    assert verdict is Verdict.WARN and lines[0].startswith("Whole fragment, genomes collected")
    assert any(x.startswith("Collection year 2026 on its own") for x in lines)
    assert "a single collection year below the limit" in lines[0]


def test_identical_sites_are_one_pattern(tmp_path):
    _, _, res = _run(tmp_path, "release")
    d = res.inclusivity.distinct
    # GCF_1 and GCF_2 (other strand) carry the reference sites: one pattern; GCA_3 the variant
    assert (d.genomes, d.patterns, d.detectable, d.likely_failure) == (3, 2, 1, 1)
    assert (d.largest, d.likely_failure_genomes, d.axis) == (2, 1, "release")
    line = next(x for x in res.inclusivity.rationale if x.startswith("Distinct site patterns"))
    assert "carry 2 different combinations" in line
    assert "50.0% of the patterns are detectable" in line
    assert "against 66.7% of the genomes" in line
    # the status still counts genomes
    assert "66.7% detectable" in res.inclusivity.rationale[0]


def test_many_copies_of_one_lineage_weigh_once(tmp_path):
    items = _dated() + [
        FakeAssembly(f"GCF_00000010{i}.1", "2025-06-01", genome(10 + i)) for i in range(5)
    ]
    _, _, res = _run(tmp_path, "release", items)
    d = res.inclusivity.distinct
    assert (d.genomes, d.patterns, d.largest) == (8, 2, 7)


def test_report_and_summary_follow_the_axis(tmp_path):
    for axis in ("release", "collection"):
        cfg, assay, res = _run(tmp_path / axis, axis)
        result = evaluate(
            assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
            release_dates=res.release_dates, inclusivity=res.inclusivity,
            specificity=_empty_specificity(),
        )  # fmt: skip
        html = render_report(result, cfg)
        (row,) = [x for x in summary_rows(result, cfg, []) if x.check.startswith("Target detect")]
        assert "distinct site patterns, information" in row.result
        assert "<strong>Distinct site patterns</strong>" in html
        if axis == "collection":
            assert "1 genomes collected 2024–2024" in row.scope
            assert "by collection year</strong> (the status uses this table)" in html
            assert "complete collection years" in html
        else:
            assert "genomes released 2024–2026" in row.scope
            assert "by collection year</strong> (information only)" in html
