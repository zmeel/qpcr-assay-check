"""End-to-end assessment (BLAST hits -> full-length sites -> products -> verdict).

Uses the constructed world in tests/world.py: hits follow the real NCBI layout, efetch serves
windows of constructed genomes.
"""

import pytest

from qpcr_assay_check.config import load_config
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.search.orchestrate import run_search
from qpcr_assay_check.search.planner import plan_searches
from qpcr_assay_check.specificity.assess import assess_specificity
from qpcr_assay_check.verdict import Verdict

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import make_assay
from .world import World, WorldFake, filler, make_runner, mutate

NEAR, HUMAN, TARGET = 100, 9606, 2697049
ACC = "OT000001.1"
# layout: F at 201-220, probe at 251-274, reverse primer site at 305-328  => 128 bp product
F_START, P_START, R_START = 201, 251, 305


def offtarget_genome(
    f=(), r=(), p=(), acc=ACC, taxid=NEAR, name="Bacterium exemplum", title="", world=None
):
    w = world or World()
    seq = (
        filler(200, 1)
        + mutate(F, list(f))
        + filler(30, 2)
        + mutate(P, list(p))
        + filler(30, 3)
        + iupac.reverse_complement(mutate(R, list(r)))
        + filler(200, 4)
    )
    assert seq[F_START - 1 : F_START + 19] == mutate(F, list(f))
    w.genome(acc, taxid, name, seq, title)
    return w


def run(world, tmp_path, cfg=None, assay=None, **cfg_changes):
    cfg = cfg or load_config()
    for key, value in cfg_changes.items():
        obj, attr = key.split("__")
        setattr(getattr(cfg, obj), attr, value)
    assay = assay or make_assay(near_neighbour_taxids=[NEAR])
    fake = WorldFake(world)
    runner, store, fetcher = make_runner(cfg, tmp_path, fake)
    plan = plan_searches(assay, cfg)
    parsed: dict = {}
    outcome = run_search(plan, cfg, runner, store, tmp_path / "s", inputs_hash="h", keep=parsed)
    return assess_specificity(assay, cfg, plan, parsed, outcome, fetcher), fetcher, fake


def add_all(w, f=(F_START, "+"), r=(R_START, "-"), p=(P_START, "+"), taxid=NEAR, acc=ACC, **trim):
    w.hit(taxid, "forward", F, acc, f[0], f[1], **trim.get("f", {}))
    w.hit(taxid, "reverse", R, acc, r[0], r[1], **trim.get("r", {}))
    w.hit(taxid, "probe", P, acc, p[0], p[1], **trim.get("p", {}))


def add_target_hits(w):
    """Perfect full-length hits of all three oligos on the intended target."""
    seq = "T" * 50 + F + "T" * 30 + P + "T" * 30 + iupac.reverse_complement(R) + "T" * 50
    w.genome("NC_045512.2", TARGET, "SARS-CoV-2", seq)
    w.hit(TARGET, "forward", F, "NC_045512.2", 51, "+")
    w.hit(TARGET, "probe", P, "NC_045512.2", 101, "+")
    w.hit(TARGET, "reverse", R, "NC_045512.2", 155, "-")


# ------------------------------------------------------------------ the headline scenarios
def test_an_off_target_product_that_primers_and_probe_would_detect_fails(tmp_path):
    w = offtarget_genome(f=[10, 15], r=[5], p=[8])
    add_all(w)
    res, fetcher, _ = run(w, tmp_path)
    assert res.verdict is Verdict.FAIL and res.verdict_amplicons is Verdict.FAIL
    (amp,) = res.amplicons
    assert (amp.classification, amp.length, amp.start, amp.end) == (
        "likely_detected",
        128,
        201,
        328,
    )
    assert amp.roles == "forward/reverse" and amp.tier == "near_neighbours" and amp.probe_site
    assert amp.organism == "Bacterium exemplum" and amp.record_type == "genomic"
    sites = {s.role: s for s in res.sites}
    assert (sites["forward"].n_mismatch, sites["forward"].level) == (2, "critical")
    assert (sites["reverse"].orientation, sites["reverse"].subject_start) == ("-", R_START)
    assert sites["forward"].source == "blast_full" and fetcher.n_network == 0
    # a mismatched duplex is less stable than a perfect one
    assert sites["forward"].tm_c is not None and sites["forward"].delta_tm_c < 0
    msgs = " ".join(res.rationale)
    assert "predicted off-target product" in msgs and "Bacterium exemplum" in msgs


def test_a_partial_hit_is_completed_by_fetching_and_re_aligning_the_window(tmp_path):
    # BLAST stopped 5 bases before the 3' end; a 5-base flank with only one mismatch would let
    # the running match(+1)/mismatch(-3) score end positive (BLAST would have extended over it),
    # so the flank needs two mismatches (16, 17) to stay realistic.
    w = offtarget_genome(f=[10, 16, 17], r=[5], p=[8])
    w.hit(NEAR, "forward", F, ACC, F_START, "+", trim3=5)
    w.hit(NEAR, "reverse", R, ACC, R_START, "-")
    w.hit(NEAR, "probe", P, ACC, P_START, "+")
    res, fetcher, fake = run(w, tmp_path)
    f = next(s for s in res.sites if s.role == "forward")
    assert f.source == "realigned" and f.n_unaligned == 0
    assert (f.n_mismatch, f.defect_positions, f.clean_3prime_nt) == (3, [10, 16, 17], 3)
    assert f.level == "warning" and (f.subject_start, f.subject_end) == (F_START, F_START + 19)
    assert fetcher.n_network == 1 and len(fake.efetch_calls) == 1
    call = fake.efetch_calls[0]
    assert call["db"] == "nuccore" and int(call["seq_start"]) <= F_START <= F_START + 19 <= int(
        call["seq_stop"]
    )
    assert res.verdict is Verdict.FAIL  # warning primer + critical primer + probe -> still detected


def test_a_partial_minus_strand_hit_is_re_aligned_in_the_right_orientation(tmp_path):
    # trim5=7 leaves a 7-base 5' flank: a single mismatch next to the boundary still lets the
    # score end positive when extended outward, so the two bases closest to the boundary (6, 7)
    # both need to mismatch to stay realistic; 23 is a separate mismatch near the 3' end.
    w = offtarget_genome(f=[10], r=[6, 7, 23], p=[8])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    w.hit(NEAR, "reverse", R, ACC, R_START, "-", trim5=7)  # BLAST covered oligo positions 8-24 only
    w.hit(NEAR, "probe", P, ACC, P_START, "+")
    res, _, fake = run(w, tmp_path)
    r = next(s for s in res.sites if s.role == "reverse")
    assert r.source == "realigned" and r.orientation == "-"
    assert (r.subject_start, r.subject_end) == (R_START, R_START + 23)
    assert r.defect_positions == [6, 7, 23] and r.clean_3prime_nt == 1
    assert r.level == "minor"  # a mismatch two bases from the 3' end: too few clean 3' nt


def test_hits_that_cannot_reach_a_relevant_level_are_not_fetched(tmp_path):
    # 5 mismatches in the aligned 20 bases + 4 unaligned bases: at least 6 mismatches (limit 5)
    w = offtarget_genome(r=[2, 5, 8, 11, 14, 21])  # 21 is the first unaligned base
    w.hit(NEAR, "reverse", R, ACC, R_START, "-", trim3=4)
    res, fetcher, fake = run(w, tmp_path)
    assert fake.efetch_calls == [] and fetcher.n_network == 0
    (site,) = [s for s in res.sites if s.role == "reverse"]
    assert site.source == "blast_partial_worst_case" and site.level == "minor"


def test_failed_window_fetch_falls_back_to_worst_case_and_makes_the_result_incomplete(tmp_path):
    w = offtarget_genome(f=[10, 16, 17])  # two flank mismatches: see the realism note above
    w.hit(NEAR, "forward", F, ACC, F_START, "+", trim3=5)
    w.missing.add(ACC)
    res, fetcher, _ = run(w, tmp_path)
    f = next(s for s in res.sites if s.role == "forward")
    assert f.source == "blast_partial_worst_case" and f.n_unaligned == 5
    assert fetcher.n_failed == 1 and res.n_fetch_failed == 1
    assert res.verdict is Verdict.INCOMPLETE  # never a pass on missing evidence
    assert any("could not be fetched" in m for m in res.rationale)


# ------------------------------------------------------------------ other verdict paths
def test_no_relevant_off_target_hit_passes_for_the_searched_tiers_only(tmp_path):
    w = offtarget_genome(r=[1, 3, 5, 7, 9, 11, 13, 15, 17])  # 9 mismatches: relevant but minor
    w.hit(NEAR, "reverse", R, ACC, R_START, "-")
    add_target_hits(w)
    res, _, _ = run(w, tmp_path)
    assert res.verdict is Verdict.PASS and res.n_sites["minor"] == 1
    assert "No off-target site or product reached warning level" in res.rationale[0]
    assert "not included yet" in res.scope  # honest about what was not searched


def test_a_lone_critical_primer_site_fails_and_counts_as_primer_only(tmp_path):
    w = offtarget_genome(f=[10])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    res, _, _ = run(w, tmp_path)
    assert res.amplicons == [] and res.n_primer_only == 1
    assert res.verdict_sites is Verdict.FAIL and res.verdict_amplicons is Verdict.PASS


def test_products_longer_than_the_limit_are_ignored_and_the_limit_is_inclusive(tmp_path):
    w = offtarget_genome(f=[10], r=[5], p=[8])
    add_all(w)
    res, _, _ = run(w, tmp_path, specificity__max_amplicon_size=127)
    assert res.amplicons == [] and res.n_primer_only == 2
    res2, _, _ = run(w, tmp_path / "b", specificity__max_amplicon_size=128)
    assert len(res2.amplicons) == 1


def test_a_weak_probe_gives_an_amplified_but_not_detected_product(tmp_path):
    w = offtarget_genome(f=[10], r=[5], p=[3, 8, 12, 16])  # 4 probe mismatches
    add_all(w)
    res, _, _ = run(w, tmp_path)
    (amp,) = res.amplicons
    assert amp.classification == "amplified_not_detected"
    assert res.verdict_amplicons is Verdict.WARN
    # ...unless the laboratory decides a 'warning'-level probe site is enough for signal
    cfg = load_config()
    cfg.specificity.probe_binds_if = "warning"
    res2, _, _ = run(w, tmp_path / "b", cfg=cfg)
    assert res2.amplicons[0].classification == "likely_detected" and res2.verdict is Verdict.FAIL


def test_a_missing_probe_site_also_means_not_detected(tmp_path):
    w = offtarget_genome(f=[10], r=[5])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    w.hit(NEAR, "reverse", R, ACC, R_START, "-")
    res, _, _ = run(w, tmp_path)
    (amp,) = res.amplicons
    assert amp.classification == "amplified_not_detected" and amp.probe_site is None


def test_severities_are_configurable(tmp_path):
    w = offtarget_genome(f=[10], r=[5], p=[8])
    add_all(w)
    cfg = load_config()
    cfg.specificity.severity.primer_site_critical = "WARN"
    cfg.specificity.severity.amplicon_likely_detected = "WARN"
    res, _, _ = run(w, tmp_path, cfg=cfg)
    assert res.verdict is Verdict.WARN


def three_relevant_forward_sites(f=()):
    """Three different records, each with a relevant forward-primer site."""
    w = World()
    for i in (1, 2, 3):
        acc = f"OT00000{i}.1"
        offtarget_genome(f=f, acc=acc, world=w)
        w.hit(NEAR, "forward", F, acc, F_START, "+")
    return w


def test_a_saturated_off_target_hit_list_is_incomplete_not_a_pass(tmp_path):
    res, _, _ = run(three_relevant_forward_sites(), tmp_path, search__hitlist_size=3)
    assert res.verdict in (Verdict.INCOMPLETE, Verdict.FAIL)
    assert any("saturated" in m for m in res.rationale)


def test_a_full_list_of_irrelevant_hits_is_not_saturation(tmp_path):
    """Hits with too few identical bases to matter do not make the list 'saturated'."""
    w = offtarget_genome()
    for start in (F_START, F_START + 1, F_START + 2):  # shifted placements: ~7 identical bases
        w.hit(NEAR, "forward", F, ACC, start, "+")
    res, _, _ = run(w, tmp_path, search__hitlist_size=3)
    assert not any("saturated" in m for m in res.rationale)


def test_an_assessment_cut_by_the_site_cap_is_incomplete(tmp_path):
    res, _, _ = run(three_relevant_forward_sites(), tmp_path, specificity__max_sites_per_query=2)
    assert res.counts[0].truncated and res.counts[0].sites_assessed == 2
    assert any("only the 2 strongest were assessed" in m for m in res.rationale)
    assert res.verdict in (Verdict.INCOMPLETE, Verdict.FAIL)


def test_without_any_off_target_tier_the_result_is_incomplete(tmp_path):
    w = offtarget_genome()
    cfg = load_config()
    cfg.search.background_taxids = []
    res, _, _ = run(w, tmp_path, cfg=cfg, assay=make_assay())
    assert res.verdict is Verdict.INCOMPLETE
    assert any("No off-target tier was searched" in m for m in res.rationale)


def test_the_intended_target_tier_is_a_positive_control_not_an_off_target(tmp_path):
    w = offtarget_genome()
    add_target_hits(w)
    res, _, _ = run(w, tmp_path)
    assert res.intended_target == {"forward": 1, "reverse": 1, "probe": 1}
    assert not res.sites  # target hits are not assessed as off-target
    assert res.verdict is Verdict.PASS


def test_an_oligo_without_any_perfect_hit_on_its_own_target_is_flagged(tmp_path):
    w = offtarget_genome()  # the target search finds nothing at all
    res, _, _ = run(w, tmp_path)
    assert res.verdict is Verdict.WARN
    assert any("no perfect full-length hit for forward, probe, reverse" in m for m in res.rationale)


def test_no_target_search_means_no_positive_control_finding(tmp_path):
    w = offtarget_genome()
    assay = make_assay(near_neighbour_taxids=[NEAR], target={"accession": "NC_045512.2"})
    res, _, _ = run(w, tmp_path, assay=assay)
    assert not any("Intended target" in f.message for f in res.findings)


# ------------------------------------------------------------------ genomic DNA versus RNA
@pytest.mark.parametrize("template, expect_note", [("RNA", True), ("DNA", False)])
def test_genomic_dna_products_are_flagged_for_rna_assays_in_eukaryotes(
    tmp_path, template, expect_note
):
    w = offtarget_genome(
        taxid=HUMAN, name="Homo sapiens", title="Homo sapiens chromosome 7, RefSeqGene"
    )
    add_all(w, taxid=HUMAN)
    res, _, _ = run(w, tmp_path, assay=make_assay(template_type=template))
    (amp,) = res.amplicons
    assert amp.tier == "background" and amp.record_type == "genomic"
    assert bool(amp.note) is expect_note
    if expect_note:
        assert "genomic DNA" in amp.note


def test_results_are_deterministic(tmp_path):
    def once(sub):
        w = offtarget_genome(f=[10, 16, 17], r=[5], p=[8])
        w.hit(NEAR, "forward", F, ACC, F_START, "+", trim3=5)
        w.hit(NEAR, "reverse", R, ACC, R_START, "-")
        w.hit(NEAR, "probe", P, ACC, P_START, "+")
        return run(w, tmp_path / sub)[0].model_dump_json()

    assert once("a") == once("b")


def test_windows_are_cached_so_a_second_run_needs_no_network_fetches(tmp_path):
    w = offtarget_genome(f=[10, 16, 17])
    w.hit(NEAR, "forward", F, ACC, F_START, "+", trim3=5)
    fake = WorldFake(w)
    cfg = load_config()
    runner, store, fetcher = make_runner(cfg, tmp_path, fake)
    plan = plan_searches(make_assay(near_neighbour_taxids=[NEAR]), cfg)
    parsed: dict = {}
    outcome = run_search(plan, cfg, runner, store, tmp_path / "s", inputs_hash="h", keep=parsed)
    assess_specificity(
        make_assay(near_neighbour_taxids=[NEAR]), cfg, plan, parsed, outcome, fetcher
    )
    assert (fetcher.n_network, fetcher.n_cached) == (1, 0)
    runner2, store2, fetcher2 = make_runner(cfg, tmp_path, fake)
    parsed2: dict = {}
    outcome2 = run_search(plan, cfg, runner2, store2, tmp_path / "s", inputs_hash="h", keep=parsed2)
    assess_specificity(
        make_assay(near_neighbour_taxids=[NEAR]), cfg, plan, parsed2, outcome2, fetcher2
    )
    assert (fetcher2.n_network, fetcher2.n_cached) == (0, 1)
