"""target.exclude_taxids: taxa inside the target taxon that the assay must not detect.

Taxonomy IDs below are placeholders for the tests (real IDs are only used in the example assay,
where they were checked live).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import InputError
from qpcr_assay_check.ncbi.blast import build_entrez_query
from qpcr_assay_check.pipeline import evaluate
from qpcr_assay_check.report.html import render_report
from qpcr_assay_check.search.planner import plan_searches
from qpcr_assay_check.variants.exhaustive import run_exhaustive
from qpcr_assay_check.variants.partitioned import base_term
from qpcr_assay_check.variants.store import store_path

from .conftest import make_assay

TARGET = {"taxid": 100, "exclude_taxids": [300, 200, 300]}


def test_the_entrez_query_leaves_the_excluded_taxa_out():
    assert build_entrez_query([100]) == "txid100[ORGN]"
    assert build_entrez_query([100], [200, 300]) == (
        "(txid100[ORGN] NOT (txid200[ORGN] OR txid300[ORGN]))"
    )
    assert base_term(100, "25000:32000[SLEN]", [200]) == (
        "(txid100[ORGN] NOT (txid200[ORGN])) AND (25000:32000[SLEN])"
    )


def test_the_target_tier_excludes_them_and_the_near_neighbours_search_them():
    assay = make_assay(target=TARGET)
    assert assay.target.excluded_taxids == [200, 300]  # sorted, unique
    assert assay.target.must_not_detect_taxids == [200, 300]  # exclude_taxids = must_not_detect
    plan = plan_searches(assay, load_config(), exclusivity_taxids=[])
    target = {ps.entrez_query for ps in plan.searches if ps.tier == "target"}
    near = [ps for ps in plan.searches if ps.tier == "near_neighbours"]
    assert target == {"(txid100[ORGN] NOT (txid200[ORGN] OR txid300[ORGN]))"}
    assert near and all(ps.taxids == [200, 300] for ps in near)


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ({"accession": "NC_045512.2", "exclude_taxids": [200]}, "need the target's 'taxid'"),
        ({"taxid": 100, "exclude_taxids": [100]}, "own taxid"),
        ({"taxid": 100, "exclude_taxids": [0]}, "positive"),
    ],
)
def test_invalid_exclusions_are_rejected(target, message):
    with pytest.raises(ValidationError, match=message):
        make_assay(target=target)


def test_the_region_store_is_separate_for_a_different_exclusion(tmp_path):
    a = store_path(tmp_path, 100, "ACGT", 50, "blast_partitioned")
    b = store_path(tmp_path, 100, "ACGT", 50, "blast_partitioned", [200])
    assert a != b and a == store_path(tmp_path, 100, "ACGT", 50, "blast_partitioned", [])


def test_the_datasets_source_refuses_exclusions(tmp_path):
    assay = make_assay(target=TARGET, reference_amplicon="ACGT" * 20)
    with pytest.raises(InputError, match="not supported with variants.source: datasets"):
        run_exhaustive(assay, load_config(), None, tmp_path, lambda a: "")  # type: ignore[arg-type]


def test_the_report_names_the_excluded_taxa():
    assay = make_assay(target=TARGET)
    cfg = load_config()
    html = render_report(evaluate(assay, cfg, qc_only=True), cfg)
    assert "Excluding" in html and "wwwtax.cgi?id=200" in html and "near neighbours" in html


class _FakeTaxonomy:
    """E-utilities stand-in: taxonomy XML with a lineage per taxon (SYNTHETIC IDs)."""

    LINEAGES = {200: [1, 50, 100], 300: [1, 50, 100, 200], 50: [1]}

    def __init__(self):
        self.calls = 0

    def fetch_taxonomy(self, taxids):
        self.calls += 1
        parts = []
        for t in taxids:
            lin = "".join(f"<Taxon><TaxId>{a}</TaxId></Taxon>" for a in self.LINEAGES[t])
            parts.append(f"<Taxon><TaxId>{t}</TaxId><LineageEx>{lin}</LineageEx></Taxon>")
        return "<TaxaSet>" + "".join(parts) + "</TaxaSet>"


def test_excluded_taxa_outside_the_target_are_found(tmp_path):
    from qpcr_assay_check.ncbi.cache import Cache
    from qpcr_assay_check.taxonomy.resolve import outside_target

    fake, cache = _FakeTaxonomy(), Cache(tmp_path / "cache")
    assert outside_target(fake, cache, 100, [200, 300], ttl_days=30) == []
    assert outside_target(fake, cache, 100, [50, 200], ttl_days=30) == [50]  # an ancestor
    assert fake.calls == 2  # 200 came from the cache the second time
    assert outside_target(fake, cache, 100, [50], ttl_days=30) == [50] and fake.calls == 2


def test_the_search_plan_refuses_an_exclusion_outside_the_target(tmp_path, monkeypatch):
    from qpcr_assay_check.search import execute

    monkeypatch.setattr(execute, "outside_target", lambda *a, **k: [50])
    with pytest.raises(InputError, match="must lie inside the target taxon 100.*50"):
        execute._resolve_and_plan(make_assay(target={"taxid": 100, "exclude_taxids": [50]}),
                                  load_config(), None, None, only_tiers=None)  # fmt: skip


ROLES = {"taxid": 100, "taxa": [
    {"taxid": 200, "role": "must_not_detect", "reason": "rhinovirus (synthetic ID)"},
    {"taxid": 400, "role": "out_of_scope", "reason": "animal virus (synthetic ID)"},
]}  # fmt: skip


def test_roles_split_the_searches_must_not_detect_near_out_of_scope_own_tier():
    assay = make_assay(target=ROLES | {"exclude_taxids": [300]})  # short form: must_not_detect
    t = assay.target
    assert t.must_not_detect_taxids == [200, 300] and t.out_of_scope_taxids == [400]
    assert t.exclude_taxids == [] and t.excluded_taxids == [200, 300, 400]
    plan = plan_searches(assay, load_config(), exclusivity_taxids=[])
    by_tier = {ps.tier: ps for ps in plan.searches}
    assert by_tier["near_neighbours"].taxids == [200, 300]
    assert by_tier["out_of_scope"].taxids == [400]
    assert "NOT (txid200[ORGN] OR txid300[ORGN] OR txid400[ORGN])" in (
        by_tier["target"].entrez_query or ""
    )


def test_a_taxon_listed_twice_is_rejected():
    with pytest.raises(ValidationError, match="in both 'exclude_taxids' and 'taxa'"):
        make_assay(target=ROLES | {"exclude_taxids": [200]})
    with pytest.raises(ValidationError, match="listed twice"):
        make_assay(target={"taxid": 100, "taxa": [{"taxid": 200}, {"taxid": 200}]})


def test_a_loaded_assay_validates_again_unchanged():
    """Records store the normalised assay; loading it again must give the same assay."""
    from qpcr_assay_check.models import Assay

    assay = make_assay(target=ROLES | {"exclude_taxids": [300]})
    assert Assay.model_validate_json(assay.model_dump_json()) == assay


def test_out_of_scope_findings_are_information_only():
    from qpcr_assay_check.specificity.findings import build_findings

    from .test_exclusivity import site

    rules = load_config().specificity

    def severities(tier):
        findings = build_findings(
            sites=[site(400, "forward", "critical", tier=tier)], amplicons=[], site_by_id={},
            counts=[], saturated=[(tier, "forward", "")], off_tiers_seen=[tier],
            intended_target={}, target_searched=True, n_primer_only=1, n_fetch_failed=0,
            amplicons_truncated=False, rules=rules,
        )  # fmt: skip
        return {f.severity for f in findings if f.message.startswith(f"Tier '{tier}'")}

    assert severities("out_of_scope") == {"INFO"}  # even a saturated hit list
    assert severities("near_neighbours") == {"INCOMPLETE", "WARN"}  # the same evidence, judged


def test_the_report_lists_the_roles_and_reasons():
    assay = make_assay(target=ROLES)
    cfg = load_config()
    html = render_report(evaluate(assay, cfg, qc_only=True), cfg)
    assert "Must not detect" in html and "rhinovirus (synthetic ID)" in html
    assert "Out of scope" in html and "animal virus (synthetic ID)" in html
