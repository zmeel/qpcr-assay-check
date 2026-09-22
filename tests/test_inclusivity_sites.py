"""Full-length assessment of target-tier candidates for inclusivity: always re-aligned."""

from __future__ import annotations

import itertools

from qpcr_assay_check.align import realign
from qpcr_assay_check.config import load_config
from qpcr_assay_check.inclusivity.sites import assess_candidates
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.search.orchestrate import run_search
from qpcr_assay_check.search.planner import plan_searches
from qpcr_assay_check.specificity.sites import make_candidate

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .world import World, WorldFake, make_runner, mutate

TARGET = 2697049
REF = "NC_045512.2"
OTHER = "OT000002.1"


def target_world() -> World:
    w = World()
    seq = "T" * 50 + F + "T" * 30 + P + "T" * 30 + iupac.reverse_complement(R) + "T" * 50
    w.genome(REF, TARGET, "SARS-CoV-2", seq)
    w.hit(TARGET, "forward", F, REF, 51, "+")

    # a second target-taxon accession with a real, BLAST-realistic 2-mismatch partial hit
    seq2 = "A" * 50 + mutate(F, [10, 16, 17]) + "A" * 50
    w.genome(OTHER, TARGET, "SARS-CoV-2", seq2)
    w.hit(TARGET, "forward", F, OTHER, 51, "+", trim3=5)
    return w


def candidates_for(tmp_path, world):
    cfg = load_config()
    assay = make_assay(target={"taxid": TARGET, "accession": REF})
    fake = WorldFake(world)
    runner, store, fetcher = make_runner(cfg, tmp_path, fake)
    plan = plan_searches(assay, cfg)
    (target_ps,) = [ps for ps in plan.searches if ps.tier == "target"]
    parsed: dict = {}
    run_search(
        plan, cfg, runner, store, tmp_path / "s", inputs_hash="h", keep=parsed,
        keep_tiers={"target"},
    )  # fmt: skip
    q = parsed[target_ps.key].queries["forward"]
    oligo = plan.queries["forward"]
    cands = [
        make_candidate("target", "forward", oligo, hit, hsp) for hit in q.hits for hsp in hit.hsps
    ]
    return cfg, cands, fetcher


def test_a_full_length_hit_needs_no_fetch(tmp_path):
    cfg, cands, fetcher = candidates_for(tmp_path, target_world())
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    ref_only = [c for c in cands if c.accession == REF]
    sites = assess_candidates(
        ref_only, cfg.specificity.primer_site, fetcher, scoring,
        cfg.specificity.window_padding_nt, itertools.count(1),
    )  # fmt: skip
    (full,) = sites
    assert full.source == "blast_full" and full.n_mismatch == 0
    assert fetcher.n_network == 0


def test_a_partial_hit_is_always_fetched_and_exactly_re_aligned_not_worst_cased(tmp_path):
    cfg, cands, fetcher = candidates_for(tmp_path, target_world())
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    sites = assess_candidates(
        cands, cfg.specificity.primer_site, fetcher, scoring,
        cfg.specificity.window_padding_nt, itertools.count(1),
    )  # fmt: skip
    partial = next(s for s in sites if s.accession == OTHER)
    # exact re-alignment, not the risk-conservative worst-case estimate off-target sites use
    assert partial.source == "realigned"
    assert partial.n_mismatch == 3 and partial.defect_positions == [10, 16, 17]
    assert fetcher.n_network == 1


def test_a_failed_fetch_falls_back_to_worst_case_and_is_flagged(tmp_path):
    world = target_world()
    world.missing.add(OTHER)
    cfg, cands, fetcher = candidates_for(tmp_path, world)
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    sites = assess_candidates(
        cands, cfg.specificity.primer_site, fetcher, scoring,
        cfg.specificity.window_padding_nt, itertools.count(1),
    )  # fmt: skip
    partial = next(s for s in sites if s.accession == OTHER)
    assert partial.source == "blast_partial_worst_case"
    assert fetcher.n_failed == 1
