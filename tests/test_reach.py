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


@pytest.mark.parametrize("bad", [0, -1, "nan", "inf"])
def test_unusable_statistics_count_as_none_instead_of_failing(bad):
    """Code review 2026-09-30: an empty search space must not abort the assessment."""
    stat = dict(STAT, eff_space=bad)
    doc = {"BlastOutput2": [{"report": {"results": {"search": {
        "query_id": "Q_1", "query_title": "forward", "stat": stat}}}}]}  # fmt: skip
    assert parse_blast_json(json.dumps(doc), ["forward"]).queries["forward"].stat is None


def test_a_full_hit_list_qualifies_always_reported():
    from qpcr_assay_check.search.assess import QuerySaturation

    s = load_config().search
    rec = _record("background", 8e8)
    rec.saturation = [QuerySaturation(label="forward", n_hits=5000, hitlist_size=5000,
                                      list_full=True, weakest_identity=16,
                                      min_relevant_identity=14, saturated=True,
                                      note="")]  # fmt: skip
    out = floors([rec], {"forward": "GTTGAAACACCGCCCGG"}, ["background"], s)
    assert out[0].list_full
    assert "unless cut from the full hit list" in floor_findings(out, s.expect)[0].message


def _multi(stat, hsps, query_len=17):
    hits = [{"num": i + 1, "description": [{"id": f"gi|1|gb|X{i}.1|", "accession": f"X{i}"}],
             "hsps": [dict({"num": 1, "bit_score": 20.0, "identity": 12, "align_len": 12,
                            "query_from": 1, "query_to": 12, "hit_from": 1, "hit_to": 12,
                            "qseq": "A" * 12, "hseq": "A" * 12}, **h)]}
            for i, h in enumerate(hsps)]  # fmt: skip
    doc = {"BlastOutput2": [{"report": {"results": {"search": {
        "query_id": "Q_1", "query_title": "forward", "query_len": query_len, "hits": hits,
        "stat": stat}}}}]}  # fmt: skip
    return parse_blast_json(json.dumps(doc), ["forward"]).queries["forward"].stat


def test_a_zero_search_space_is_derived_from_the_reported_alignments():
    """Live cache check (2026-09-30): multi-query searches report eff_space 0. The sweep's own
    numbers: the largest E-value, 621.94 at score 10, gives the reported 8.12e8."""
    stat = dict(STAT, eff_space=0, hsp_len=0)
    st = _multi(stat, [{"score": 10, "evalue": 621.94}, {"score": 13, "evalue": 9.8}])
    assert st.space_source == "from_hits"
    assert st.eff_space == pytest.approx(STAT["eff_space"], rel=0.01)
    assert score_floor(st.eff_space, st.kappa, st.lambda_, 1000) == 10


def test_without_alignments_the_space_is_bounded_from_above():
    stat = dict(STAT, eff_space=0, hsp_len=0)
    st = _multi(stat, [])
    assert st.space_source == "upper_bound" and st.eff_space == 17 * STAT["db_len"]
    # an upper bound can only raise the floor: the guarantee gets weaker, never stronger
    assert score_floor(st.eff_space, st.kappa, st.lambda_, 1000) >= 10


def test_the_finding_says_how_the_space_was_known():
    s = load_config().search
    rec = _record("background", 8e8)
    rec.stats["forward"] = rec.stats["forward"].model_copy(update={"space_source": "from_hits"})
    out = floors([rec], {"forward": "GTTGAAACACCGCCCGG"}, ["background"], s)
    assert out[0].space_source == "from_hits"
    assert "derived from the reported alignments" in floor_findings(out, s.expect)[0].message
