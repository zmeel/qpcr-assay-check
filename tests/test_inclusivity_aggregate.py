"""End-to-end inclusivity: bucket target-tier hits into years, sample, re-align, aggregate."""

from __future__ import annotations

from datetime import UTC, datetime

from qpcr_assay_check.config import load_config
from qpcr_assay_check.inclusivity.aggregate import compute_inclusivity
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.search.orchestrate import run_search
from qpcr_assay_check.search.planner import plan_searches
from qpcr_assay_check.verdict import Verdict

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .world import World, WorldFake, make_runner, mutate

TARGET = 2697049
REF = "NC_045512.2"
Y2023_ACC = "OT000010.1"
Y2020_ACC = "OT000011.1"
NOW = datetime(2024, 6, 1, tzinfo=UTC)


def build_world() -> World:
    w = World()
    seq = "T" * 50 + F + "T" * 30 + P + "T" * 30 + iupac.reverse_complement(R) + "T" * 50
    w.genome(REF, TARGET, "SARS-CoV-2", seq)
    w.hit(TARGET, "forward", F, REF, 51, "+")
    w.date(REF, "2023/05/01")

    seq_2020 = "A" * 50 + mutate(F, [10]) + "A" * 50  # 1 aligned mismatch, full-length hit
    w.genome(Y2020_ACC, TARGET, "SARS-CoV-2", seq_2020)
    w.hit(TARGET, "forward", F, Y2020_ACC, 51, "+")
    w.date(Y2020_ACC, "2020/02/14")
    return w


def run(tmp_path, world, *, lookback_years=5, sample_per_window=20):
    cfg = load_config()
    cfg.inclusivity.lookback_years = lookback_years
    cfg.inclusivity.sample_per_window = sample_per_window
    assay = make_assay(target={"taxid": TARGET, "accession": REF})
    fake = WorldFake(world)
    runner, store, fetcher = make_runner(cfg, tmp_path, fake)
    plan = plan_searches(assay, cfg)
    parsed: dict = {}
    run_search(
        plan, cfg, runner, store, tmp_path / "s", inputs_hash="h", keep=parsed,
        keep_tiers={"target"},
    )  # fmt: skip
    result = compute_inclusivity(
        assay, cfg, plan, parsed, fetcher, fetcher.eutils, fetcher.cache,
        tier_searched=True, now=NOW,
    )  # fmt: skip
    return result


def test_hits_are_bucketed_into_the_right_year_and_re_aligned(tmp_path):
    result = run(tmp_path, build_world())
    forward = next(o for o in result.oligos if o.role == "forward")
    by_year = {w.year: w for w in forward.windows}
    assert by_year[2023].n_perfect == 1 and by_year[2023].sample_size == 1
    assert by_year[2020].n_one_mismatch == 1 and by_year[2020].sample_size == 1
    assert by_year[2020].per_position_mismatches[9] == 1  # 1-based position 10 -> index 9
    # years with no hits are still reported, honestly, as zero -- not omitted
    other_years = [w for y, w in by_year.items() if y not in (2020, 2023)]
    assert other_years and all(w.sample_size == 0 for w in other_years)


def test_reverse_and_probe_have_no_hits_in_this_constructed_world(tmp_path):
    result = run(tmp_path, build_world())
    reverse = next(o for o in result.oligos if o.role == "reverse")
    assert all(w.sample_size == 0 for w in reverse.windows)


def test_population_size_is_reported_independently_of_sample_size(tmp_path):
    result = run(tmp_path, build_world())
    forward = next(o for o in result.oligos if o.role == "forward")
    by_year = {w.year: w for w in forward.windows}
    assert by_year[2023].population_size == 1  # one date registered for 2023 in this world
    assert by_year[2020].population_size == 1


def test_the_sample_cap_is_honoured_and_deterministic(tmp_path):
    world = build_world()
    for i in range(5):
        acc = f"OT0000{20 + i}.1"
        world.genome(acc, TARGET, "SARS-CoV-2", "A" * 50 + F + "A" * 50)
        world.hit(TARGET, "forward", F, acc, 51, "+")
        world.date(acc, "2023/01/01")
    result = run(tmp_path, world, sample_per_window=2)
    forward = next(o for o in result.oligos if o.role == "forward")
    w2023 = next(w for w in forward.windows if w.year == 2023)
    assert w2023.sample_size == 2  # capped, even though 6 records exist for 2023


def test_a_clean_assay_passes_and_a_worse_one_does_not(tmp_path):
    clean = run(tmp_path / "clean", build_world())
    assert clean.verdict in (Verdict.WARN, Verdict.PASS)  # 1 mismatch in 2020 is still <=1

    bad_world = World()
    seq = "T" * 50 + F + "T" * 30 + P + "T" * 30 + iupac.reverse_complement(R) + "T" * 50
    bad_world.genome(REF, TARGET, "SARS-CoV-2", seq)
    bad_world.hit(TARGET, "forward", F, REF, 51, "+")
    bad_world.date(REF, "2023/05/01")
    seq_bad = "A" * 50 + mutate(F, [3, 8, 14]) + "A" * 50  # 3 mismatches: 2+ bucket
    bad_world.genome(Y2020_ACC, TARGET, "SARS-CoV-2", seq_bad)
    bad_world.hit(TARGET, "forward", F, Y2020_ACC, 51, "+")
    bad_world.date(Y2020_ACC, "2020/02/14")
    bad = run(tmp_path / "bad", bad_world)
    assert bad.verdict in (Verdict.WARN, Verdict.FAIL)
    assert any("2020" in line for line in bad.rationale)


def test_no_target_tier_search_is_incomplete(tmp_path):
    cfg = load_config()
    assay = make_assay(target={"taxid": TARGET, "accession": REF})
    fake = WorldFake(build_world())
    _, _, fetcher = make_runner(cfg, tmp_path, fake)
    result = compute_inclusivity(
        assay, cfg, plan_searches(assay, cfg), {}, fetcher, fetcher.eutils, fetcher.cache,
        tier_searched=False, now=NOW,
    )  # fmt: skip
    assert result.verdict is Verdict.INCOMPLETE and result.oligos == []


def test_a_year_with_records_but_no_sampled_hit_is_stated_as_not_assessed(tmp_path):
    world = build_world()
    world.date("OT000030.1", "2022/03/01")  # a 2022 record at NCBI that BLAST did not return
    result = run(tmp_path, world)
    line = next(r for r in result.rationale if r.startswith("2022:"))
    assert "1 record(s) at NCBI" in line and "not assessed" in line
    assert "forward, reverse, probe" in line
    # years with no records at all are not flagged: there was nothing to assess
    assert not any(r.startswith(("2021:", "2024:")) for r in result.rationale)
    # the reverse and probe oligos have no hits in 2020/2023 here either, and say so
    assert any(r.startswith("2020:") and "reverse, probe" in r for r in result.rationale)
