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


def test_each_search_of_a_tier_shows_its_own_floor():
    # tiers review 2026-11-20, F6: a 3-taxon tail search set the whole tier's floor unseen
    s = load_config().search
    big = _record("exclusivity", 8e8).model_copy(update={"taxids": list(range(1, 21))})
    tail = _record("exclusivity", 8e11).model_copy(update={"taxids": [31, 32, 33]})
    out = floors([big, tail], {"forward": "GTTGAAACACCGCCCGG"}, ["exclusivity"], s)
    assert out[0].min_score == 15 and out[0].per_search == [(list(range(1, 21)), 10),
                                                            ([31, 32, 33], 15)]  # fmt: skip
    msg = floor_findings(out, s.expect)[0].message
    assert "least sensitive search" in msg
    assert "search 1 (20 taxa: 1, 2, 3, 4, 5 +15 more): score >= 10" in msg
    assert "search 2 (3 taxa: 31, 32, 33): score >= 15" in msg
    one = floors([big], {"forward": "GTTGAAACACCGCCCGG"}, ["exclusivity"], s)
    assert "per search" not in floor_findings(one, s.expect)[0].message


def _floor(tier, label, length, score, mm, **kw):
    from qpcr_assay_check.specificity.models import ScoreFloor

    return ScoreFloor(tier=tier, query=label, length=length, min_score=score,
                      max_mismatches_reported=mm, **kw)  # fmt: skip


def test_the_probe_bound_needs_every_condition():
    # tiers review 2026-11-20, F3: "not detected" without a re-aligned probe holds when every
    # probe site that could bind would have been reported in the tier
    from qpcr_assay_check.specificity.reach import probe_bound

    p25 = {"probe": ("A" * 25, False)}
    ok = [_floor("nn", "probe", 25, 12, 2)]
    assert probe_bound("nn", p25, ok, set(), 14, False) == (True, "")
    assert probe_bound("nn", p25, ok, set(), 14, True)[0] is False  # a gapped site can bind
    assert "not always reported" in probe_bound("nn", p25, [_floor("nn", "probe", 25, 18, 1)],
                                                set(), 14, False)[1]  # fmt: skip
    assert "cut" in probe_bound("nn", p25, ok, {("nn", "probe")}, 14, False)[1]
    full = [_floor("nn", "probe", 25, 12, 2, list_full=True)]
    assert "cut" in probe_bound("nn", p25, full, set(), 14, False)[1]
    assert "no score floor" in probe_bound("other", p25, ok, set(), 14, False)[1]
    # relevance filter: 21 nt with 2 mismatches can score 13 < 14 identical bases
    p21 = {"probe": ("A" * 21, False)}
    assert "too short" in probe_bound("nn", p21, [_floor("nn", "probe", 21, 10, 2)], set(), 14,
                                      False)[1]  # fmt: skip
    # an MGB probe binds with at most one mismatch: 1 always reported suffices, 18 nt is enough
    mgb = {"probe": ("A" * 18, True)}
    assert probe_bound("nn", mgb, [_floor("nn", "probe", 18, 12, 1)], set(), 14, False)[0]


def test_a_bounded_tier_reads_not_detected_instead_of_incomplete():
    from qpcr_assay_check.specificity.assess import scan_findings
    from qpcr_assay_check.specificity.models import PartnerScan

    scan = PartnerScan(primer_sites=0, windows=0, products_not_scanned=500,
                       products_not_scanned_by_tier={"near_neighbours": 500})  # fmt: skip
    (_, f) = scan_findings(scan, 1000, lambda tier: (True, ""), 1000)
    assert f.severity == "INFO" and "Not detected (proven)" in f.message
    (_, g) = scan_findings(scan, 1000, lambda tier: (False, "why not"), 1000)
    assert g.severity == "INCOMPLETE" and "this cannot be ruled out: why not." in g.message
    # the sign-off's short wording: tier and gap, without the explanation (user, 2026-11-20)
    assert g.tier == "near_neighbours"
    assert g.short == (
        "probe not checked in 500 amplicons (probe_scan_max_products); a detectable amplicon "
        "cannot be ruled out"
    )
    scan = PartnerScan(primer_sites=1483, windows=1000, not_scanned=483)
    (_, p) = scan_findings(scan, 1000, lambda tier: (False, ""), 1000)
    assert p.short == (
        "483 off-target primer sites not checked for the opposite primer binding nearby "
        "(partner_scan_max_windows); an amplicon formed there could be missing"
    )
    assert not p.tier and "partner" not in p.message.replace("partner_scan", "")
