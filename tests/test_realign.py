"""Tests for the full-length re-alignment core (align/realign.py)."""

import pytest

from qpcr_assay_check.align import realign
from qpcr_assay_check.oligo import iupac

F = "GACCCCAAAATCAGCGAAAT"


def align(subject):
    a = realign.align_semiglobal(F, subject)
    return a, realign.measure(a.q_aln, a.s_aln)


def test_perfect_match_is_found_inside_flanks():
    a, m = align("TTTTTTTTTT" + F + "GGGGGGGGGG")
    assert (a.s_start, a.s_end) == (10, 30) and a.q_aln == a.s_aln == F
    assert (m.n_mismatch, m.n_gap, m.clean_3prime_nt) == (0, 0, 20)


def test_internal_mismatch_is_located_and_the_3prime_end_stays_clean():
    a, m = align("CCCCCCCCCC" + F[:9] + "G" + F[10:] + "TTTTTTTTTT")
    assert m.n_mismatch == 1 and m.defect_positions == (10,)
    assert m.clean_3prime_nt == 10 and m.mismatches_last5 == 0 and not m.terminal_defect


def test_3prime_terminal_mismatch_is_flagged():
    _, m = align("CCCCCCCCCC" + F[:-1] + "C" + "TTTTTTTTTT")
    assert m.defect_positions == (20,) and m.terminal_defect and m.clean_3prime_nt == 0
    assert m.mismatches_last3 == 1 and m.mismatches_last5 == 1


def test_a_single_base_insertion_in_the_subject_is_a_gap_not_a_shifted_run_of_mismatches():
    a, m = align("CCCCCCCCCC" + F[:13] + "G" + F[13:] + "TTTTTTTTTT")
    assert m.n_gap == 1 and m.n_mismatch == 0
    assert "-" in a.q_aln and a.s_aln.replace("-", "") == F[:13] + "G" + F[13:]


def test_a_deletion_in_the_subject_leaves_the_oligo_base_unpaired():
    _, m = align("CCCCCCCCCC" + F[:6] + F[7:] + "TTTTTTTTTT")
    assert m.n_gap == 1 and m.n_mismatch == 0 and m.defect_positions == (7,)


def test_ambiguity_codes_in_the_subject_match_when_compatible_and_are_counted():
    _, m = align("CCCCCCCCCC" + F[:5] + "S" + F[6:] + "TTTTTTTTTT")  # S = C/G, oligo has C
    assert m.n_mismatch == 0 and m.n_ambiguous == 1
    _, bad = align(
        "CCCCCCCCCC" + F[:6] + "W" + F[7:] + "TTTTTTTTTT"
    )  # W = A/T, oligo has A? pos7=A
    assert bad.n_mismatch == 0
    _, worse = align("CCCCCCCCCC" + F[:2] + "R" + F[3:] + "TTTTTTTTTT")  # R = A/G, oligo has C
    assert worse.n_mismatch == 1


def test_unknown_characters_in_the_subject_become_N():
    assert realign.sanitise_subject("acgt*x-") == "ACGTNNN"


def test_window_shorter_than_the_oligo_still_aligns_the_whole_oligo_with_gaps():
    a = realign.align_semiglobal(F, F[:14])
    m = realign.measure(a.q_aln, a.s_aln)
    assert m.oligo_length == 20 and m.n_gap == 6 and m.terminal_defect


def test_measure_and_midline_agree_and_reject_unequal_strings():
    q, s = "ACGTA", "ACCTA"
    assert realign.midline(q, s) == "|| ||" and realign.measure(q, s).n_mismatch == 1
    with pytest.raises(ValueError):
        realign.measure("ACG", "AC")


def test_alignment_is_deterministic_and_prefers_the_leftmost_of_equal_sites():
    subject = F + "TTTT" + F
    first = realign.align_semiglobal(F, subject)
    assert first == realign.align_semiglobal(F, subject) and first.s_start == 0


def test_reverse_complement_subjects_can_be_read_in_oligo_orientation():
    rc = iupac.reverse_complement("AAAA" + F + "CCCC")
    oriented = iupac.reverse_complement(rc)
    a = realign.align_semiglobal(F, oriented)
    assert (a.s_start, a.s_end) == (4, 24)
