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
    assert g.grade_primer(PRIMER, mutated(7, 10, 14)).cls == g.AT_RISK  # 3, none in the last 5
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
    assert "plus a gap" in g.grade_probe(probe, many, mgb=True).note
    assert g.grade_probe(probe, many, mgb=False).cls == g.AT_RISK
    assert g.grade_primer(PRIMER[:-1] + "-", mutated(1, 2, 3)[:-1] + "A").cls == g.FAILURE
    # a gap alone (no mismatches) stays indeterminate
    assert g.grade_probe(probe, "CCCTTCA-CATCAGTGAAA", mgb=True).rule == "R5"


def test_an_oligo_end_without_a_partner_base_is_a_mismatch_not_a_gap():
    """Live Neisseria report (user, 2026-09-26): '-24 deleted' plus poly-A 7->8 was
    indeterminate because of two gap blocks; the 5'-terminal base without a partner is a 5'
    mismatch, so the site is graded like the other poly-A 7->8 sites. SYNTHETIC alignments."""
    q, s = "CGGTTTGACCGGTT-AAAAAAAGAT", "-GGTTTGACCGGTTAAAAAAAAGAT"
    assert (g.grade_primer(q, s).cls, g.grade_primer(q, s).rule) == (g.AT_RISK, "R5b")
    # a 3'-terminal base without a partner is a terminal mismatch: likely failure
    three = g.grade_primer("ACGTACGTACGTACGTACGT", "ACGTACGTACGTACGTACG-")
    assert three.cls == g.FAILURE and three.rule == "R1"
