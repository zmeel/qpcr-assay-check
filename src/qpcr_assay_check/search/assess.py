"""Assess raw search results: hit-list saturation and a summary of taxon restriction."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from ..ncbi.parser import QueryResult


class QuerySaturation(BaseModel):
    """Is the hit list for one query complete enough to trust?"""

    label: str
    n_hits: int
    hitlist_size: int
    list_full: bool
    weakest_identity: int | None
    min_relevant_identity: int
    saturated: bool
    note: str


def assess_saturation(q: QueryResult, hitlist_size: int, min_relevant: int) -> QuerySaturation:
    """A full hit list only matters if its weakest hit is still a relevant off-target.

    ``list_full`` alone is not alarming: with a very permissive E-value the tail of the list is
    usually random short matches. It is *saturated* when the list is full **and** even its weakest
    hit has at least ``min_relevant`` identical bases, meaning relevant hits may have been cut off.
    """
    n = len(q.hits)
    full = n >= hitlist_size
    weakest = min((h.best_identity for h in q.hits), default=None)
    saturated = full and weakest is not None and weakest >= min_relevant
    if saturated:
        note = (
            f"Hit list full ({n}) and its weakest hit still has {weakest} identical bases "
            f"(relevance threshold {min_relevant}): relevant hits may be missing. Split the search "
            "into smaller taxon groups."
        )
    elif full:
        note = (
            f"Hit list full ({n}), but its weakest hit has only {weakest} identical bases "
            f"(< {min_relevant}): nothing relevant appears to have been cut off."
        )
    else:
        note = f"{n} hits; the list is not full."
    return QuerySaturation(
        label=q.label,
        n_hits=n,
        hitlist_size=hitlist_size,
        list_full=full,
        weakest_identity=weakest,
        min_relevant_identity=min_relevant,
        saturated=saturated,
        note=note,
    )


class RestrictionSummary(BaseModel):
    """What a taxon-restricted search actually returned.

    Hit taxa can legitimately be *descendants* (strains) of the requested taxa, so membership in
    the requested set is only a partial check; a lineage-based check arrives in v0.4.0. Also,
    ``ENTREZ_QUERY`` filters on the organism *index* of the whole record: in a live human search
    one of 3,715 hits was a "synthetic construct" record that carries a human source feature.
    The restriction is effective, not airtight.
    """

    requested_taxids: list[int]
    n_descriptions: int
    n_without_taxid: int
    n_taxid_in_requested: int
    n_taxid_other: int
    fraction_in_requested: float | None
    top_organisms: list[tuple[str, int]]
    verifiable: bool


def summarise_restriction(
    results: list[QueryResult], requested: list[int], *, top: int = 5
) -> RestrictionSummary:
    """Count hit descriptions by taxon relative to the requested set."""
    wanted = set(requested)
    names: Counter[str] = Counter()
    total = without = inside = other = 0
    for q in results:
        for hit in q.hits:
            for d in hit.descriptions:
                total += 1
                if d.taxid is None:
                    without += 1
                elif d.taxid in wanted:
                    inside += 1
                else:
                    other += 1
                names[d.sciname or "(no organism name)"] += 1
    return RestrictionSummary(
        requested_taxids=sorted(wanted),
        n_descriptions=total,
        n_without_taxid=without,
        n_taxid_in_requested=inside,
        n_taxid_other=other,
        fraction_in_requested=(inside / total) if total else None,
        top_organisms=names.most_common(top),
        verifiable=total > 0 and without < total,
    )
