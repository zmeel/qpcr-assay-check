"""The taxa of each off-target tier, checked against the target and against each other.

Tiers review 2026-11-20, F2: only ``target.taxa`` used to be checked against the target's
lineage. A near neighbour or an organism-list entry that is an *ancestor* of the target (an
influenza A subtype assay listing "Influenza A virus") searched the target's own records as
off-target; a *descendant* (a genus assay listing one of its species) counted the same genomes as
targets in inclusivity and as off-target products. And a taxon listed in two tiers (the packaged
starter list names *Homo sapiens*, the human background searches 9606) was searched twice.

This module decides, before anything is planned:

* a taxon equal to the target, or inside it, outside ``target.taxa``: refused (InputError), with
  what to do instead. The exclusivity tier's own target row is left out as before;
* an ancestor of the target: searched with ``NOT`` the target (and the plan says so);
* a taxon in two tiers: searched once, in the more specific tier (near neighbours, then out of
  scope, then background, then the organism list), and the plan says so;
* a taxon whose descendants are searched by a more specific tier: searched with ``NOT`` those, so
  their records are assessed once.

Exact duplicates need no lineage and are removed by the planner even without this check (a dry
run plans offline); the lineage rules need NCBI Taxonomy and run before a real search.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from ..errors import InputError
from ..models import Assay

#: Most specific first: a taxon in two tiers is searched in the first of them.
TIER_PRIORITY = ("near_neighbours", "out_of_scope", "background", "exclusivity")


@dataclass
class TierTaxa:
    """What each tier searches: its taxa, the taxa left out of each one's search, and notes."""

    taxa: dict[str, list[int]]
    exclude: dict[int, list[int]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def assay_tier_taxa(
    assay: Assay, background: list[int], exclusivity: list[int] | None
) -> dict[str, list[int]]:
    """The taxa each tier would search, straight from the assay and configuration."""
    must_not = assay.target.must_not_detect_taxids
    near = sorted(set(assay.near_neighbour_taxids) | set(assay.exclusion_taxids) | set(must_not))
    return {
        "near_neighbours": near,
        "out_of_scope": sorted(set(assay.target.out_of_scope_taxids)),
        "background": sorted(set(background)),
        "exclusivity": sorted(set(exclusivity or [])),
    }


def dedupe(taxa: dict[str, list[int]]) -> tuple[dict[str, list[int]], list[str]]:
    """Each taxon in the most specific tier that lists it; a note per taxon moved."""
    seen: dict[int, str] = {}
    out: dict[str, list[int]] = {}
    notes: list[str] = []
    for tier in TIER_PRIORITY:
        keep = []
        for t in taxa.get(tier, []):
            if t in seen:
                notes.append(
                    f"Taxon {t} is listed for the {seen[t]} and the {tier} tier: searched once, "
                    f"in the {seen[t]} tier."
                )
            else:
                seen[t] = tier
                keep.append(t)
        out[tier] = keep
    return out, notes


def check_tier_taxa(
    assay: Assay,
    taxa: dict[str, list[int]],
    ancestors_of: Callable[[list[int]], dict[int, set[int]]],
    names: dict[int, str] | None = None,
) -> TierTaxa:
    """Apply the lineage rules (module docstring) to deduplicated tier taxa.

    ``ancestors_of``: NCBI ancestors of taxa, each taxon itself included
    (``taxonomy.resolve.ancestors``). ``names``: organism names for the messages (the
    organism list's own spelling), where known.
    """
    names = names or {}
    target = assay.target.taxid
    inside_ok = set(assay.target.excluded_taxids)  # target.taxa: inside the target by design
    every = sorted({t for ts in taxa.values() for t in ts} | ({target} if target else set()))
    anc = ancestors_of(every) if every else {}

    def label(t: int) -> str:
        return f"{names[t]} ({t})" if t in names else f"taxon {t}"

    def lineage(t: int) -> set[int]:
        return anc.get(t, set()) | {t}

    refused: list[str] = []
    exclude: dict[int, list[int]] = {}
    notes: list[str] = []
    out = {tier: list(ts) for tier, ts in taxa.items()}
    if target is not None:
        target_line = lineage(target)
        for tier in ("near_neighbours", "background", "exclusivity"):
            for t in list(out.get(tier, [])):
                if t in inside_ok:
                    continue
                if t == target:
                    refused.append(f"{label(t)} in the {tier} tier is the target itself")
                elif target in lineage(t):
                    refused.append(f"{label(t)} in the {tier} tier lies inside the target {target}")
                elif t in target_line:
                    exclude.setdefault(t, []).append(target)
                    notes.append(
                        f"{label(t)} ({tier} tier) contains the target {target}: searched without "
                        "the target's own records (NOT the target)."
                    )
    if refused:
        raise InputError(
            "Off-target taxa must lie outside the target: "
            + "; ".join(refused)
            + ". Put a taxon inside the target that the assay must not detect (or that is "
            "out of scope) in target.taxa with its role, remove it from the organism list or "
            "the near neighbours, or give the assay its own exclusivity_organisms."
        )
    # a taxon whose descendants a more specific tier searches: leave those out of its search
    for i, tier in enumerate(TIER_PRIORITY):
        earlier = [t for prior in TIER_PRIORITY[:i] for t in out.get(prior, [])]
        for t in out.get(tier, []):
            below = [b for b in earlier if b != t and t in lineage(b)]
            if below:
                exclude.setdefault(t, []).extend(below)
                notes.append(
                    f"{label(t)} ({tier} tier) contains "
                    + ", ".join(label(b) for b in below)
                    + ", searched in a more specific tier: left out of this search."
                )
    return TierTaxa(taxa=out, exclude={t: sorted(set(x)) for t, x in exclude.items()}, notes=notes)
