"""Condensed report tables: off-target products and sites per tier and species.

Every product and site stays in the workbook and hits.tsv; the HTML shows one row per tier and
species, most concerning first (must-not-detect tiers before background, out of scope last),
with the counts it summarises. Advice of the advisor subagent (2026-09-25): state the
denominator on every row and never hide a WARN or FAIL in a collapsed block.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..specificity.models import AmpliconResult, SiteResult

TIER_ORDER = {"near_neighbours": 0, "exclusivity": 1, "background": 2, "out_of_scope": 9}


def species_of(taxonomy_breakdown: list) -> dict[int, str]:
    """taxid -> species (or the taxon's own name when the species is not known)."""
    return {t.taxid: t.species or t.scientific_name for t in taxonomy_breakdown if t.taxid}


def _name(taxid: int | None, organism: str | None, species: dict[int, str]) -> str:
    return (species.get(taxid) if taxid else None) or organism or "unknown organism"


@dataclass
class ProductGroup:
    tier: str
    species: str
    n_products: int = 0
    records: set[str] = field(default_factory=set)
    n_detected: int = 0  # the probe binds inside the product
    best_mismatches: int = 99
    best: AmpliconResult | None = None
    lengths: list[int] = field(default_factory=list)
    pairs: Counter = field(default_factory=Counter)
    names: Counter = field(default_factory=Counter)

    @property
    def n_records(self) -> int:
        return len(self.records)

    @property
    def length_range(self) -> str:
        lo, hi = min(self.lengths), max(self.lengths)
        return f"{lo} bp" if lo == hi else f"{lo}-{hi} bp"


def group_products(
    amplicons: list[AmpliconResult], sites: dict[str, SiteResult], species: dict[int, str]
) -> list[ProductGroup]:
    """One row per tier and species; identical products (same record, coordinates and primer
    pair, e.g. once per variant of a degenerate primer) are counted once."""
    groups: dict[tuple[str, str], ProductGroup] = {}
    seen: set[tuple[str, int, int, str, str]] = set()
    for a in amplicons:
        key = (a.accession, a.start, a.end, a.roles, a.tier)
        if key in seen:
            continue
        seen.add(key)
        name = _name(a.taxid, a.organism, species)
        g = groups.setdefault((a.tier, name), ProductGroup(a.tier, name))
        g.n_products += 1
        g.records.add(a.accession)
        g.n_detected += a.classification == "likely_detected"
        g.lengths.append(a.length)
        g.pairs[a.roles] += 1
        g.names[a.organism or name] += 1
        left, right = sites.get(a.left_site), sites.get(a.right_site)
        mm = (left.n_mismatch + left.n_gap if left else 9) + (
            right.n_mismatch + right.n_gap if right else 9
        )
        better = mm < g.best_mismatches or (
            mm == g.best_mismatches and a.classification == "likely_detected"
        )
        if g.best is None or better:
            g.best, g.best_mismatches = a, mm
    return sorted(
        groups.values(),
        key=lambda g: (TIER_ORDER.get(g.tier, 5), g.n_detected == 0, g.best_mismatches,
                       -g.n_records, g.species),
    )  # fmt: skip


@dataclass
class SiteGroup:
    tier: str
    species: str
    n_sites: int = 0
    records: set[str] = field(default_factory=set)
    levels: Counter = field(default_factory=Counter)
    best: SiteResult | None = None
    names: Counter = field(default_factory=Counter)

    @property
    def n_records(self) -> int:
        return len(self.records)


def _closeness(s: SiteResult) -> tuple[int, int]:
    return (s.n_mismatch + s.n_gap, -s.clean_3prime_nt)


def group_sites(sites: list[SiteResult], species: dict[int, str]) -> list[SiteGroup]:
    """Off-target sites (warning or critical) per tier and species, closest first."""
    groups: dict[tuple[str, str], SiteGroup] = {}
    for s in sites:
        if s.level == "minor":
            continue
        name = _name(s.taxid, s.organism, species)
        g = groups.setdefault((s.tier, name), SiteGroup(s.tier, name))
        g.n_sites += 1
        g.records.add(s.accession)
        g.levels[s.level] += 1
        g.names[s.organism or name] += 1
        if g.best is None or _closeness(s) < _closeness(g.best):
            g.best = s
    return sorted(
        groups.values(),
        key=lambda g: (TIER_ORDER.get(g.tier, 5), g.levels["critical"] == 0,
                       _closeness(g.best) if g.best else (99, 0), -g.n_sites, g.species),
    )  # fmt: skip
