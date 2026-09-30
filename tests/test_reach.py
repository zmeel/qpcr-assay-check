"""Score floor of a BLAST search: checked against the E-value sweep of the smoke test."""

import json

import pytest

from qpcr_assay_check.config import load_config
from qpcr_assay_check.ncbi.parser import SearchStat, parse_blast_json
from qpcr_assay_check.search.orchestrate import SearchRecord
from qpcr_assay_check.specificity.reach import (
    always_reported,
    floor_findings,
    floors,
    score_floor,
)

# Real statistics (smoke test, 2026-09-30, RID BTN2BA3N016): NG-F (17 nt) against txid487.
STAT = {
    "db_num": 6618,
    "db_len": 406052228,
    "hsp_len": 15,
    "eff_space": 811905916,
    "kappa": 0.710602795216363,
    "lambda": 1.37406312246009,
    "entropy": 1.30724660390929,
}


@pytest.mark.parametrize(("expect", "lowest_reported"), [(1000, 10), (10000, 8), (100000, 7)])
def test_the_floor_matches_the_lowest_score_ncbi_reported(expect, lowest_reported):
    """The smoke test's sweep: lowest raw scores NCBI reported were 10, 8 and 7."""
    f = score_floor(STAT["eff_space"], STAT["kappa"], STAT["lambda"], expect)
    assert f == lowest_reported


def test_a_larger_search_space_raises_the_floor():
    small = score_floor(8e8, STAT["kappa"], STAT["lambda"], 1000)
    large = score_floor(8e11, STAT["kappa"], STAT["lambda"], 1000)
    assert large - small == 5  # ln(1000) / lambda = 5.03 -> 5 points


def test_mismatches_always_reported():
    # 17 nt, floor 10: one mismatch scores 13 and leaves a run of 8 >= 7; two score 9
    assert always_reported(17, 10, 1, -3, 7) == 1
    # floor 8: two mismatches score 9, but may leave no run of 7 identical bases
    assert always_reported(17, 8, 1, -3, 7) == 1
    # 25 nt, floor 10: three mismatches score 13 and leave a run of ceil(22 / 4) = 6 < 7
    assert always_reported(25, 10, 1, -3, 7) == 2
    assert always_reported(10, 11, 1, -3, 7) == -1


def test_the_parser_reads_the_statistics():
    doc = {
        "BlastOutput2": [
            {
                "report": {
                    "results": {
                        "search": {"query_id": "Q_1", "query_title": "forward", "stat": STAT}
                    }
                }
            }
        ]
    }
    q = parse_blast_json(json.dumps(doc), ["forward"]).queries["forward"]
    assert q.stat == SearchStat(
        eff_space=STAT["eff_space"], kappa=STAT["kappa"], lambda_=STAT["lambda"]
    )
    del doc["BlastOutput2"][0]["report"]["results"]["search"]["stat"]
    assert parse_blast_json(json.dumps(doc), ["forward"]).queries["forward"].stat is None


def _record(tier, eff_space, with_stat=True):
    st = SearchStat(eff_space=eff_space, kappa=STAT["kappa"], lambda_=STAT["lambda"])
    return SearchRecord(
        tier=tier, label=tier, taxids=[], entrez_query=None, key=f"{tier}{eff_space}", rid=None,
        state="done", blast_version=None, database=None, n_hits={"forward": 3}, saturation=[],
        restriction=None, stats={"forward": st} if with_stat else {},
    )  # fmt: skip


def test_the_least_sensitive_search_of_a_tier_decides():
    s = load_config().search
    recs = [_record("background", 8e8), _record("background", 8e11), _record("exclusivity", 8e8)]
    out = floors(recs, {"forward": "GTTGAAACACCGCCCGG"}, ["exclusivity", "background"], s)
    assert [(e.tier, e.min_score, e.max_mismatches_reported) for e in out] == [
        ("exclusivity", 10, 1),
        ("background", 15, 0),
    ]
    msgs = [f.message for f in floor_findings(out, s.expect)]
    assert "forward (17 nt): score >= 15, sites with up to 0 mismatch(es)" in msgs[1]


def test_searches_without_statistics_are_said_so():
    s = load_config().search
    out = floors([_record("background", 8e8, with_stat=False)], {"forward": "ACGT" * 5},
                 ["background"], s)  # fmt: skip
    assert out[0].min_score is None and out[0].searches_without_statistics == 1
    assert "not known" in floor_findings(out, s.expect)[0].message
