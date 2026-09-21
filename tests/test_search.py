import json
import re
import time
from datetime import UTC, datetime

import pytest
from typer.testing import CliRunner

from qpcr_assay_check.cli import app
from qpcr_assay_check.ncbi.parser import parse_blast_json
from qpcr_assay_check.search.assess import assess_saturation, summarise_restriction
from qpcr_assay_check.search.planner import (
    build_queries,
    is_offpeak,
    plan_searches,
    split_batches,
)

from .conftest import ROOT_EXAMPLE, make_assay
from .fake_ncbi import FakeNcbi, blast_json, hits_for_payload

runner = CliRunner()


# ---------------------------------------------------------------- planner
def test_default_plan_has_target_and_background_tiers(cfg, n1):
    plan = plan_searches(n1, cfg)
    assert [(s.tier, s.entrez_query) for s in plan.searches] == [
        ("target", "txid2697049[ORGN]"),
        ("background", "txid9606[ORGN]"),
    ]
    assert plan.searches[0].labels == ["forward", "reverse", "probe"]
    assert len({s.key for s in plan.searches}) == 2
    assert any("organism-list tier" in n for n in plan.notes)


def test_near_neighbours_and_exclusions_are_chunked_to_the_taxid_limit(cfg):
    cfg.search.max_taxids_per_search = 2
    a = make_assay(near_neighbour_taxids=[1, 2, 3], exclusion_taxids=[4, 5])
    near = [s for s in plan_searches(a, cfg).searches if s.tier == "near_neighbours"]
    assert [s.taxids for s in near] == [[1, 2], [3, 4], [5]]
    assert near[0].entrez_query == "(txid1[ORGN] OR txid2[ORGN])"
    assert near[2].entrez_query == "txid5[ORGN]" and near[0].n_chunks == 3


def test_missing_target_taxid_skips_the_target_tier_with_a_note(cfg):
    a = make_assay(target={"accession": "NC_045512.2"})
    plan = plan_searches(a, cfg)
    assert [s.tier for s in plan.searches] == ["background"]
    assert any("target tier was skipped" in n for n in plan.notes)


def test_degenerate_oligos_are_sent_as_separate_variants(cfg):
    q = build_queries(make_assay(forward="GACCCCAAAATCAGCGAAAW"), cfg)
    assert list(q) == ["forward_v1", "forward_v2", "reverse", "probe"]
    assert q["forward_v1"] != q["forward_v2"]


def test_large_query_sets_are_split_into_batches_of_at_most_1000_bases():
    q = {f"q{i}": "A" * 24 for i in range(100)}
    batches = split_batches(q)
    assert sum(len(b) for b in batches) == 100 and len(batches) == 3
    assert all(sum(len(s) for s in b.values()) <= 1000 for b in batches)
    assert split_batches({"a": "A" * 1500}) == [{"a": "A" * 1500}]  # oversized query still sent


def test_search_budget_warning(cfg, n1):
    cfg.search.max_searches_warn = 1
    plan = plan_searches(n1, cfg)
    assert any("03:00-11:00" in w for w in plan.warnings)


@pytest.mark.parametrize(
    "when, expected",
    [
        (datetime(2026, 9, 26, 12, 0, tzinfo=UTC), True),  # Saturday
        (datetime(2026, 9, 27, 23, 0, tzinfo=UTC), True),  # Sunday
        (datetime(2026, 9, 21, 15, 0, tzinfo=UTC), False),  # Monday 11:00 Eastern
        (datetime(2026, 9, 22, 2, 30, tzinfo=UTC), True),  # Monday 22:30 Eastern
        (datetime(2026, 9, 22, 8, 0, tzinfo=UTC), True),  # Tuesday 04:00 Eastern
        (datetime(2026, 9, 22, 10, 0, tzinfo=UTC), False),  # Tuesday 06:00 Eastern
    ],
)
def test_offpeak_window_is_us_eastern(when, expected):
    assert is_offpeak(when) is expected


# ---------------------------------------------------------------- assessment
def q_result(identities, label="forward"):
    text = blast_json(
        {
            label: [
                {"acc": f"AB{i:06d}", "identity": v, "taxid": 9606}
                for i, v in enumerate(identities)
            ]
        }
    )
    return parse_blast_json(text, [label]).queries[label]


def test_saturation_needs_a_full_list_whose_tail_is_still_relevant():
    saturated = assess_saturation(q_result([24, 20, 18]), hitlist_size=3, min_relevant=14)
    assert (
        saturated.list_full
        and saturated.saturated
        and "relevant hits may be missing" in saturated.note
    )
    harmless = assess_saturation(q_result([24, 10, 9]), hitlist_size=3, min_relevant=14)
    assert harmless.list_full and not harmless.saturated and "nothing relevant" in harmless.note
    roomy = assess_saturation(q_result([24, 20]), hitlist_size=3, min_relevant=14)
    assert not roomy.list_full and not roomy.saturated
    empty = assess_saturation(q_result([]), hitlist_size=3, min_relevant=14)
    assert empty.weakest_identity is None and not empty.saturated


def test_restriction_summary_counts_taxa_and_flags_missing_taxonomy():
    text = blast_json(
        {"forward": [{"acc": "A1", "taxid": 9606, "sciname": "Homo sapiens"},
                     {"acc": "A2", "taxid": 63221, "sciname": "Homo sapiens neanderthalensis"},
                     {"acc": "A3", "taxid": None, "sciname": None}]}
    )  # fmt: skip
    r = summarise_restriction(list(parse_blast_json(text, ["forward"]).queries.values()), [9606])
    assert (r.n_descriptions, r.n_taxid_in_requested, r.n_taxid_other, r.n_without_taxid) == (
        3,
        1,
        1,
        1,
    )
    assert r.verifiable and r.top_organisms[0] == ("Homo sapiens", 1)
    assert r.fraction_in_requested == pytest.approx(1 / 3)
    none = summarise_restriction(
        list(
            parse_blast_json(blast_json({"forward": [{"acc": "A1"}]}), ["forward"]).queries.values()
        ),
        [1],
    )
    assert not none.verifiable


# ---------------------------------------------------------------- CLI end to end (fake NCBI)
@pytest.fixture
def cli_env(tmp_path, monkeypatch):
    cache = tmp_path / "cache"
    conf = tmp_path / "config.yaml"
    conf.write_text(f"ncbi:\n  cache_dir: {cache}\n")
    monkeypatch.setenv("NCBI_EMAIL", "lab@example.org")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.setattr(time, "sleep", lambda s: None)
    holder = {}

    def install(fake):
        holder["fake"] = fake
        monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
        return fake

    install(FakeNcbi(hits_for_payload))
    return type(
        "E",
        (),
        {"conf": conf, "out": tmp_path / "out", "install": staticmethod(install), "h": holder},
    )


def args(env, *extra):
    return ["search", str(ROOT_EXAMPLE), "--config", str(env.conf), "-o", str(env.out), *extra]


def test_dry_run_shows_the_plan_and_sends_nothing(cli_env, monkeypatch):
    monkeypatch.delenv("NCBI_EMAIL")
    r = runner.invoke(app, args(cli_env, "--dry-run"))
    assert r.exit_code == 0, r.output
    assert "GACCCCAAAATCAGCGAAAT" in r.output and "txid2697049[ORGN]" in r.output
    assert "Dry run: nothing was sent" in r.output
    assert cli_env.h["fake"].calls == []


def test_missing_email_is_a_clear_input_error(cli_env, monkeypatch):
    monkeypatch.delenv("NCBI_EMAIL")
    r = runner.invoke(app, args(cli_env, "--yes"))
    assert r.exit_code == 64 and "NCBI_EMAIL" in r.output
    assert cli_env.h["fake"].calls == []


def test_declining_the_confirmation_sends_nothing(cli_env):
    r = runner.invoke(app, args(cli_env), input="n\n")
    assert r.exit_code == 64 and "Nothing was sent" in r.output
    assert cli_env.h["fake"].n_put == 0


def test_full_search_writes_hits_and_records_and_a_rerun_is_free(cli_env):
    r = runner.invoke(app, args(cli_env, "--yes"))
    assert r.exit_code == 0, r.output
    fake = cli_env.h["fake"]
    assert fake.n_put == 2 and "Done: 2 search(es)" in r.output
    (search_dir,) = list((cli_env.out / "cdc-2019-ncov-n1").glob("search-*"))
    tsv = (search_dir / "hits.tsv").read_text().splitlines()
    assert tsv[0].startswith("tier\tquery\taccession\ttaxid") and len(tsv) == 1 + 2 * 3 * 3
    doc = json.loads((search_dir / "search.json").read_text())
    assert [s["tier"] for s in doc["searches"]] == ["target", "background"]
    assert doc["searches"][0]["rid"] == "RID0001" and doc["parameters"]["blast_versions"]
    assert doc["searches"][0]["entrez_query"] == "txid2697049[ORGN]"
    assert "email" not in json.dumps(doc).lower().replace("entrez", "")  # no identity in the record
    rerun = runner.invoke(app, args(cli_env))  # no --yes needed: everything is cached
    assert rerun.exit_code == 0 and fake.n_put == 2


def test_saturated_hit_list_gives_exit_code_10(cli_env, tmp_path):
    conf = tmp_path / "small.yaml"
    conf.write_text(f"ncbi:\n  cache_dir: {tmp_path / 'c2'}\nsearch:\n  hitlist_size: 3\n")
    r = runner.invoke(
        app, ["search", str(ROOT_EXAMPLE), "-c", str(conf), "-o", str(cli_env.out), "--yes"]
    )
    assert (
        r.exit_code == 10 and "WARNING" in r.output and "relevant hits may be missing" in r.output
    )


def test_ncbi_failure_gives_exit_code_70(cli_env):
    cli_env.install(FakeNcbi(hits_for_payload, put_failures=[400]))
    r = runner.invoke(app, args(cli_env, "--yes"))
    assert r.exit_code == 70 and "NCBI problem" in r.output


def test_interrupted_search_resumes_with_the_same_command(cli_env):
    cli_env.install(FakeNcbi(hits_for_payload, crash_on_first_status=True))
    with pytest.raises(RuntimeError):
        runner.invoke(app, args(cli_env, "--yes"), catch_exceptions=False)
    fake = cli_env.h["fake"]
    assert fake.n_put == 1
    r = runner.invoke(app, args(cli_env, "--yes"))
    assert r.exit_code == 0, r.output
    assert fake.n_put == 2  # first search resumed (no resubmission), second search submitted
    assert re.search(r"Done: 2 search", r.output)


def test_target_tier_saturation_is_informational_not_a_warning(cli_env, tmp_path):
    """Live finding: SARS-CoV-2 (9 million records) always fills the hit list with perfect hits."""
    conf = tmp_path / "small_target.yaml"
    conf.write_text(
        f"ncbi:\n  cache_dir: {tmp_path / 'c3'}\n"
        "search:\n  hitlist_size: 3\n  background_taxids: []\n"
    )
    r = runner.invoke(
        app, ["search", str(ROOT_EXAMPLE), "-c", str(conf), "-o", str(cli_env.out), "--yes"]
    )
    assert r.exit_code == 0, r.output  # only the target tier exists, and it is saturated
    (search_dir,) = list((cli_env.out / "cdc-2019-ncov-n1").glob("search-*"))
    doc = json.loads((search_dir / "search.json").read_text())
    assert doc["warnings"] == []
    assert any("Expected for a well-sequenced target" in n for n in doc["notes"])
    assert doc["searches"][0]["saturation"][0]["saturated"] is True  # still recorded
