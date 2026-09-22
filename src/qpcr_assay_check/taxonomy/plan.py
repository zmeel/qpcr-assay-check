"""Resolve the configured organism list into taxonomy IDs ready for the exclusivity tier."""

from __future__ import annotations

import logging

from pydantic import BaseModel

from ..config import Config
from ..ncbi.cache import Cache
from ..ncbi.eutils import Eutils
from .organisms import load_organism_list
from .resolve import Resolution, resolve_names

log = logging.getLogger(__name__)


class OrganismListResolution(BaseModel):
    """Every organism-list name, resolved or not; never a guess for the ones that were not."""

    resolutions: list[Resolution]

    @property
    def taxids(self) -> list[int]:
        """Taxonomy IDs of the names that resolved to exactly one, in list order."""
        return [r.taxid for r in self.resolutions if r.taxid is not None]

    @property
    def unresolved(self) -> list[Resolution]:
        """Names that were ambiguous or not found, for the report."""
        return [r for r in self.resolutions if r.status != "resolved"]


def resolve_organism_list(cfg: Config, eutils: Eutils, cache: Cache) -> OrganismListResolution:
    """Load the configured organism list and resolve every name to a taxonomy ID (cached)."""
    names = load_organism_list(cfg).names
    resolutions = resolve_names(
        eutils,
        cache,
        names,
        ttl_days=cfg.ncbi.taxonomy_cache_ttl_days,
        synonyms=cfg.organisms.resolve_synonyms,
    )
    unresolved = [r.name for r in resolutions if r.status != "resolved"]
    if unresolved:
        log.warning(
            "%d of %d organism-list name(s) did not resolve to exactly one taxonomy ID: %s",
            len(unresolved), len(names), ", ".join(unresolved),
        )  # fmt: skip
    return OrganismListResolution(resolutions=resolutions)
