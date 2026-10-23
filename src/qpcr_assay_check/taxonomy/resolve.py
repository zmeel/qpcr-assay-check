"""Resolve organism names to taxonomy IDs, and turn taxonomy IDs into species/genus/family.

Query format and response shape were checked against the live servers in the v0.2.1 smoke test
(``docs/ARCHITECTURE.md``, "Verified in the first live smoke run"): the term
``f"{name}[Scientific Name]"`` resolved 12 of 13 tried names to exactly one taxonomy ID, and the
Taxonomy EFetch XML (``TaxId``, ``ScientificName``, ``Rank``, ``LineageEx/Taxon``) parsed as
expected. The rank/lineage aggregation into species/genus/family was checked live in the v0.4.0
phase 4a smoke test (2026-09-22): 5/5 sampled lineages came back with a populated genus and family.

The one miss ("Mycoplasma pneumoniae") is believed to be a scientific-name change (the genus was
moved to *Mycoplasmoides* in 2018) -- **but the live smoke test confirmed the ``[All Names]``
synonym fallback does NOT catch it** (both terms returned zero hits): NCBI's ``[All Names]`` index
does not appear to carry the old genus as a synonym for this species. The fallback is kept because
it does help other cases (unverified which), but a genus-level rename like this one still needs the
organism list updated with the current name directly (see ``data/clinical_organisms.yaml``).
"""

from __future__ import annotations

import json
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


def _taxa_root(text: str) -> ET.Element:
    """A Taxonomy EFetch response as XML; a truncated or garbled one is an :class:`NcbiError`,
    so every caller's network-error handling covers it (a raw ``ParseError`` aborted a run)."""
    try:
        return ET.fromstring(text)
    except ET.ParseError as exc:
        raise NcbiError(f"Unparseable Taxonomy EFetch response: {exc}") from exc


def _lineages_of(root: ET.Element) -> dict[int, Lineage]:
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


def _ancestors_of(root: ET.Element) -> dict[int, set[int]]:
    out: dict[int, set[int]] = {}
    for taxon in root.findall("Taxon"):
        tid = int(taxon.findtext("TaxId") or 0)
        out[tid] = {int(x.findtext("TaxId") or 0) for x in taxon.iterfind("LineageEx/Taxon")}
    return out


def parse_taxonomy_xml(text: str) -> dict[int, Lineage]:
    """Parse a Taxonomy EFetch (``retmode=xml``) response into one :class:`Lineage` per taxon."""
    return _lineages_of(_taxa_root(text))


def _lineage_key(taxid: int) -> str:
    return content_key({"kind": "lineage", "taxid": taxid})


def _ancestors_key(taxid: int) -> str:
    return content_key({"ancestors": taxid})


def _fetch_taxa(
    eutils: Eutils, cache: Cache, taxids: list[int]
) -> tuple[dict[int, set[int]], dict[int, Lineage]]:
    """EFetch ``taxids`` (200 per request) and cache what each response says both ways, as
    ancestors and as a lineage: the specificity tiers ask for the one and the taxonomy summary
    for the other, about the same organisms, so each is fetched once."""
    anc: dict[int, set[int]] = {}
    lin: dict[int, Lineage] = {}
    for i in range(0, len(taxids), 200):  # keep individual EFetch id lists moderate
        root = _taxa_root(eutils.fetch_taxonomy(taxids[i : i + 200]))
        for tid, ids in _ancestors_of(root).items():
            anc[tid] = ids | {tid}
            cache.put("taxonomy_ancestors", _ancestors_key(tid), json.dumps(sorted(ids)))
        for tid, lineage in _lineages_of(root).items():
            lin[tid] = lineage
            cache.put("taxonomy_lineage", _lineage_key(tid), lineage.model_dump_json())
    return anc, lin


def fetch_lineages(
    eutils: Eutils, cache: Cache, taxids: list[int], *, ttl_days: float
) -> dict[int, Lineage]:
    """Lineages for ``taxids``, cached per taxid; one EFetch call for whatever is not cached."""
    out: dict[int, Lineage] = {}
    missing: list[int] = []
    for t in taxids:
        cached = cache.get("taxonomy_lineage", _lineage_key(t), ttl_days=ttl_days)
        if cached is not None:
            out[t] = Lineage.model_validate_json(cached)
        else:
            missing.append(t)
    if missing:
        out.update(_fetch_taxa(eutils, cache, missing)[1])
    return out


def ancestors(
    eutils: Eutils, cache: Cache, taxids: list[int], *, ttl_days: float
) -> dict[int, set[int]]:
    """Every taxon's NCBI ancestors, itself included (``LineageEx``), cached per taxon."""
    out: dict[int, set[int]] = {}
    missing: list[int] = []
    for t in taxids:
        cached = cache.get("taxonomy_ancestors", _ancestors_key(t), ttl_days=ttl_days)
        if cached is None:
            missing.append(t)
        else:
            out[t] = set(json.loads(cached)) | {t}
    if missing:
        out.update(_fetch_taxa(eutils, cache, missing)[0])
    return out


def outside_target(
    eutils: Eutils, cache: Cache, target: int, taxids: list[int], *, ttl_days: float
) -> list[int]:
    """The taxa in ``taxids`` that are not descendants of ``target`` (by their NCBI lineage).

    Used for ``target.exclude_taxids``: excluding an ancestor or an unrelated taxon would empty
    the target search or search the target itself as an off-target tier. Cached per taxon.
    """
    anc = ancestors(eutils, cache, taxids, ttl_days=ttl_days)
    return [t for t in taxids if target not in anc.get(t, set()) - {t}]
