"""Condensed report tables: off-target products and sites per tier and species.

Every product and site stays in the workbook and hits.tsv; the HTML shows one row per tier and
species, most concerning first (must-not-detect tiers before background, out of scope last),
with the counts it summarises. Advice of the advisor subagent (2026-09-25): state the
denominator on every row and never hide a WARN or FAIL in a collapsed block. Rows that can
fail the verdict (must-not-detect tiers, products the probe would detect, critical sites) are
always shown; only the remaining rows beyond a fixed number go to the workbook.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from ..oligo.grade import (
    DETECTABLE,
    FAILURE,
    INDETERMINATE,
    UNDETERMINED_RULES,
    pair_fails,
)
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

    @property
    def n_critical(self) -> int:
        return self.levels["critical"]


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


def shown_rows(groups: list[Any], flagged: str, limit: int) -> tuple[list[Any], int]:
    """The judged rows (out of scope excluded) to show and how many more are in the workbook:
    near-neighbour rows and rows whose ``flagged`` count is non-zero always, then the others up
    to ``limit``; the order of ``groups`` is kept."""
    judged = [g for g in groups if g.tier != "out_of_scope"]
    keep = {id(g) for g in judged if g.tier == "near_neighbours" or getattr(g, flagged)}
    rest = [g for g in judged if id(g) not in keep]
    keep |= {id(g) for g in rest[:limit]}
    return [g for g in judged if id(g) in keep], max(0, len(rest) - limit)


# ---------------------------------------------------------------- whole-fragment combinations
OUTCOMES = ("likely failure", "at risk", "undetermined", "detectable")  # most concerning first
_ORDER = (*OUTCOMES, "")  # "": sites without a class (not graded), listed after the rest


def fragment_outcome(f: Any, bulges: bool = False) -> tuple[str, bool]:
    """The genome-level outcome of one forward/probe/reverse combination, as the variant
    analysis judges a copy (docs/MISMATCH_CLASSES.md), and whether the primer-pair rule decides
    it. Rows made before the classes (no grade) get ''."""
    sites = (f.forward, f.probe, f.reverse)
    if any(s.grade is None for s in sites):
        return "", False
    pair = pair_fails(f.forward.n_mismatch, f.reverse.n_mismatch)

    def state(s: Any) -> str:
        if s.grade in DETECTABLE:
            return "detectable"
        if s.grade == INDETERMINATE:
            if s.note:  # homopolymer bulge: its own setting
                return "detectable" if bulges and s.n_mismatch == 0 else "at risk"
            if s.grade_rule in UNDETERMINED_RULES:
                return "undetermined"
            return "at risk"  # an unexplained gap: not detected, no published size
        return "likely failure" if s.grade == FAILURE else "at risk"

    states = [state(s) for s in sites]
    if pair:
        states.append("likely failure")
    return min(states, key=OUTCOMES.index), pair and not any(
        s == "likely failure" for s in states[:3]
    )


@dataclass
class FragmentView:
    total: int
    records: Counter  # outcome -> records
    attention: list[tuple[Any, str, bool]]  # (row, outcome, decided by the pair rule)
    # per outcome: its 3 main types (name, records), combinations, records, number of types
    attention_grouped: list[tuple[str, list[tuple[str, int]], int, int, int]]
    detectable_top: list[tuple[Any, str, bool]]
    detectable_rest: int  # combinations
    detectable_rest_records: int
    detectable_rest_types: list[tuple[str, int]]


def fragment_view(
    fragments: list[Any], total: int, bulges: bool = False, *, top: int = 10, cap: int = 30,
    per_outcome: int = 5,
) -> FragmentView:
    """Part A (needs attention: every combination that is not detectable) and Part B
    (detectable: the ``top`` most frequent, the rest in one summary row); advisor subagent,
    2026-09-25.

    Part A lists up to ``cap`` combinations: the ``per_outcome`` most frequent of each outcome,
    then the most frequent of the rest, so a problem in hundreds of genomes is never pushed out
    by single-genome failures (user, 2026-09-25). Listed rows are shown worst outcome first; the
    others are one row per outcome with their main types. Combinations without a class (sites
    not graded) are never shown as detectable: they go to Part A as "not classified"."""
    rows = [(f, *fragment_outcome(f, bulges)) for f in fragments]
    records: Counter = Counter()
    for f, outcome, _pair in rows:
        records[outcome or "not classified"] += f.count
    by_count = sorted([r for r in rows if r[1] != "detectable"], key=lambda r: -r[0].count)
    chosen: list[int] = []
    for outcome in _ORDER:
        chosen += [id(r) for r in by_count if r[1] == outcome][:per_outcome]
    chosen = chosen[:cap]
    chosen += [id(r) for r in by_count if id(r) not in set(chosen)][: cap - len(chosen)]
    keep = set(chosen)
    attention = sorted(
        [r for r in by_count if id(r) in keep], key=lambda r: (_ORDER.index(r[1]), -r[0].count)
    )
    n_combos: Counter = Counter()
    n_records: Counter = Counter()
    kinds: dict[str, Counter] = defaultdict(Counter)
    for r in by_count:
        if id(r) in keep:
            continue
        f, outcome, _pair = r
        n_combos[outcome] += 1
        n_records[outcome] += f.count
        kinds[outcome].update(dict(f.organisms) if f.organisms else {"unknown": f.count})
    detectable = sorted([r for r in rows if r[1] == "detectable"], key=lambda r: -r[0].count)
    rest = detectable[top:]
    types: Counter = Counter()
    for f, _o, _p in rest:
        types.update(dict(f.organisms))
    return FragmentView(
        total=total,
        records=records,
        attention=attention,
        attention_grouped=[
            (o, kinds[o].most_common(3), n_combos[o], n_records[o], len(kinds[o]))
            for o in sorted(n_combos, key=_ORDER.index)
        ],
        detectable_top=detectable[:top],
        detectable_rest=len(rest),
        detectable_rest_records=sum(f.count for f, _o, _p in rest),
        detectable_rest_types=types.most_common(5),
    )  # fmt: skip
