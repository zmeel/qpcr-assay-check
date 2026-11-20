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


def run(world, tmp_path, cfg=None, assay=None, ancestors_of=None, **cfg_changes):
    cfg = cfg or load_config()
    cfg_changes.setdefault("specificity__partner_scan_max_windows", 0)  # scan: tests below
    # the exclusivity tier needs name resolution, which these tests do not plan
    cfg_changes.setdefault("specificity__off_target_tiers", ["near_neighbours", "background"])
    for key, value in cfg_changes.items():
        obj, attr = key.split("__")
        setattr(getattr(cfg, obj), attr, value)
    assay = assay or make_assay(near_neighbour_taxids=[NEAR])
    fake = WorldFake(world)
    runner, store, fetcher = make_runner(cfg, tmp_path, fake)
    plan = plan_searches(assay, cfg)
    parsed: dict = {}
    outcome = run_search(plan, cfg, runner, store, tmp_path / "s", inputs_hash="h", keep=parsed)
    result = assess_specificity(
        assay, cfg, plan, parsed, outcome, fetcher, ancestors_of=ancestors_of
    )
    return result, fetcher, fake


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
    # the re-aligned forward site has 3 mismatches in its 3'-most 16 nt: R3 grades it likely
    # failure, so it cannot prime and no product forms (one rule set, review 2026-11-17, P3)
    assert f.grade == "likely_failure" and res.amplicons == []
    # by the count-based levels alone (the earlier rule) the warning site still primed
    cfg = load_config()
    cfg.specificity.graded_off_target = False
    old, _, _ = run(w, tmp_path / "levels", cfg=cfg)
    assert old.verdict is Verdict.FAIL and len(old.amplicons) == 1


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
    assert "not searched" not in res.scope and "planned for" not in res.scope
    # with the exclusivity tier required but not searched, the gap is Incomplete evidence
    # (tiers review 2026-11-20, F7), and the scope says so honestly
    res, _, _ = run(
        w, tmp_path / "all",
        specificity__off_target_tiers=["near_neighbours", "background", "exclusivity"],
    )  # fmt: skip
    assert res.verdict is Verdict.INCOMPLETE
    assert "Configured off-target tiers not searched in this run: exclusivity" in res.scope


def test_a_lone_critical_primer_site_warns_and_counts_as_primer_only(tmp_path):
    """A critical primer site without a facing partner forms no product: WARN, not FAIL
    (primer_site_critical_no_product; user decision 2026-09-25, advisor review)."""
    w = offtarget_genome(f=[10])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    res, _, _ = run(w, tmp_path)
    assert res.amplicons == [] and res.n_primer_only == 1
    assert res.verdict_sites is Verdict.WARN and res.verdict_amplicons is Verdict.PASS
    assert any("forming no predicted product" in f.message for f in res.findings)


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
    # 4 mismatches in an unmodified probe are graded likely failure (R9), so a looser level does
    # not make it bind...
    cfg = load_config()
    cfg.specificity.probe_binds_if = "warning"
    res2, _, _ = run(w, tmp_path / "b", cfg=cfg)
    assert res2.amplicons[0].classification == "amplified_not_detected"
    # ...unless the levels alone decide (graded_off_target: false), the earlier rule
    cfg.specificity.graded_off_target = False
    res3, _, _ = run(w, tmp_path / "c", cfg=cfg)
    assert res3.amplicons[0].classification == "likely_detected" and res3.verdict is Verdict.FAIL


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
    res, _, _ = run(w, tmp_path, search__target_tier=True)
    assert res.intended_target == {"forward": 1, "reverse": 1, "probe": 1}
    assert not res.sites  # target hits are not assessed as off-target
    assert res.verdict is Verdict.PASS


def test_an_oligo_without_any_perfect_hit_on_its_own_target_is_flagged(tmp_path):
    w = offtarget_genome()  # the target search finds nothing at all
    res, _, _ = run(w, tmp_path, search__target_tier=True)
    assert res.verdict is Verdict.WARN
    assert any("no perfect full-length hit for forward, probe, reverse" in m for m in res.rationale)


def test_the_target_is_not_searched_as_a_tier_by_default(tmp_path):
    """search.target_tier is off (user decision 2026-10-23): the variant analysis assesses every
    record of the target, and for influenza A the target search took 19 hours."""
    plan = plan_searches(make_assay(near_neighbour_taxids=[NEAR]), load_config())
    assert "target" not in {ps.tier for ps in plan.searches}
    assert any("not searched as a tier" in n for n in plan.notes)
    w = offtarget_genome()
    add_target_hits(w)  # would be the positive control, but nothing searches for it
    res, _, fake = run(w, tmp_path)
    assert not any("Intended target" in f.message for f in res.findings)
    assert all("txid2697049" not in c.get("data", {}).get("ENTREZ_QUERY", "") for c in fake.calls)


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
    cfg.specificity.partner_scan_max_windows = 0  # one re-alignment window, nothing else
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


# ------------------------------------------------------------------ hits outside a tier's taxa
LEAK_ACC = "MW220816.1"


def leaked_world():
    """A near-neighbour search that also returns a record of the intended target, as NCBI's
    ENTREZ_QUERY restriction occasionally does (live: an influenza A record in an exclusivity
    search without influenza A, 2026-10-21)."""
    w = offtarget_genome()  # the genuine near neighbour, taxid NEAR, all three sites perfect
    add_all(w)
    offtarget_genome(acc=LEAK_ACC, taxid=TARGET, name="Leaked target virus", world=w)
    add_all(w, taxid=NEAR, acc=LEAK_ACC)  # filed under NEAR's search, carrying TARGET's taxid
    return w


def lineage_of(taxids):
    """NCBI ancestors, themselves included; 101 is a strain below the near neighbour 100."""
    parents = {101: {100, 1}, NEAR: {1}, TARGET: {1}}
    return {t: {t, *parents.get(t, {1})} for t in taxids}


def test_a_hit_outside_the_tier_taxa_is_set_aside_with_a_finding(tmp_path):
    res, _, _ = run(leaked_world(), tmp_path, ancestors_of=lineage_of)
    assert {s.accession for s in res.sites} == {ACC}  # the near neighbour only
    (f,) = [f for f in res.findings if "set aside" in f.message]
    assert f.severity == "INFO" and "near_neighbours" in f.message
    assert LEAK_ACC in f.message and "Leaked target virus" in f.message


def test_a_descendant_of_the_tier_taxon_is_kept(tmp_path):
    w = offtarget_genome(taxid=101, name="Bacterium exemplum strain X")
    add_all(w, taxid=NEAR)  # returned by the search for NEAR, organism a strain below it
    res, _, _ = run(w, tmp_path, ancestors_of=lineage_of)
    assert {s.accession for s in res.sites} == {ACC}
    assert not any("set aside" in f.message for f in res.findings)


def test_without_lineages_every_hit_counts_as_before(tmp_path):
    res, _, _ = run(leaked_world(), tmp_path)
    assert {s.accession for s in res.sites} == {ACC, LEAK_ACC}


def test_a_failed_lineage_lookup_keeps_every_hit_and_says_so(tmp_path):
    from qpcr_assay_check.ncbi.http import NcbiError

    def failing(taxids):
        raise NcbiError("HTTP 502")

    res, _, _ = run(leaked_world(), tmp_path, ancestors_of=failing)
    assert {s.accession for s in res.sites} == {ACC, LEAK_ACC}
    assert any(
        "could not be checked" in f.message and "HTTP 502" in f.message for f in res.findings
    )


def test_a_hit_without_records_counts_as_inside_its_tier():
    from qpcr_assay_check.ncbi.parser import Hit, Hsp
    from qpcr_assay_check.specificity.assess import _in_tier

    hsp = Hsp(num=1, bit_score=40, evalue=1, identity=20, align_len=20, query_from=1,
              query_to=20, hit_from=1, hit_to=20)  # fmt: skip
    hit = Hit(num=1, descriptions=[], hsps=[hsp])
    assert _in_tier(hit, {NEAR}, lineage_of([NEAR])) is hit  # was silently dropped


def test_only_relevant_hits_have_their_organism_looked_up(tmp_path):
    w = leaked_world()
    w.genome("WEAK1.1", 4242, "Weakly hit organism", filler(400, 9))
    w.hit(NEAR, "forward", F, "WEAK1.1", 101, "+", realistic=False)  # 0-2 identical bases
    asked: list[int] = []

    def recording(taxids):
        asked.extend(taxids)
        return lineage_of(taxids)

    res, _, _ = run(w, tmp_path, ancestors_of=recording)
    assert 4242 not in asked and NEAR in asked and TARGET in asked
    (f,) = [f for f in res.findings if "set aside" in f.message]
    assert "WEAK1.1" not in f.message  # an irrelevant hit is not reported as set aside


# ------------------------------------------------------------------ tiers review 2026-11-20, F1
def test_a_searched_tier_left_out_of_off_target_tiers_is_still_assessed(tmp_path):
    """off_target_tiers says which tiers must be searched, not which are assessed: a near-
    neighbour product the probe detects used to vanish (row No flags) once the tier was left
    out of the list."""
    w = offtarget_genome(f=[10, 15], r=[5], p=[8])
    add_all(w)
    res, _, _ = run(w, tmp_path, specificity__off_target_tiers=["background"])
    assert res.verdict is Verdict.FAIL
    (amp,) = res.amplicons
    assert amp.tier == "near_neighbours" and amp.classification == "likely_detected"


def test_off_target_tiers_names_are_checked():
    from qpcr_assay_check.errors import ConfigError

    for bad in (["target"], ["near_neighbors"], ["background", "background"]):
        with pytest.raises(ConfigError):
            load_config(None, {"specificity": {"off_target_tiers": bad}})
    with pytest.raises(ConfigError, match="reason"):
        load_config(None, {"specificity": {"tier_waivers": {"near_neighbours": " "}}})
    with pytest.raises(ConfigError, match="unknown tier"):
        load_config(None, {"specificity": {"tier_waivers": {"target": "no"}}})
    cfg = load_config(None, {"specificity": {"tier_waivers": {"near_neighbours": "in the list"}}})
    assert cfg.specificity.tier_waivers == {"near_neighbours": "in the list"}


def test_a_record_of_the_target_is_never_an_off_target_site(tmp_path):
    """Tiers review 2026-11-20, F2: a near neighbour that contains the target (a genus around a
    species target) returns the target's own records; they are set aside, its other species
    kept, even if the NOT-target restriction lets one through."""
    genus, sibling = 50, 51

    def lineages(taxids):
        parents = {TARGET: {genus, 1}, sibling: {genus, 1}, genus: {1}}
        return {t: {t, *parents.get(t, {1})} for t in taxids}

    w = offtarget_genome(taxid=sibling, name="Sister virus")
    add_all(w, taxid=genus)
    offtarget_genome(acc=LEAK_ACC, taxid=TARGET, name="The target itself", world=w)
    add_all(w, taxid=genus, acc=LEAK_ACC)
    res, _, _ = run(
        w, tmp_path, assay=make_assay(near_neighbour_taxids=[genus]), ancestors_of=lineages
    )
    assert {s.accession for s in res.sites} == {ACC}
    assert any("set aside" in f.message and LEAK_ACC in f.message for f in res.findings)


def test_the_restriction_check_counts_by_lineage(tmp_path):
    # tiers review 2026-11-20, F5: exact taxon IDs read "0 of N" when records sit below the
    # requested taxon; the lineage check the assessment already makes is the meaningful count
    w = leaked_world()
    offtarget_genome(acc="OT000002.1", taxid=101, name="Strain below NEAR", world=w)
    add_all(w, taxid=NEAR, acc="OT000002.1")
    res, _, _ = run(w, tmp_path, ancestors_of=lineage_of)
    assert res.restriction_by_lineage["near_neighbours"] == {
        "inside": 6, "set_aside": 3, "not_checkable": 0
    }  # fmt: skip
    assert run(leaked_world(), tmp_path / "plain")[0].restriction_by_lineage == {}


def _three_products(probe_on=None):
    w = offtarget_genome(f=[10], r=[5], p=[8])
    for acc in ("OT000002.1", "OT000003.1"):
        offtarget_genome(f=[10], r=[5], p=[8], acc=acc, world=w)
    for acc in (ACC, "OT000002.1", "OT000003.1"):
        w.hit(NEAR, "forward", F, acc, F_START, "+")
        w.hit(NEAR, "reverse", R, acc, R_START, "-")
    if probe_on:
        w.hit(NEAR, "probe", P, probe_on, P_START, "+")
    w.stat = {"eff_space": 811905916, "kappa": 0.710602795216363, "lambda": 1.37406312246009}
    return w


def test_a_cut_product_list_is_bounded_when_no_detectable_product_can_hide_beyond_it(tmp_path):
    """Tiers review 2026-11-20, F4: HSV-2 filled the 500-product cap of HSV-1's near-neighbour
    tier on every run, so the tier read Incomplete although the conclusion was clear."""
    res, _, _ = run(
        _three_products(), tmp_path, specificity__max_amplicons=1, specificity__cautious_tiers=[]
    )
    (cut,) = [f for f in res.findings if "was cut at max_amplicons" in f.message]
    assert cut.severity == "INFO" and "Bounded" in cut.message
    assert res.verdict is Verdict.WARN  # a product the probe does not detect: Review
    # a probe site that binds on a record beyond the cut: a detectable product may hide there
    res, _, _ = run(
        _three_products(probe_on="OT000003.1"), tmp_path / "b", specificity__max_amplicons=1,
        specificity__cautious_tiers=[],
    )  # fmt: skip
    (cut,) = [f for f in res.findings if "was cut at max_amplicons" in f.message]
    assert cut.severity == "INCOMPLETE" and "beyond it (e.g. OT000003.1)" in cut.message
    # in a cautious tier a gapped probe site could bind unreported: not bounded
    res, _, _ = run(_three_products(), tmp_path / "c", specificity__max_amplicons=1)
    (cut,) = [f for f in res.findings if "was cut at max_amplicons" in f.message]
    assert cut.severity == "INCOMPLETE" and "not bounded: a probe site with a gap" in cut.message


def test_products_are_also_counted_as_distinct_patterns(tmp_path):
    res, _, _ = run(_three_products(), tmp_path)
    (f,) = [f for f in res.findings if "predicted off-target product(s)" in f.message]
    assert "3 predicted off-target product(s)" in f.message
    assert "1 distinct product pattern(s)" in f.message
