"""Collection dates: parsing, where NCBI gives them, the store's side file and the second axis."""

import json

import pytest

from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.variants.collection import collection_year, from_biosample, from_docsum
from qpcr_assay_check.variants.genomestore import GenomeStore

from .fake_datasets import FakeDatasets
from .test_variants_exhaustive import NOW, _empty_specificity, assemblies, run, setup


@pytest.mark.parametrize(
    ("value", "year"),
    [
        ("2019-05-12", 2019), ("2019-05", 2019), ("2019", 2019), ("10-Mar-2019", 2019),
        ("Mar-2019", 2019), ("2018/2019", 2018), ("2018-11-30/2019-01-02", 2018),
        ("missing", None), ("not applicable", None), ("not collected", None), ("", None),
        (None, None), ("12345", None),
    ],
)  # fmt: skip
def test_the_collection_year_is_the_first_year_in_the_value(value, year):
    assert collection_year(value) == year


def test_a_year_after_the_latest_is_not_a_collection_year():
    assert collection_year("2031", latest=2026) is None


def test_the_biosample_field_is_read_and_its_attribute_is_the_fallback():
    # shapes as the live Datasets report of 2026-09-30 (GCF_022869645.1: "missing")
    assert from_biosample({"assembly_info": {"biosample": {"collection_date": "missing"}}}) == (
        "missing"
    )
    attr = {"attributes": [{"name": "collection_date", "value": "2011-07"}]}
    assert from_biosample({"assembly_info": {"biosample": attr}}) == "2011-07"
    assert from_biosample({"assembly_info": {}}) == ""


def test_the_docsum_qualifiers_are_paired_by_position():
    # the live ESummary of LC951483.1 (2026-09-30): collected 2021, published 2026
    doc = {
        "subtype": "isolate|host|country|isolation_source|collection_date",
        "subname": "EVE/CEP-8/JPN/2021/E2|Bos taurus|Japan|feces|2021-12-03",
    }
    assert from_docsum(doc) == "2021-12-03"
    assert from_docsum({"subtype": "strain|country", "subname": "X|Y"}) == ""
    shifted = {"subtype": "isolate|collection_date", "subname": "a|b|2020"}
    assert from_docsum(shifted) == ""  # a '|' inside a value: no guess


def test_the_store_keeps_dates_beside_it_and_writes_only_changes(tmp_path):
    key = {"schema": 0, "taxon": "1"}
    store = GenomeStore(tmp_path / "g.jsonl", key)
    store.note_dates({"A.1": "2020", "B.1": ""})
    stamp = store.dates_path.stat().st_mtime_ns
    store.note_dates({"A.1": "2020"})
    assert store.dates_path.stat().st_mtime_ns == stamp
    again = GenomeStore(tmp_path / "g.jsonl", key)
    assert again.dates == {"A.1": "2020", "B.1": ""}
    assert json.loads(store.dates_path.read_text()) == {"A.1": "2020", "B.1": ""}


def _dated():
    out = assemblies()
    dates = ["2024-01", "2012-06-01", "missing", "2026", None]  # the last: no biosample
    for a, d in zip(out, dates, strict=True):
        a.collection_date = d
    return out


def test_genomes_are_counted_by_collection_year_with_undated_ones_apart(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(_dated()))
    res = run(tmp_path, cfg, client, assay)
    ca = res.inclusivity.collection
    by_year = {r.year: r.with_region for r in ca.years}
    # with the region: GCF_1 (collected 2024), GCF_2 (2012, released 2025), GCA_3 ('missing')
    assert by_year == {2024: 1}
    # undated: GCA_3 ('missing') and GCA_5, cut by a contig end and counted as undetermined
    # (user, 2026-10-01), with no BioSample
    assert (ca.earlier.with_region, ca.undated.with_region, ca.not_read.with_region) == (1, 2, 0)
    assert ca.undated.unjudged == 1
    assert ca.earlier.label.startswith("before ")
    line = next(x for x in res.inclusivity.rationale if x.startswith("By collection date"))
    assert "1 were collected before" in line and "2 carry no usable collection date" in line
    # the verdict and the per-release-year table are unchanged by the second axis
    assert {f.year for f in res.inclusivity.fragment_years} >= {2024, 2025, 2026}


def test_genomes_stored_before_dates_were_read_get_them_on_the_next_listing(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(_dated()))
    run(tmp_path, cfg, client, assay)
    (store_file,) = (tmp_path / "cache" / "genomes").glob("*.dates.json")
    store_file.unlink()  # as a store made before this version
    n_downloads = len(fake.downloads)
    res = run(tmp_path, cfg, client, assay)
    assert len(fake.downloads) == n_downloads  # nothing downloaded again
    assert res.inclusivity.collection.not_read.with_region == 0
    assert json.loads(store_file.read_text())["GCF_000000002.1"] == "2012-06-01"


def test_the_report_shows_the_collection_axis(tmp_path):
    cfg, fake, client, assay = setup(tmp_path, fake=FakeDatasets(_dated()))
    res = run(tmp_path, cfg, client, assay)
    result = evaluate(
        assay, cfg, now=NOW, target_sites=res.sites, variant_coverage=res.coverage,
        release_dates=res.release_dates, inclusivity=res.inclusivity,
        specificity=_empty_specificity(),
    )  # fmt: skip
    html = render_report(result, cfg)
    assert "by collection year</strong> (information only)" in html
    assert "no usable date" in html and "BioSample collection_date" in html
