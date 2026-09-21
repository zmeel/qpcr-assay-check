"""Amplicon pairing rules, tested on directly constructed sites."""

from qpcr_assay_check.config import load_config
from qpcr_assay_check.specificity.models import SiteResult
from qpcr_assay_check.specificity.pairing import predict_amplicons, primer_can_prime, probe_binds

from .conftest import make_assay

RULES = load_config().specificity
ASSAY = make_assay()
_n = 0


def mk(
    role, orientation, start, end, level="critical", tier="background", acc="X.1", taxid=1, mm=1
):
    global _n
    _n += 1
    return SiteResult(
        id=f"S{_n}", tier=tier, query=role, role=role, oligo="A" * (end - start + 1),
        accession=acc, taxid=taxid, organism="Org", title="chromosome", orientation=orientation,
        subject_start=start, subject_end=end, source="blast_full", q_aln="A", s_aln="A",
        midline="|", n_match=20, n_mismatch=mm, n_gap=0, n_ambiguous=0, defect_positions=[],
        mismatches_last5=0, mismatches_last3=0, terminal_defect=False, clean_3prime_nt=10,
        level=level,
    )  # fmt: skip


def pair(*sites, rules=RULES):
    return predict_amplicons(list(sites), rules, ASSAY)


def test_forward_on_plus_upstream_of_reverse_on_minus_makes_a_product():
    f, r = mk("forward", "+", 100, 119), mk("reverse", "-", 200, 223)
    amps, used, truncated = pair(f, r)
    (a,) = amps
    assert (a.start, a.end, a.length, a.roles) == (100, 223, 124, "forward/reverse")
    assert used == {f.id, r.id} and not truncated and a.classification == "amplified_not_detected"


def test_the_strands_can_be_swapped_reverse_upstream_on_plus_forward_downstream_on_minus():
    r, f = mk("reverse", "+", 100, 123), mk("forward", "-", 200, 219)
    (a,), _, _ = pair(r, f)
    assert a.roles == "reverse/forward" and a.length == 120


def test_primers_that_face_away_from_each_other_make_no_product():
    minus_first = [mk("reverse", "-", 100, 123), mk("forward", "+", 200, 219)]
    assert pair(*minus_first)[0] == []


def test_two_primers_on_the_same_strand_make_no_product():
    assert pair(mk("forward", "+", 100, 119), mk("reverse", "+", 200, 223))[0] == []


def test_the_same_primer_twice_does_not_pair_with_itself():
    assert pair(mk("forward", "+", 100, 119), mk("forward", "-", 200, 219))[0] == []


def test_sites_on_different_records_or_tiers_do_not_pair():
    assert (
        pair(mk("forward", "+", 100, 119, acc="A.1"), mk("reverse", "-", 200, 223, acc="B.1"))[0]
        == []
    )
    assert (
        pair(mk("forward", "+", 100, 119, tier="near_neighbours"), mk("reverse", "-", 200, 223))[0]
        == []
    )


def test_minor_sites_cannot_prime_and_never_pair():
    f, r = mk("forward", "+", 100, 119, level="minor"), mk("reverse", "-", 200, 223)
    assert not primer_can_prime(f) and pair(f, r)[0] == []


def test_warning_level_primers_can_prime():
    f, r = (
        mk("forward", "+", 100, 119, level="warning"),
        mk("reverse", "-", 200, 223, level="warning"),
    )
    assert len(pair(f, r)[0]) == 1


def test_probe_inside_the_product_makes_it_detectable_and_outside_does_not():
    f, r = mk("forward", "+", 100, 119), mk("reverse", "-", 200, 223)
    inside = mk("probe", "+", 130, 153)
    (a,), _, _ = pair(f, r, inside)
    assert a.classification == "likely_detected" and a.probe_site == inside.id
    outside = mk("probe", "+", 300, 323)
    assert pair(f, r, outside)[0][0].classification == "amplified_not_detected"
    partly = mk("probe", "+", 90, 113)  # sticks out over the forward primer's 5' end
    assert pair(f, r, partly)[0][0].classification == "amplified_not_detected"


def test_probe_on_either_strand_counts():
    f, r = mk("forward", "+", 100, 119), mk("reverse", "-", 200, 223)
    assert pair(f, r, mk("probe", "-", 130, 153))[0][0].classification == "likely_detected"


def test_probe_needs_the_configured_level():
    weak = mk("probe", "+", 130, 153, level="warning")
    assert not probe_binds(weak, RULES)
    lenient = RULES.model_copy(update={"probe_binds_if": "warning"})
    assert probe_binds(weak, lenient)
    f, r = mk("forward", "+", 100, 119), mk("reverse", "-", 200, 223)
    assert pair(f, r, weak)[0][0].classification == "amplified_not_detected"
    assert pair(f, r, weak, rules=lenient)[0][0].classification == "likely_detected"


def test_the_best_probe_site_is_reported():
    f, r = mk("forward", "+", 100, 119), mk("reverse", "-", 200, 223)
    worse, better = mk("probe", "+", 130, 153, mm=3), mk("probe", "+", 150, 173, mm=1)
    assert pair(f, r, worse, better)[0][0].probe_site == better.id


def test_the_size_limit_is_inclusive_and_the_cap_is_reported():
    f, r = mk("forward", "+", 1, 20), mk("reverse", "-", 1977, 2000)
    assert len(pair(f, r)[0]) == 1  # 2000 bp exactly
    assert pair(mk("forward", "+", 1, 20), mk("reverse", "-", 1978, 2001))[0] == []
    capped = RULES.model_copy(update={"max_amplicons": 1})
    sites = [
        mk("forward", "+", 100, 119),
        mk("reverse", "-", 200, 223),
        mk("reverse", "-", 300, 323),
    ]
    amps, _, truncated = pair(*sites, rules=capped)
    assert len(amps) == 1 and truncated


def test_every_forward_reverse_combination_on_a_record_is_reported():
    sites = [
        mk("forward", "+", 100, 119), mk("forward", "+", 400, 419),
        mk("reverse", "-", 500, 523),
    ]  # fmt: skip
    amps, _, _ = pair(*sites)
    assert sorted(a.length for a in amps) == [124, 424]


def test_ids_are_unique_and_output_is_deterministic():
    sites = [
        mk("forward", "+", 100, 119),
        mk("reverse", "-", 200, 223),
        mk("reverse", "-", 250, 273),
    ]
    a1, _, _ = pair(*sites)
    a2, _, _ = pair(*reversed(sites))
    assert [a.id for a in a1] == ["A1", "A2"]
    assert [a.model_dump() for a in a1] == [a.model_dump() for a in a2]


def test_rna_assays_get_a_genomic_dna_remark_for_eukaryotic_genomic_records_only():
    f, r = mk("forward", "+", 100, 119, taxid=9606), mk("reverse", "-", 200, 223, taxid=9606)
    (a,), _, _ = pair(f, r)
    assert "genomic DNA" in a.note
    bact = pair(mk("forward", "+", 100, 119, taxid=562), mk("reverse", "-", 200, 223, taxid=562))[
        0
    ][0]
    assert bact.note == ""
