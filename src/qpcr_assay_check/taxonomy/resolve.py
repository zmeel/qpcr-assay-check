"""Resolve organism names to taxonomy IDs, and turn taxonomy IDs into species/genus/family.

Query format and response shape were checked against the live servers in the v0.2.1 smoke test
(``docs/ARCHITECTURE.md``, "Verified in the first live smoke run"): the term
``f"{name}[Scientific Name]"`` resolved 12 of 13 tried names to exactly one taxonomy ID, and the
Taxonomy EFetch XML (``TaxId``, ``ScientificName``, ``Rank``, ``LineageEx/Taxon``) parsed as
expected. The one miss ("Mycoplasma pneumoniae") is believed to be a scientific-name change (the
genus was moved to *Mycoplasmoides* in 2018), which is exactly what the ``[All Names]`` synonym
fallback here is for. The rank/lineage aggregation into species/genus/family below has not itself
been exercised live and should be checked by the next smoke-test run before this is trusted.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Literal

from pydantic import BaseModel, Field

from ..ncbi.cache import Cache, content_key
from ..ncbi.eutils import Eutils
from ..ncbi.http import NcbiError

log = logging.getLogger(__name__)

ResolutionStatus = Literal["resolved", "ambiguous", "unresolved"]


class Resolution(BaseModel):
    """The outcome of resolving one organism name to a taxonomy ID. Never a guess."""

    name: str
    status: ResolutionStatus
    taxid: int | None = None
    matched_term: str | None = None
    candidates: list[int] = Field(default_factory=list, description="UIDs, when ambiguous")


class Lineage(BaseModel):
    """The parts of a taxon's lineage this tool aggregates hits by."""

    taxid: int
    scientific_name: str
    rank: str
    species: str | None = None
    genus: str | None = None
    family: str | None = None


def resolve_name(
    eutils: Eutils, cache: Cache, name: str, *, ttl_days: float, synonyms: bool
) -> Resolution:
    """Resolve one organism name; cached by the exact name text.

    Tries ``[Scientific Name]`` first, then (if ``synonyms``) ``[All Names]``. Exactly one UID is
    a resolution; more than one is flagged ambiguous; none (after every term) is unresolved.
    Never picks a UID out of an ambiguous result: that would be guessing.
    """
    key = content_key({"kind": "resolve", "name": name})
    cached = cache.get("taxonomy_name", key, ttl_days=ttl_days)
    if cached is not None:
        return Resolution.model_validate_json(cached)
    terms = [f"{name}[Scientific Name]"]
    if synonyms:
        terms.append(f"{name}[All Names]")
    result = Resolution(name=name, status="unresolved")
    for term in terms:
        ids = eutils.esearch_ids("taxonomy", term)
        if len(ids) == 1:
            result = Resolution(name=name, status="resolved", taxid=ids[0], matched_term=term)
            break
        if len(ids) > 1:
            result = Resolution(name=name, status="ambiguous", candidates=ids, matched_term=term)
            break
    cache.put("taxonomy_name", key, result.model_dump_json())
    return result


def resolve_names(
    eutils: Eutils, cache: Cache, names: list[str], *, ttl_days: float, synonyms: bool
) -> list[Resolution]:
    """Resolve every name in ``names``, in order. One ESearch round-trip per uncached name."""
    return [
        resolve_name(eutils, cache, name, ttl_days=ttl_days, synonyms=synonyms) for name in names
    ]


def parse_taxonomy_xml(text: str) -> dict[int, Lineage]:
    """Parse a Taxonomy EFetch (``retmode=xml``) response into one :class:`Lineage` per taxon."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise NcbiError(f"Unparseable Taxonomy EFetch response: {exc}") from exc
    out: dict[int, Lineage] = {}
    for taxon in root.findall("Taxon"):
        taxid_text = taxon.findtext("TaxId")
        name = taxon.findtext("ScientificName")
        if not taxid_text or not name:
            continue
        taxid = int(taxid_text)
        rank = taxon.findtext("Rank") or "no rank"
        by_rank: dict[str, str] = {rank: name}
        for ancestor in taxon.findall("LineageEx/Taxon"):
            r, n = ancestor.findtext("Rank"), ancestor.findtext("ScientificName")
            if r and n:
                by_rank.setdefault(r, n)
        out[taxid] = Lineage(
            taxid=taxid,
            scientific_name=name,
            rank=rank,
            species=by_rank.get("species"),
            genus=by_rank.get("genus"),
            family=by_rank.get("family"),
        )
    return out


def fetch_lineages(
    eutils: Eutils, cache: Cache, taxids: list[int], *, ttl_days: float
) -> dict[int, Lineage]:
    """Lineages for ``taxids``, cached per taxid; one EFetch call for whatever is not cached."""
    out: dict[int, Lineage] = {}
    missing: list[int] = []
    for t in taxids:
        key = content_key({"kind": "lineage", "taxid": t})
        cached = cache.get("taxonomy_lineage", key, ttl_days=ttl_days)
        if cached is not None:
            out[t] = Lineage.model_validate_json(cached)
        else:
            missing.append(t)
    for i in range(0, len(missing), 200):  # keep individual EFetch id lists moderate
        chunk = missing[i : i + 200]
        for t, lin in parse_taxonomy_xml(eutils.fetch_taxonomy(chunk)).items():
            out[t] = lin
            cache.put(
                "taxonomy_lineage", content_key({"kind": "lineage", "taxid": t}),
                lin.model_dump_json(),
            )  # fmt: skip
    return out
