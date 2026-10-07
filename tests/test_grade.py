"""Graded mismatch classes (docs/MISMATCH_CLASSES.md). Alignments are SYNTHETIC: a primer and
its site in the primer's own sense, mutated at chosen positions from the 3' end."""

from __future__ import annotations

import pytest

from qpcr_assay_check.oligo import grade as g

PRIMER = "RATTGTCACCATAAGCAGCCA"  # the user's enterovirus reverse primer (5'->3')
SITE = "AATTGTCACCATAAGCAGCCA"  # a perfect site (R = A)


def site_with(changes: dict[int, str], base: str = SITE) -> str:
    """Replace the base at position -k (1 = 3'-terminal) by the given base."""
    s = list(base)
    for k, b in changes.items():
        assert s[len(s) - k] != b, f"-{k} is already {b}"
        s[len(s) - k] = b
    return "".join(s)


def mutated(*positions: int) -> str:
    """The site with a different base (T, or G where T is already there) at each position."""
    return site_with({k: "G" if SITE[len(SITE) - k] == "T" else "T" for k in positions})


def test_perfect_and_degenerate_primer_bases_match():
    assert g.grade_primer(PRIMER, SITE).cls == g.PERFECT
    assert g.grade_primer(PRIMER, "G" + SITE[1:]).cls == g.PERFECT  # R matches G too


def test_ev_d68_reverse_primer_c_a_at_minus_3_is_tolerated():
    """Live: EV-D68 site ...AGTCA vs primer ...AGCCA: primer C faces template A (C-A), G3."""
    r = g.grade_primer(PRIMER, site_with({3: "T"}))
    assert (r.cls, r.rule) == (g.TOLERATED, "R1") and "C-A at -3" in r.note


@pytest.mark.parametrize(
    ("pos", "site_base", "expected"),
    [
        (1, "T", g.FAILURE),  # primer A, template A: A-A (G1) terminal -> avoid
        (2, "G", g.AT_RISK),  # primer C, template C: C-C (G1) penultimate -> avoid
        (1, "G", g.TOLERATED),  # primer A, template C: A-C (G3) terminal -> acceptable
        (2, "A", g.TOLERATED),  # primer C, template T: C-T (G2) penultimate -> acceptable
        (1, "C", g.FAILURE),  # primer A, template G: A-G (G1) terminal
    ],
)
def test_single_mismatch_in_the_last_5_follows_stadhouders_table_1(pos, site_base, expected):
    assert g.grade_primer(PRIMER, site_with({pos: site_base})).cls == expected


def test_position_4_is_marked_interpolated():
    assert "not tested" in g.grade_primer(PRIMER, site_with({4: "T"})).note


def test_single_mismatch_beyond_5_is_tolerated_per_lefever():
    r6 = g.grade_primer(PRIMER, mutated(7))
    r12 = g.grade_primer(PRIMER, mutated(12))
    assert (r6.cls, r6.rule) == (g.TOLERATED, "R2") and "can be tolerated" in r6.note
    assert r12.cls == g.TOLERATED and "negligible" in r12.note


def test_several_mismatches():
    assert g.grade_primer(PRIMER, mutated(1, 4)).cls == g.FAILURE  # terminal + another
    assert g.grade_primer(PRIMER, mutated(8, 12)).cls == g.AT_RISK  # 2, none in the last 5
    # 3 within the 3'-most 16 nt, none in the last 5: likely failure since 2026-09-30 (Lefever
    # Fig. 6 median about 15 dCq; Otwell 2025 +6 to +7 Ct, missed at 50 copies)
    assert g.grade_primer(PRIMER, mutated(7, 10, 14)).cls == g.FAILURE
    assert g.grade_primer(PRIMER, mutated(3, 10, 14)).cls == g.FAILURE  # 3, one in the last 5
    assert g.grade_primer(PRIMER, mutated(7, 9, 12, 15)).cls == g.FAILURE  # 4 spread
    assert g.grade_primer(PRIMER, mutated(16, 17, 18, 19)).cls == g.AT_RISK  # 4 adjacent, 5' end


def test_gaps_and_ambiguity_codes_are_indeterminate():
    assert g.grade_primer(PRIMER + "-", SITE + "A").cls == g.INDETERMINATE
    assert g.grade_primer(PRIMER, site_with({2: "Y"})).rule == "R6"


def test_probes_keep_the_current_rule_and_mgb_mismatches_are_indeterminate():
    probe = "AAACACGGACACCCAAA"
    one_internal = probe[:5] + "T" + probe[6:]
    assert g.grade_probe(probe, one_internal, mgb=False).cls == g.TOLERATED
    assert g.grade_probe(probe, one_internal, mgb=True).cls == g.INDETERMINATE
    assert g.grade_probe(probe, probe[:-1] + "G", mgb=False).cls == g.AT_RISK
    two = one_internal[:9] + "T" + one_internal[10:]
    assert g.grade_probe(probe, two, mgb=True).cls == g.FAILURE  # 2+ in an MGB probe
    assert g.grade_probe(probe, two, mgb=False).cls == g.AT_RISK  # unmodified probe: unchanged


def test_primer_pair_rule_r8():
    assert g.pair_fails(3, 2) and g.pair_fails(1, 4) and g.pair_fails(4, 1)
    assert not g.pair_fails(3, 1) and not g.pair_fails(2, 2)


def test_one_mgb_mismatch_is_undetermined_not_an_escape(tmp_path):
    """User decision 2026-09-25: an MGB probe with 1 mismatch is undetermined, neither detected nor
    an escape; an unexplained gap still counts as not detected."""
    from qpcr_assay_check.variants.exhaustive import site_state

    from .test_exclusivity import site

    mgb1 = site(1, "probe", "critical").model_copy(
        update={"grade": g.INDETERMINATE, "grade_rule": "R9"}
    )
    gap = site(1, "reverse", "critical").model_copy(
        update={"grade": g.INDETERMINATE, "grade_rule": "R5", "n_gap": 1}
    )
    assert site_state(mgb1) == "undetermined" and site_state(gap) == "fail"


def test_a_worst_case_site_is_graded_not_a_crash():
    """Review finding: unaligned ends of a worst-case site ('.', window not fetched) raised
    KeyError; they are mismatches of unknown type."""
    grade = g.grade_primer(PRIMER, SITE[:-3] + "...")
    assert grade.cls == g.FAILURE


def test_an_ambiguity_code_never_hides_a_real_failure():
    """Review finding: R6 was returned before the real mismatches were looked at."""
    terminal = mutated(1)  # a terminal mismatch alone: likely failure
    with_code = site_with({3: "Y"}, base=terminal)  # plus a compatible code at -3 (C)
    grade = g.grade_primer(PRIMER, with_code)
    assert grade.cls == g.FAILURE and "ambiguity" in grade.note
    # the code decides between detectable and not: undetermined
    assert g.grade_primer(PRIMER, site_with({2: "Y"})).rule == "R6"
    # beyond the last 5 nt a compatible code is a match
    assert g.grade_primer(PRIMER, site_with({6: "Y"})).cls == g.PERFECT  # -6 is C
    # a code that cannot pair with the primer base is a plain mismatch
    assert g.grade_primer(PRIMER, site_with({1: "Y"})).rule == "R1"  # -1 is A


def test_homopolymer_length_differences_are_graded_r5b():
    """Advisor 2026-09-26 (N. gonorrhoeae reverse primer, poly-A 7): no PCR study measured a
    homopolymer bulge; one base, run away from the last 3 nt = at risk, else likely failure.
    SYNTHETIC alignments modelled on that primer."""
    r = "CGGTTTGACCGGTTAAAAAAAGAT"
    one_more = g.grade_primer("CGGTTTGACCGGTT-AAAAAAAGAT", "CGGTTTGACCGGTTAAAAAAAAGAT")
    one_less = g.grade_primer(r, "CGGTTTGACCGGTT-AAAAAAGAT")
    two_more = g.grade_primer("CGGTTTGACCGGTT--AAAAAAAGAT", "CGGTTTGACCGGTTAAAAAAAAAGAT")
    assert (one_more.cls, one_more.rule) == (g.AT_RISK, "R5b") and one_less.cls == g.AT_RISK
    assert "run ending at -4" in one_more.note
    assert two_more.cls == g.FAILURE
    # a run that reaches the last 3 nt
    near = g.grade_primer("ACGTACGTACGTACG-TTTT", "ACGTACGTACGTACGTTTTT")
    assert near.cls == g.FAILURE and "last 3 nt" in near.note
    # plus a mismatch: the worse of the two
    both = g.grade_primer("CGGTTTGACCGGTT-AAAAAAAGAT", "CGGTTTGACCGTTTAAAAAAAAGAT")
    assert both.cls in (g.AT_RISK, g.FAILURE) and "mismatch" in both.note
    # a gap that is not in a run stays indeterminate (R5)
    assert g.grade_primer("CGGTTTGAC-CGGTTAAAAAAAGAT", "CGGTTTGACTCGGTTAAAAAAAGAT").rule == "R5"


def test_a_gap_never_hides_mismatches_that_already_fail():
    """User 2026-09-26 (Neisseria probe variant with 7 mismatches and a gap): 'indeterminate'
    was milder than the mismatches alone; a gap can only make a site worse."""
    probe = "CCCTTCAACATCAGTGAAA"
    many = "GCCTTCA--ATCTGTAAAC"  # SYNTHETIC: several mismatches plus a 2-base gap
    assert g.grade_probe(probe, many, mgb=True).cls == g.FAILURE
    assert "deleted" in g.grade_probe(probe, many, mgb=True).note
    assert g.grade_probe(probe, many, mgb=False).cls == g.FAILURE  # R5c: deletion + 3+ mismatches
    assert g.grade_primer(PRIMER[:-1] + "-", mutated(1, 2, 3)[:-1] + "A").cls == g.FAILURE
    # an insertion in the template within the probe site (not measured) stays indeterminate
    assert g.grade_probe("CCCTTCA-ACATCAGTGAAA", "CCCTTCATACATCAGTGAAA", mgb=True).rule == "R5"


def test_an_oligo_end_without_a_partner_base_is_a_mismatch_not_a_gap():
    """Live Neisseria report (user, 2026-09-26): '-24 deleted' plus poly-A 7->8 was
    indeterminate because of two gap blocks; the 5'-terminal base without a partner is a 5'
    mismatch, so the site is graded like the other poly-A 7->8 sites. SYNTHETIC alignments."""
    q, s = "CGGTTTGACCGGTT-AAAAAAAGAT", "-GGTTTGACCGGTTAAAAAAAAGAT"
    assert (g.grade_primer(q, s).cls, g.grade_primer(q, s).rule) == (g.AT_RISK, "R5b")
    # a 3'-terminal base without a partner is a terminal mismatch: likely failure
    three = g.grade_primer("ACGTACGTACGTACGTACGT", "ACGTACGTACGTACGTACG-")
    assert three.cls == g.FAILURE and three.rule == "R1"


def test_mismatches_beyond_the_tested_region_count_less():
    """Otwell et al. 2025 (supplementary Table 2): 3-4 primer mismatches only beyond -16 shifted
    Ct by at most 2.2; with one more within the 3'-most 16 nt mostly +3 to +6, never a miss at
    50 copies. Lefever 2013 tested the 3'-most 16 nt only."""
    only_outer = g.grade_primer(PRIMER, mutated(19, 20, 21))
    assert (only_outer.cls, only_outer.rule) == (g.TOLERATED, "R3b")
    assert g.grade_primer(PRIMER, mutated(17, 18, 19, 20)).cls == g.TOLERATED
    assert g.grade_primer(PRIMER, mutated(9, 19, 20, 21)).cls == g.AT_RISK  # was likely failure
    assert g.grade_primer(PRIMER, mutated(1, 4, 20)).cls == g.FAILURE  # the inner rule stands
    # Lefever's 4-adjacent exception holds for 4 mismatches in all, not with more beyond -16
    # (Otwell 2025, China_N FN5780: -13..-16 plus 3 at the 5' end, +13.6 Ct)
    assert g.grade_primer(PRIMER, mutated(12, 13, 14, 15)).cls == g.AT_RISK
    assert g.grade_primer(PRIMER, mutated(12, 13, 14, 15, 20)).cls == g.FAILURE


def test_the_pair_rule_counts_mismatches_within_the_tested_region():
    from types import SimpleNamespace as NS

    def primer(site: str) -> NS:
        gr = g.grade_primer(PRIMER, site)
        mm = g._mismatches(PRIMER, site)[0]
        return NS(grade=gr.cls, grade_rule=gr.rule, n_mismatch=len(mm), note="",
                  q_aln=PRIMER, s_aln=site)  # fmt: skip

    probe = NS(grade=g.PERFECT, grade_rule="", n_mismatch=0, note="")
    # 3 + 2 mismatches, but 2 of the first primer's lie beyond -16: 1 + 2 counted, no pair rule
    outcome, by_pair = g.combination_outcome(primer(mutated(9, 19, 20)), probe,
                                             primer(mutated(8, 12)))  # fmt: skip
    assert not by_pair and outcome == "at risk"
    assert g.pair_fails(g.tested_mismatches(primer(mutated(7, 9, 12))), 2)


def test_more_mismatches_beyond_the_tested_region_than_were_measured_are_at_risk():
    """Otwell 2025 measured 3-4 mismatches beyond -16 only (code review 2026-09-30)."""
    four = g.grade_primer(PRIMER, mutated(17, 18, 19, 20))
    assert four.cls == g.TOLERATED and "outside the measured data" not in four.note
    five = g.grade_primer(PRIMER, mutated(17, 18, 19, 20, 21))
    assert (five.cls, five.rule) == (g.AT_RISK, "R3b")
    assert "outside the measured data" in five.note
    both = g.grade_primer(PRIMER, mutated(9, 17, 18, 19, 20, 21))
    assert both.cls == g.AT_RISK and both.rule == "R2+R3b"
    assert "outside the measured data" in both.note


def test_deletions_in_the_probe_site_follow_otwell_2025():
    """Otwell et al. 2025, probe-site deletions: C4 ORF8 <= 6 nt detected with Ct shifts <= 5,
    7 nt Ct > 40 at 50 copies, 8 nt not detected; ncov_n_gene 3 nt about +3 Ct; Young-S 3 nt
    plus three mismatches not detected; Yale 69/70 del 6 nt not detected (the worse is taken).
    SYNTHETIC alignments of a 26-nt probe site."""
    probe = "ACGTTGCAACGTTGCAACGTTGCAAC"  # 26 nt, SYNTHETIC

    def deleted(n, at=10):
        return probe[:at] + "-" * n + probe[at + n :]

    for n in (1, 3, 5):
        d = g.grade_probe(probe, deleted(n), mgb=False)
        assert (d.cls, d.rule) == (g.AT_RISK, "R5c") and "Otwell" in d.note
    for n in (6, 7, 8):
        assert g.grade_probe(probe, deleted(n), mgb=False).cls == g.FAILURE
    # a deletion with three mismatches: not detected (Young-S)
    three = deleted(3)[:20] + "".join("T" if c != "T" else "A" for c in deleted(3)[20:23])
    three += deleted(3)[23:]
    assert g.grade_probe(probe, three, mgb=False).cls == g.FAILURE
    # with one mismatch: at risk, and the note says the combination was not measured
    one = deleted(3)[:20] + ("T" if deleted(3)[20] != "T" else "A") + deleted(3)[21:]
    assert "not measured" in g.grade_probe(probe, one, mgb=False).note
    # an MGB probe whose mismatches already fail keeps failing
    assert g.grade_probe(probe, three, mgb=True).cls == g.FAILURE


@pytest.mark.parametrize(
    ("site_base", "kind"),
    [("A", "T-T"), ("G", "T-C")],  # site in the primer's sense: the template faces its complement
)
def test_terminal_g2_is_at_risk_with_every_source_named(site_base, kind):
    """User, 2026-10-02: Stadhouders 'avoid' (3.8-4.8 Ct), but Kwok 1990 amplified terminal G2
    like a match and Huang 1992 found C-T the most easily extended mispair."""
    primer = "GACCCCAAAATCAGCGAAAT"
    r = g.grade_primer(primer, primer[:-1] + site_base)
    assert (r.cls, r.rule) == (g.AT_RISK, "R1") and f"{kind} at -1" in r.note
    assert "Kwok 1990" in r.note and "Huang 1992" in r.note
    c_t = g.grade_primer("GACCCCAAAATCAGCGAAAC", "GACCCCAAAATCAGCGAAAA")  # primer C, template T
    assert c_t.cls == g.AT_RISK and "C-T at -1" in c_t.note
    # terminal G1 stays likely failure, terminal G3 stays tolerated with Huang printed
    assert g.grade_primer(PRIMER, site_with({1: "T"})).cls == g.FAILURE
    g3 = g.grade_primer(PRIMER, site_with({1: "G"}))
    assert g3.cls == g.TOLERATED and "Huang 1992" in g3.note


@pytest.mark.parametrize(
    ("pos", "expected"),
    [(1, g.FAILURE), (5, g.FAILURE), (7, g.FAILURE), (8, g.INDETERMINATE), (12, g.INDETERMINATE)],
)
def test_one_mgb_mismatch_under_the_mgb_is_a_likely_failure(pos, expected):
    """User, 2026-10-02, after Kutyavin 2000: a single mismatch in the 3'-most 7 nt of an MGB
    probe (the MGB's 5-6 bp plus 1-2 bp of sliding) is a likely failure; further toward the 5'
    end the MGB adds nothing and the class stays undetermined."""
    probe = "AAACACGGACACCCAAA"
    i = len(probe) - pos
    site = probe[:i] + ("T" if probe[i] != "T" else "G") + probe[i + 1 :]
    r = g.grade_probe(probe, site, mgb=True)
    assert (r.cls, r.rule) == (expected, "R9") and f"at -{pos}" in r.note and "Kutyavin" in r.note
    assert g.grade_probe(probe, site, mgb=False).cls != g.FAILURE  # unmodified probes unchanged


def test_an_unmodified_probe_fails_from_three_mismatches_on():
    """R9, unmodified probes (user decision 2026-10-07, after the Legionella run of 2026-10-02
    graded an 11-mismatch unmodified probe site only 'at risk'): 1 mismatch outside the last 5 nt
    tolerated, 2 at risk, 3 or more likely failure. Klungthong et al. 2010 measured two mismatches
    in an unmodified 30-mer, every sample still detected; beyond that there is no source, so the
    ceiling is expert judgement, as the MGB rule already was."""
    probe = "ACGTTGCAACGTTGCAACGTTGCAAC"  # 26 nt, SYNTHETIC

    def mism(n, start=2):
        s = list(probe)
        for i in range(start, start + 2 * n, 2):
            s[i] = "T" if s[i] != "T" else "A"
        return "".join(s)

    assert g.grade_probe(probe, mism(1), mgb=False).cls == g.TOLERATED
    two = g.grade_probe(probe, mism(2), mgb=False)
    assert (two.cls, two.rule) == (g.AT_RISK, "R9") and "Klungthong" in two.note
    for n in (3, 4, 8):
        bad = g.grade_probe(probe, mism(n), mgb=False)
        assert (bad.cls, bad.rule) == (g.FAILURE, "R9"), n
        assert f"{n} mismatches" in bad.note and "expert judgement" in bad.note
    # one mismatch inside the last 5 nt stays at risk, not a failure
    last5 = probe[:-3] + ("T" if probe[-3] != "T" else "A") + probe[-2:]
    assert g.grade_probe(probe, last5, mgb=False).cls == g.AT_RISK


def test_probe_deletions_say_where_the_measured_data_stop():
    """R5c grades only what Otwell et al. 2025 measured: 25-28 nt linear probes, 55 C, 50 cycles,
    deletions of 1, 3, 4, 6, 7 and 8 nt. The classes are unchanged; the note now says when a
    probe's length or chemistry, or a deletion length, lies outside that (advisor's literature
    search 2026-10-07: no study measured a deletion under an MGB probe)."""
    long_probe = "ACGTTGCAACGTTGCAACGTTGCAAC"  # 26 nt, inside the measured range
    short_probe = "ACGTTGCAACGTTGCAACG"  # 19 nt, outside it

    def deleted(probe, n, at=8):
        return probe[:at] + "-" * n + probe[at + n :]

    measured = g.grade_probe(long_probe, deleted(long_probe, 3), mgb=False)
    assert measured.cls == g.AT_RISK and "55 C over 50 cycles" in measured.note
    assert "never tested" not in measured.note and "no measured data" not in measured.note
    for n in (2, 5):  # lengths with no template in the study
        note = g.grade_probe(long_probe, deleted(long_probe, n), mgb=False).note
        assert f"{n} nt was never tested" in note and "interpolated" in note
    mgb = g.grade_probe(long_probe, deleted(long_probe, 3), mgb=True)
    assert mgb.cls == g.AT_RISK and "no study measured a deletion under an MGB probe" in mgb.note
    short = g.grade_probe(short_probe, deleted(short_probe, 3), mgb=False)
    assert short.cls == g.AT_RISK and "no measured data for a probe of 19 nt" in short.note
