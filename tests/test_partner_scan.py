"""Partner scan: a partner primer or probe that BLAST did not report is found next to the one it
did report (constructed world of tests/world.py)."""

from qpcr_assay_check.specificity.models import SiteResult
from qpcr_assay_check.specificity.scan import facing_window
from qpcr_assay_check.verdict import Verdict

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .test_assess import (
    ACC,
    F_START,
    HUMAN,
    NEAR,
    P_START,
    R_START,
    add_all,
    offtarget_genome,
    run,
)

SCAN = {"specificity__partner_scan_max_windows": 1000}


def test_an_unreported_reverse_primer_is_found_next_to_the_forward_primer(tmp_path):
    w = offtarget_genome(f=[10], r=[5, 12], p=[8])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")  # BLAST reported only the forward primer
    w.hit(NEAR, "probe", P, ACC, P_START, "+")
    without, _, _ = run(w, tmp_path / "off")
    assert without.amplicons == []
    res, _, fake = run(w, tmp_path / "on", **SCAN)
    (amp,) = res.amplicons
    assert (amp.start, amp.end, amp.classification) == (F_START, R_START + 23, "likely_detected")
    rev = next(s for s in res.sites if s.id == amp.right_site)
    assert rev.source == "scanned" and rev.orientation == "-" and rev.n_mismatch == 2
    assert rev.subject_start == R_START and "partner scan" in rev.note
    assert rev.organism == "Bacterium exemplum" and rev.tm_c is not None
    assert res.verdict is Verdict.FAIL
    scan = res.partner_scan
    assert (scan.primer_sites, scan.windows, scan.primer_sites_added) == (1, 1, 1)
    (call,) = [c for c in fake.efetch_calls if int(c["seq_start"]) == F_START]
    assert int(call["seq_stop"]) == len(w.genomes[ACC]["seq"])  # the record's end, not +1999
    assert any(f.message.startswith("Partner scan:") for f in res.findings)


def test_an_unreported_probe_is_re_aligned_inside_the_product(tmp_path):
    w = offtarget_genome(f=[10], r=[5])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    w.hit(NEAR, "reverse", R, ACC, R_START, "-")  # no probe hit from BLAST
    res, _, _ = run(w, tmp_path, **SCAN)
    (amp,) = res.amplicons
    probe = next(s for s in res.sites if s.id == amp.probe_site)
    assert amp.classification == "likely_detected" and probe.source == "scanned"
    assert (probe.subject_start, probe.orientation, probe.n_mismatch) == (P_START, "+", 0)
    assert res.partner_scan.probe_sites_added == 1


def test_primer_sites_that_already_form_a_product_are_not_scanned(tmp_path):
    w = offtarget_genome(f=[10], r=[5], p=[8])
    add_all(w)
    res, _, fake = run(w, tmp_path, **SCAN)
    assert len(res.amplicons) == 1 and not [s for s in res.sites if s.source == "scanned"]
    assert res.partner_scan.primer_sites == 0 and res.partner_scan.windows == 0
    assert fake.efetch_calls == []  # the probe site was reported: nothing to re-align


def test_a_partner_too_poor_to_prime_adds_nothing(tmp_path):
    w = offtarget_genome(f=[10], r=[1, 3, 5, 7, 9, 11, 13])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    res, _, _ = run(w, tmp_path, **SCAN)
    assert res.amplicons == [] and res.partner_scan.primer_sites_added == 0


def test_primer_sites_beyond_the_window_limit_make_the_scan_incomplete(tmp_path):
    w = offtarget_genome(f=[10], r=[5, 12], p=[8])
    offtarget_genome(f=[10], r=[5, 12], p=[8], acc="OT000002.1", world=w)
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    w.hit(NEAR, "forward", F, "OT000002.1", F_START, "+")
    res, _, _ = run(w, tmp_path, specificity__partner_scan_max_windows=1)
    scan = res.partner_scan
    assert (scan.primer_sites, scan.windows, scan.not_scanned) == (2, 1, 1)
    assert len(res.amplicons) == 1  # the scanned record only
    assert any(
        f.severity == "INCOMPLETE" and "partner_scan_max_windows" in f.message for f in res.findings
    )


def test_the_window_faces_the_way_the_primer_extends():
    base = {
        "id": "S1", "tier": "t", "query": "forward", "role": "forward", "oligo": "A",
        "accession": "X", "source": "blast_full", "q_aln": "A", "s_aln": "A", "midline": "|",
        "n_match": 1, "n_mismatch": 0, "n_gap": 0, "n_ambiguous": 0, "defect_positions": [],
        "mismatches_last5": 0, "mismatches_last3": 0, "terminal_defect": False,
        "clean_3prime_nt": 1, "level": "critical",
    }  # fmt: skip
    plus = SiteResult(**base, orientation="+", subject_start=100, subject_end=119)
    minus = SiteResult(**base, orientation="-", subject_start=100, subject_end=119,
                       subject_length=5000)  # fmt: skip
    assert facing_window(plus, 2000) == (100, 2099)
    assert facing_window(minus, 2000) == (1, 119)
    assert facing_window(minus, 50) == (70, 119)


def test_a_probe_too_poor_to_bind_is_not_added(tmp_path):
    """Code review 2026-09-30: only probe sites of at least warning level are added."""
    w = offtarget_genome(f=[10], r=[5], p=[1, 3, 5, 7, 9, 11, 13, 15, 17, 19])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    w.hit(NEAR, "reverse", R, ACC, R_START, "-")
    res, _, _ = run(w, tmp_path, **SCAN)
    (amp,) = res.amplicons
    assert amp.classification == "amplified_not_detected" and amp.probe_site is None
    assert res.partner_scan.probe_sites_added == 0 and res.partner_scan.product_windows == 1
    assert not [s for s in res.sites if s.source == "scanned"]


def test_the_same_record_in_two_tiers_gets_its_partner_in_each(tmp_path):
    """Code review 2026-09-30: products are paired per tier, so de-duplication is too."""
    w = offtarget_genome(f=[10], r=[5, 12], p=[8])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")
    w.hit(HUMAN, "forward", F, ACC, F_START, "+")  # the same record found in the background tier
    w.hit(NEAR, "probe", P, ACC, P_START, "+")
    w.hit(HUMAN, "probe", P, ACC, P_START, "+")
    res, _, _ = run(w, tmp_path, **SCAN)
    assert sorted(a.tier for a in res.amplicons) == ["background", "near_neighbours"]
    assert res.partner_scan.primer_sites_added == 2


def test_product_fetches_count_against_the_limit(tmp_path):
    w = offtarget_genome(f=[10], r=[5, 12])
    w.hit(NEAR, "forward", F, ACC, F_START, "+")  # the scan finds the reverse primer: 1 fetch
    offtarget_genome(f=[10], r=[5], acc="OT000002.1", world=w)
    w.hit(NEAR, "forward", F, "OT000002.1", F_START, "+")
    w.hit(NEAR, "reverse", R, "OT000002.1", R_START, "-")  # a product without a probe site
    res, _, _ = run(w, tmp_path, specificity__partner_scan_max_windows=1)
    scan = res.partner_scan
    assert (scan.windows, scan.product_windows, scan.products_not_scanned) == (1, 0, 1)
    assert any(
        f.severity == "INCOMPLETE" and f.message.startswith("Probe re-alignment incomplete")
        for f in res.findings
    )


def test_a_tier_whose_product_list_was_cut_is_not_scanned(tmp_path):
    w = offtarget_genome(f=[10], r=[5], p=[8])
    for acc in ("OT000002.1", "OT000003.1"):
        offtarget_genome(f=[10], r=[5], p=[8], acc=acc, world=w)
    for acc in (ACC, "OT000002.1"):
        w.hit(NEAR, "forward", F, acc, F_START, "+")
        w.hit(NEAR, "reverse", R, acc, R_START, "-")
    w.hit(NEAR, "forward", F, "OT000003.1", F_START, "+")  # unpaired, in the cut tier
    res, _, _ = run(w, tmp_path, specificity__max_amplicons=1, **SCAN)
    assert res.partner_scan.primer_sites == 0 and res.partner_scan.windows == 0


def test_the_limitations_say_whether_the_scan_ran(tmp_path):
    w = offtarget_genome(f=[10], r=[5], p=[8])
    add_all(w)
    on, _, _ = run(w, tmp_path / "on", **SCAN)
    off, _, _ = run(w, tmp_path / "off")
    assert any("partner scan narrows that gap" in x for x in on.limitations)
    assert any("partner scan was switched off" in x for x in off.limitations)


def test_a_run_of_n_is_not_a_partner_site(tmp_path):
    """Live enterovirus run (2026-09-30): PX731700.1 has a stretch of N 1.5 kb downstream; the
    scan took it for a perfect reverse primer site and predicted a 1,506-bp product."""
    from .world import World, filler

    w = World()
    seq = filler(200, 1) + F + filler(300, 2) + "N" * 60 + filler(200, 3)
    w.genome(ACC, NEAR, "Rhinovirus A", seq)
    w.hit(NEAR, "forward", F, ACC, 201, "+")
    res, _, _ = run(w, tmp_path, **SCAN)
    assert res.amplicons == [] and res.partner_scan.primer_sites_added == 0


def test_unobserved_bases_count_as_mismatches_in_a_scanned_site():
    from qpcr_assay_check.align import realign

    strict = realign.measure("ACGTACGT", "ACGNNCGT", unobserved_matches=False)
    assert (strict.n_mismatch, strict.n_ambiguous) == (2, 0)
    lenient = realign.measure("ACGTACGT", "ACGNNCGT")
    assert (lenient.n_mismatch, lenient.n_ambiguous) == (0, 2)
    sc = realign.Scoring(unobserved_matches=False)
    aln = realign.align_semiglobal("ACGTACGTAC", "TTTT" + "N" * 12 + "TTACGTACGTCCTT", sc)
    assert "N" not in aln.s_aln and aln.s_aln.startswith("ACGTACGT")
