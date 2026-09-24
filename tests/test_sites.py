"""Site construction on REAL BLAST hits (tests/fixtures/real_hits_strands.json)."""

import json
from pathlib import Path

import pytest

from qpcr_assay_check.align import realign
from qpcr_assay_check.config import load_config
from qpcr_assay_check.ncbi.parser import Hit
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.specificity import sites as S

from .conftest import CDC_N1_F, CDC_N1_P, CDC_N1_R

FIX = json.loads((Path(__file__).parent / "fixtures" / "real_hits_strands.json").read_text())[
    "hits"
]
OLIGOS = {"forward": CDC_N1_F, "reverse": CDC_N1_R, "probe": CDC_N1_P}
RULES = load_config().specificity


def cand(name, tier="background"):
    item = FIX[name]
    hit = Hit.model_validate(item["hit"] | {"descriptions": item["hit"]["description"]})
    label = item["label"]
    return S.make_candidate(tier, label, OLIGOS[label], hit, hit.hsps[0], label.split("_v")[0])


def test_minus_strand_convention_matches_the_real_output():
    c = cand("sars2_reverse_minus")
    assert (c.hsp.hit_from, c.hsp.hit_to, c.hsp.hit_strand) == (28340, 28317, "Minus")
    assert c.orientation == "-" and not c.partial
    site = S.site_from_full(c, RULES.primer_site, "S1")
    assert (site.subject_start, site.subject_end) == (28317, 28340)  # forward-strand coordinates
    assert site.source == "blast_full" and site.q_aln == site.s_aln == CDC_N1_R
    assert (site.n_mismatch, site.n_gap, site.clean_3prime_nt, site.level) == (0, 0, 24, "critical")


def test_a_hit_group_can_carry_alignments_on_both_strands():
    item = FIX["sars2_probe_three_hsps"]
    hit = Hit.model_validate(item["hit"] | {"descriptions": item["hit"]["description"]})
    made = [S.make_candidate("target", "probe", CDC_N1_P, hit, h, "probe") for h in hit.hsps]
    assert [c.orientation for c in made] == ["-", "+", "+"]
    starts = [
        S.site_from_full(c, RULES.probe_site, f"S{i}").subject_start for i, c in enumerate(made)
    ]
    assert starts == [65, 28452, 28693]


@pytest.mark.parametrize(
    "name, u5, u3, bound, footprint",
    [
        ("human_forward_partial_minus", 0, 5, 2, (3299, 3318)),
        ("human_reverse_partial_minus", 7, 0, 2, (147651, 147674)),
        ("human_probe_partial_minus", 2, 7, 2 + 0, (665, 681 + 2)),
    ],
)
def test_partial_hits_report_the_unaligned_ends_and_the_expected_footprint(
    name, u5, u3, bound, footprint
):
    c = cand(name)
    assert c.partial and (c.u5, c.u3) == (u5, u3)
    assert c.orientation == "-"
    lo, hi = S.footprint(c)
    assert hi - lo + 1 == c.qlen  # the footprint is exactly as long as the oligo
    if name != "human_probe_partial_minus":
        assert (lo, hi) == footprint
    assert c.lower_bound >= bound - 1


def test_the_lower_bound_follows_from_blast_scoring():
    # 15 aligned + 5 unaligned at the 3' end: BLAST stopped, so >= ceil(5/4) = 2 mismatches remain
    assert cand("human_forward_partial_minus").lower_bound == 2
    # 17 aligned + 7 unaligned at the 5' end
    assert cand("human_reverse_partial_minus").lower_bound == 2


def test_pruning_never_skips_a_hit_that_could_still_matter():
    c = cand("human_forward_partial_minus")
    assert S.can_reach_warning(c, RULES.primer_site)  # bound 2 <= 5: must be fetched
    strict = RULES.primer_site.model_copy(deep=True)
    strict.warning.max_mismatches = 1
    assert not S.can_reach_warning(c, strict)


def test_a_short_unaligned_3prime_tail_rules_out_a_relevant_site_without_fetching():
    """The base after BLAST's alignment must mismatch, so few clean 3' nucleotides can remain."""
    rules = RULES.primer_site  # warning needs at least 3 clean 3' nucleotides
    c = cand("human_forward_partial_minus")  # 5 unaligned 3' bases: up to 4 may be clean
    assert c.u3 == 5 and S.can_reach_warning(c, rules)
    for u3, expected in ((0, True), (1, False), (2, False), (3, False), (4, True), (5, True)):
        c.u3 = u3
        c.hsp = c.hsp.model_copy(update={"query_to": c.qlen - u3})
        assert S.can_reach_warning(c, rules) is expected, u3
    # a 3' end that BLAST aligned completely is not limited by this rule (5' end unaligned)
    reverse = cand("human_reverse_partial_minus")
    assert reverse.u3 == 0 and reverse.u5 == 7 and S.can_reach_warning(reverse, rules)


def test_worst_case_site_is_risk_conservative_and_marked():
    c = cand("human_forward_partial_minus")
    s = S.site_from_bound(c, RULES.primer_site, "S9")
    assert s.source == "blast_partial_worst_case" and s.n_unaligned == 5
    assert s.n_mismatch == 2  # the bound, not the unaligned length
    assert s.clean_3prime_nt == 3  # defects assumed at the innermost unaligned 3' bases
    assert s.s_aln.endswith("....."), "unaligned bases are shown as dots"
    assert (s.subject_start, s.subject_end) == (3299, 3318)
    assert s.level == "warning"


def test_window_is_padded_and_clipped_to_the_record():
    c = cand("human_reverse_partial_minus")
    assert S.window_for(c, 10, 424151) == (147641, 147684)
    c2 = cand("human_probe_partial_minus")  # record is only 962 bp long
    lo, hi = S.window_for(c2, 10, 962)
    assert lo >= 1 and hi <= 962


@pytest.mark.parametrize("orientation", ["+", "-"])
def test_realignment_maps_back_to_forward_strand_coordinates(orientation):
    """A window built around a known insertion must give exactly that insertion's coordinates."""
    oligo = CDC_N1_F
    site_seq = oligo[:6] + "G" + oligo[7:]  # one mismatch inside the site
    left, right = "T" * 14, "C" * 13
    plus_window = (
        left + site_seq + right
        if orientation == "+"
        else left + iupac.reverse_complement(site_seq) + right
    )
    w_lo = 5000
    expected = (w_lo + len(left), w_lo + len(left) + len(oligo) - 1)

    class H:  # minimal stand-in candidate
        pass

    c = cand("human_forward_partial_minus")
    c.oligo = oligo
    c.hsp = c.hsp.model_copy(update={"hit_strand": "Plus" if orientation == "+" else "Minus"})
    oriented = S.oriented_window(plus_window, orientation)
    aln = realign.align_semiglobal(oligo, oriented)
    site = S.site_from_alignment(c, aln, plus_window, w_lo, RULES.primer_site, "S1")
    assert (site.subject_start, site.subject_end) == expected
    assert (site.n_mismatch, site.n_gap, site.source) == (1, 0, "realigned")
    assert site.defect_positions == [7] and site.orientation == orientation


def test_classification_uses_mismatches_gaps_and_the_clean_3prime_end():
    def metrics(defects, length=24):
        return S._metrics(length, set(defects), length - len(defects), len(defects), 0, 0)

    rules = RULES.primer_site
    assert S.classify(metrics([]), rules) == "critical"
    assert S.classify(metrics([3, 9, 15]), rules) == "critical"  # 3 mismatches, 3' end clean
    assert S.classify(metrics([3, 9, 15, 17]), rules) == "warning"  # 4 mismatches
    assert S.classify(metrics([3, 21]), rules) == "warning"  # 3 clean 3' nt: warning, not critical
    assert S.classify(metrics([3, 19]), rules) == "critical"  # 2 mismatches, 5 clean 3' nt
    assert (
        S.classify(metrics([3, 22]), rules) == "minor"
    )  # only 2 clean 3' nt: below the warning limit
    assert S.classify(metrics([3, 24]), rules) == "minor"  # terminal mismatch: 0 clean nt
    assert S.classify(metrics([1, 2, 3, 4, 5, 6]), rules) == "minor"
    gapped = realign.Metrics(24, 22, 0, 2, 0, (5, 9), 15, 0, 0, False)
    assert S.classify(gapped, rules) == "minor"  # warning allows at most one gap


@pytest.mark.parametrize(
    "acc, title, expected",
    [
        ("NG_050601.2", "Homo sapiens ZC3H14, RefSeqGene on chromosome 14", "genomic"),
        ("Z95331.2", "Human DNA sequence from clone CTA-941F9 on chromosome 22q13", "genomic"),
        ("NM_001234.5", "Homo sapiens something (GENE), mRNA", "transcript"),
        ("XR_000123.1", "PREDICTED: Homo sapiens uncharacterized ncRNA", "transcript"),
        ("AB123456.1", "Homo sapiens mRNA for KIAA0000, complete cds", "transcript"),
        ("MW000001.1", "Cloning vector pXYZ", "other"),
        (
            "OX417460.1",
            "Severe acute respiratory syndrome coronavirus 2 genome assembly, chromosome: 1",
            "genomic",
        ),
    ],
)
def test_record_type(acc, title, expected):
    assert S.record_type(acc, title) == expected


def test_roles_come_from_the_assay_s_oligo_names():
    from .conftest import make_assay

    assay = make_assay(probe=[{"name": "P1", "sequence": CDC_N1_P},
                              {"name": "P2", "sequence": CDC_N1_P[::-1]}])  # fmt: skip
    labels = ("forward", "forward_v12", "reverse_v3", "P1", "P2_v2")
    assert [assay.role_of(x) for x in labels] == [
        "forward", "forward", "reverse", "probe", "probe",
    ]  # fmt: skip
