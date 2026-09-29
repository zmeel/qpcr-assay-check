"""The chain locator (overhaul step 3) on SYNTHETIC genomes: filler around a synthetic fragment
built from the published CDC N1 oligos; no real Legionella or Neisseria sequence is used."""

from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.variants.chain import CopyRule, Reference, is_copy, locate

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .world import filler

AMP = F + filler(30, 11) + P + filler(30, 12) + iupac.reverse_complement(R)
LEFT, RIGHT = filler(300, 21), filler(300, 22)
REF = Reference(AMP)
REF_CTX = Reference(AMP, LEFT, RIGHT)
P_AT = AMP.index(P)


def copies(contigs, refs=(REF,), **kw):
    return [c for c in locate(contigs, list(refs), **kw) if is_copy(c)]


def mutate_every(seq: str, n: int, keep: range = range(0)) -> str:
    """Change every n-th base (outside ``keep``) to another base."""
    swap = {"A": "C", "C": "G", "G": "T", "T": "A"}
    return "".join(swap[b] if i % n == n - 1 and i not in keep else b for i, b in enumerate(seq))


def test_a_plain_copy():
    (c,) = copies({"c1": filler(2000, 1) + AMP + filler(2000, 2)})
    assert (c.strand, c.start, c.end, c.anchored, c.identity) == ("+", 2000, 2000 + len(AMP),
                                                                 len(AMP), 1.0)  # fmt: skip
    assert not c.cut and c.place(P_AT) == 2000 + P_AT
    assert c.forward_span() == (2000, 2000 + len(AMP))
    assert c.region[c.start - c.region_start :][: len(AMP)] == AMP


def test_an_insertion_beyond_the_old_tolerance_is_one_copy_with_both_ends_placed():
    ins = AMP[:40] + filler(60, 5) + AMP[40:]
    (c,) = copies({"c1": filler(2000, 1) + ins + filler(2000, 2)})
    assert c.length_difference == 60 and c.anchored == len(AMP)
    assert c.place(0) == 2000 and c.place(P_AT) == 2000 + P_AT + 60  # the probe after it


def test_the_minus_strand_is_read_in_the_fragment_sense():
    seq = filler(2000, 1) + AMP + filler(1500, 2)
    (c,) = copies({"c1": iupac.reverse_complement(seq)})
    assert c.strand == "-" and c.start == 2000  # on the sense sequence (= seq here)
    assert c.forward_span() == (1500, 1500 + len(AMP))  # on the contig as submitted


def test_a_copy_cut_by_the_contig_start_keeps_its_negative_start():
    (c,) = copies({"c1": AMP[60:] + filler(2000, 3)})
    assert (c.start, c.cut_left, c.cut_right) == (-60, True, False)
    assert c.anchored == len(AMP) - 60


def test_a_single_chance_seed_is_not_a_copy():
    found = locate({"c1": filler(3000, 1) + AMP[40:56] + filler(3000, 2)}, [REF])
    (c,) = found
    assert 16 <= c.anchored < 24 and not is_copy(c)


def test_two_copies_and_the_reference_that_fits_best():
    other = mutate_every(AMP, 9)  # a second lineage: exact blocks of 8 nt only
    genome = {"c1": filler(2000, 1) + AMP + filler(2000, 2) + other + filler(500, 3)}
    found = copies(genome, refs=(REF, Reference(other)))
    assert sorted((c.start, c.ref, c.anchored) for c in found) == [
        (2000, 0, len(AMP)), (4000 + len(AMP), 1, len(AMP))]  # fmt: skip


def test_identity_rule_for_a_divergent_family_member():
    keep = range(P_AT, P_AT + 20)  # one exact 20-nt stretch, every 6th base changed elsewhere
    diverged = mutate_every(AMP, 6, keep)
    (c,) = locate({"c1": filler(2000, 1) + diverged + filler(2000, 2)}, [REF])
    assert c.anchored < 32 and c.identity >= 0.75 and is_copy(c)
    assert not is_copy(c, CopyRule(min_identity=0.95))


def test_conserved_flanks_anchor_a_wholly_divergent_fragment():
    spacer = filler(len(AMP) + 25, 23)  # nothing of the fragment left, 25 nt longer
    genome = {"c1": filler(1000, 1) + LEFT + spacer + RIGHT + filler(1000, 2)}
    assert not copies(genome)  # without context there is nothing to find
    (c,) = copies(genome, refs=(REF_CTX,))
    assert c.anchored == 0 and c.context_left >= 290 and c.context_right >= 290
    assert c.start == 1300 and c.length_difference == 25 and c.identity is None


def test_one_flank_counts_only_with_the_fragment_cut_or_touched():
    # the contig ends 10 nt into the fragment: a copy cut by a contig end
    cut = {"c1": filler(1000, 1) + LEFT + AMP[:10]}
    (c,) = copies(cut, refs=(REF_CTX,))
    assert c.cut_right and c.anchored == 0
    # left flank only, fragment position inside the contig but nothing of it: not a copy
    lone = {"c1": filler(1000, 1) + LEFT + filler(2000, 9)}
    (c,) = locate(lone, [REF_CTX])
    assert c.context_left >= 290 and not is_copy(c)


def test_a_fragment_hidden_by_n_is_found_through_its_flanks():
    genome = {"c1": filler(1000, 1) + LEFT + "N" * len(AMP) + RIGHT + filler(1000, 2)}
    (c,) = copies(genome, refs=(REF_CTX,))
    assert c.n_inside == len(AMP) and c.anchored == 0


def test_n_runs_next_to_a_copy_are_measured():
    (c,) = copies({"c1": filler(1000, 1) + "N" * 40 + AMP + "N" * 7 + filler(1000, 2)})
    assert (c.n_left, c.n_right, c.n_inside) == (40, 7, 0)
