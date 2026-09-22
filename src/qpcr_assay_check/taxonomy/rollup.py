"""Aggregate off-target sites by species, genus and family (SPEC step 6).

One row per distinct taxon that produced at least one off-target site, across every off-target
tier (near neighbours, background, exclusivity) -- not only the exclusivity tier. The report
groups this flat list by whichever rank it needs; this module does not pick one rank over another.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from ..ncbi.cache import Cache
from ..ncbi.eutils import Eutils
from ..specificity.models import SiteResult
from .resolve import fetch_lineages


class TaxonCount(BaseModel):
    """One taxon among the off-target sites, with its lineage and how many sites it produced."""

    taxid: int
    scientific_name: str = ""
    species: str | None = None
    genus: str | None = None
    family: str | None = None
    n_sites: int


def taxonomy_breakdown(
    sites: list[SiteResult], eutils: Eutils, cache: Cache, *, ttl_days: float
) -> list[TaxonCount]:
    """One :class:`TaxonCount` per distinct taxid among ``sites``, most sites first."""
    per_taxid = Counter(s.taxid for s in sites if s.taxid is not None)
    if not per_taxid:
        return []
    lineages = fetch_lineages(eutils, cache, sorted(per_taxid), ttl_days=ttl_days)
    out = [
        TaxonCount(
            taxid=taxid,
            scientific_name=lin.scientific_name if lin else "",
            species=lin.species if lin else None,
            genus=lin.genus if lin else None,
            family=lin.family if lin else None,
            n_sites=n,
        )
        for taxid, n in per_taxid.items()
        for lin in [lineages.get(taxid)]
    ]
    out.sort(key=lambda c: (-c.n_sites, c.scientific_name))
    return out
