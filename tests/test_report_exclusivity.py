"""Exclusivity and taxonomy-breakdown sections of report.html and results.xlsx."""

from __future__ import annotations

from datetime import UTC, datetime

from openpyxl import load_workbook

from qpcr_assay_check.config import load_config
from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.report.xlsx import write_workbook
from qpcr_assay_check.search.orchestrate import SearchOutcome, SearchRecord
from qpcr_assay_check.specificity.models import SpecificityResult, TierCount
from qpcr_assay_check.taxonomy.plan import OrganismListResolution
from qpcr_assay_check.taxonomy.resolve import Resolution
from qpcr_assay_check.taxonomy.rollup import TaxonCount
from qpcr_assay_check.verdict import Verdict

from .test_exclusivity import CT, NG, amplicon, site

NOW = datetime(2026, 9, 20, 12, 0, 0, tzinfo=UTC)


def _specificity_with_exclusivity() -> SpecificityResult:
    sites = [site(CT, "forward", "critical", site_id="S1")]
    amps = [amplicon(CT, "likely_detected")]
    return SpecificityResult(
        verdict=Verdict.FAIL,
        verdict_sites=Verdict.FAIL,
        verdict_amplicons=Verdict.FAIL,
        scope="Off-target tiers assessed: exclusivity.",
        rationale=["Specificity: 1 critical primer site."],
        findings=[],
        counts=[
            TierCount(
                tier="exclusivity", query="forward", blast_hits=1, hsps_relevant=1,
                sites_assessed=1,
            )
        ],  # fmt: skip
        n_sites={"critical": 1, "warning": 0, "minor": 0},
        sites=sites,
        amplicons=amps,
        limitations=["Test limitation."],
        parameters={
            "alignment": {"match": 1, "mismatch": -3, "gap_open": 5, "gap_extend": 2},
            "primer_site": {}, "probe_site": {}, "severity": {},
            "window_padding_nt": 10, "max_amplicon_size": 2000, "min_identical_bases": 14,
            "blast": {"word_size": 7}, "databases": ["core_nt"],
            "blast_versions": ["BLASTN 2.17.0+"],
        },
    )  # fmt: skip


def _resolution() -> OrganismListResolution:
    return OrganismListResolution(
        resolutions=[
            Resolution(name="Chlamydia trachomatis", status="resolved", taxid=CT),
            Resolution(name="Neisseria gonorrhoeae", status="resolved", taxid=NG),
            Resolution(name="Mycoplasma pneumoniae", status="unresolved"),
        ]
    )


def _breakdown() -> list[TaxonCount]:
    return [
        TaxonCount(
            taxid=CT, scientific_name="Chlamydia trachomatis", species="Chlamydia trachomatis",
            genus="Chlamydia", family="Chlamydiaceae", n_sites=1,
        )
    ]  # fmt: skip


def _search_outcome() -> SearchOutcome:
    return SearchOutcome(
        tool={"name": "qpcr-assay-check", "version": "0"},
        generated_at=NOW.isoformat(),
        inputs_hash="x",
        oligos={},
        parameters={},
        searches=[
            SearchRecord(
                tier="exclusivity", label="exclusivity", taxids=[CT, NG], entrez_query=None,
                key="k", rid=None, state="done", blast_version=None, database=None,
                n_hits={}, saturation=[], restriction=None,
            )
        ],
    )  # fmt: skip


def _result(n1):
    cfg = load_config()
    specificity = _specificity_with_exclusivity()
    return evaluate(
        n1, cfg, now=NOW, specificity=specificity, organism_resolution=_resolution(),
        taxonomy_breakdown=_breakdown(), search_outcome=_search_outcome(),
    )  # fmt: skip


def test_the_exclusivity_table_shows_hit_and_zero_hit_and_unresolved_rows(n1):
    result = _result(n1)
    html = render_report(result, load_config())
    assert "Exclusivity against the clinical organism list" in html
    assert "2 of 3 organism-list name(s) resolved" in html
    assert "Chlamydia trachomatis" in html and "Neisseria gonorrhoeae" in html
    assert "Mycoplasma pneumoniae" in html and "unresolved" in html
    assert "likely_detected" in html


def test_the_taxonomy_breakdown_table_appears(n1):
    html = render_report(_result(n1), load_config())
    assert "Taxonomic breakdown of off-target sites" in html
    assert "Chlamydiaceae" in html


def test_no_exclusivity_or_breakdown_when_not_computed(n1):
    cfg = load_config()
    html = render_report(evaluate(n1, cfg, qc_only=True, now=NOW), cfg)
    assert "<h2>Exclusivity against the clinical organism list</h2>" not in html
    assert "<h2>Taxonomic breakdown of off-target sites</h2>" not in html


def test_workbook_gets_exclusivity_and_taxonomy_sheets(n1, tmp_path):
    result = _result(n1)
    path = tmp_path / "r.xlsx"
    write_workbook(result, path)
    wb = load_workbook(path)
    assert "Exclusivity" in wb.sheetnames and "Taxonomy breakdown" in wb.sheetnames
    rows = {row[0].value: row for row in wb["Exclusivity"].iter_rows(min_row=2)}
    assert rows["Chlamydia trachomatis"][3].value == 1  # Sites column
    assert rows["Mycoplasma pneumoniae"][1].value == "unresolved"
    tax_rows = list(wb["Taxonomy breakdown"].iter_rows(min_row=2))
    assert tax_rows[0][1].value == "Chlamydia trachomatis"
