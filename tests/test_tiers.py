"""The taxa of the off-target tiers against the target and each other (tiers review 2026-11-20,
F2) and how a tier is split into searches (F6)."""

import pytest

from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import InputError
from qpcr_assay_check.search.planner import _chunks, plan_searches
from qpcr_assay_check.search.tiers import assay_tier_taxa, check_tier_taxa, dedupe

from .conftest import make_assay

TARGET, GENUS, SIBLING, SPECIES_IN_TARGET, HUMAN = 2697049, 500, 501, 600, 9606
# NCBI ancestors, each taxon itself included: TARGET and SIBLING are species of GENUS;
# SPECIES_IN_TARGET lies below the target
PARENTS = {
    TARGET: {GENUS, 1}, SIBLING: {GENUS, 1}, GENUS: {1}, SPECIES_IN_TARGET: {TARGET, GENUS, 1}
}  # fmt: skip


def ancestors_of(taxids):
    return {t: {t, *PARENTS.get(t, {1})} for t in taxids}


def test_a_taxon_in_two_tiers_is_searched_once_in_the_more_specific_tier():
    assay = make_assay(near_neighbour_taxids=[SIBLING])
    taxa, notes = dedupe(assay_tier_taxa(assay, [HUMAN], [HUMAN, SIBLING, 777]))
    assert taxa["near_neighbours"] == [SIBLING] and taxa["background"] == [HUMAN]
    assert taxa["exclusivity"] == [777]
    assert len(notes) == 2 and any("searched once, in the background tier" in n for n in notes)
    # the planner does the same offline (a dry run): human is not searched twice
    plan = plan_searches(assay, load_config(), exclusivity_taxids=[HUMAN, SIBLING, 777])
    by_tier = {ps.tier: ps.taxids for ps in plan.searches}
    assert by_tier["exclusivity"] == [777] and by_tier["background"] == [HUMAN]


def test_an_ancestor_of_the_target_is_searched_without_the_target():
    assay = make_assay(near_neighbour_taxids=[GENUS])
    checked = check_tier_taxa(assay, {"near_neighbours": [GENUS]}, ancestors_of)
    assert checked.exclude == {GENUS: [TARGET]}
    assert any("contains the target" in n for n in checked.notes)
    plan = plan_searches(assay, load_config(), exclusivity_taxids=[], tier_taxa=checked)
    (near,) = [ps for ps in plan.searches if ps.tier == "near_neighbours"]
    assert near.entrez_query == f"(txid{GENUS}[ORGN] NOT (txid{TARGET}[ORGN]))"


@pytest.mark.parametrize("tier", ["near_neighbours", "exclusivity"])
def test_a_taxon_inside_the_target_or_the_target_itself_is_refused(tier):
    assay = make_assay()
    for taxon in (SPECIES_IN_TARGET, TARGET):
        with pytest.raises(InputError, match="target.taxa"):
            check_tier_taxa(assay, {tier: [taxon]}, ancestors_of, {taxon: "Some virus"})


def test_a_taxon_inside_the_target_is_fine_in_target_taxa():
    assay = make_assay(
        target={"taxid": TARGET, "taxa": [{"taxid": SPECIES_IN_TARGET, "reason": "must not"}]}
    )
    taxa, _ = dedupe(assay_tier_taxa(assay, [HUMAN], [SPECIES_IN_TARGET]))
    checked = check_tier_taxa(assay, taxa, ancestors_of)
    assert checked.taxa["near_neighbours"] == [SPECIES_IN_TARGET]
    assert checked.taxa["exclusivity"] == []


def test_descendants_searched_by_a_more_specific_tier_are_left_out_of_a_wider_search():
    assay = make_assay(near_neighbour_taxids=[SIBLING])
    taxa, _ = dedupe(assay_tier_taxa(assay, [HUMAN], [GENUS]))
    checked = check_tier_taxa(assay, taxa, ancestors_of)
    assert checked.exclude == {GENUS: sorted([TARGET, SIBLING])}


def test_a_tier_is_split_into_balanced_searches():
    assert [len(c) for c in _chunks(list(range(23)), 20)] == [12, 11]
    assert [len(c) for c in _chunks(list(range(40)), 20)] == [20, 20]
    assert [len(c) for c in _chunks(list(range(41)), 20)] == [14, 14, 13]
    assert _chunks([], 20) == [] and _chunks([5], 20) == [[5]]
    assert sum(_chunks(list(range(23)), 20), []) == list(range(23))
