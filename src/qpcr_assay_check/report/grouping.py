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

from ..oligo import iupac
from ..oligo.grade import OUTCOMES, combination_outcome
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
_ORDER = (*OUTCOMES, "")  # "": sites without a class (not graded), listed after the rest


def fragment_outcome(f: Any, bulges: bool = False) -> tuple[str, bool]:
    """The genome-level outcome of one forward/probe/reverse combination
    (``oligo.grade.combination_outcome``) and whether the primer-pair rule decides it."""
    return combination_outcome(f.forward, f.probe, f.reverse, bulges)


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


# ---------------------------------------------------------------- compact per-oligo variants
_CLASS_ORDER = {"likely_failure": 0, "at_risk": 1, "indeterminate": 2, None: 3, "tolerated": 4}
_COMP = {"A": "T", "C": "G", "G": "C", "T": "A"}


def site_changes(row: Any) -> str:
    """The differences of a site from its oligo, short: position from the 3' end and the type
    primer-template (as in the class notes, Stadhouders' convention), e.g. "-3 C-A, -12 G-T".
    Degenerate or ambiguous bases are written oligo/site; runs of inserted or deleted bases are
    written once ("2-base insertion between -11 and -10", "-12 to -11 deleted")."""
    q, s = row.q_aln.upper(), row.s_aln.upper()
    length = sum(c != "-" for c in q)
    pos = 0
    out: list[str] = []
    ins = 0  # bases inserted in the genome since the last oligo base
    deleted: list[int] = []  # consecutive oligo positions without a genome base

    def flush() -> None:
        nonlocal ins
        if ins:
            where = f"between -{length - pos + 1} and -{length - pos}"
            out.append(f"insertion {where}" if ins == 1 else f"{ins}-base insertion {where}")
            ins = 0
        if deleted:
            n = len(deleted)
            span = f"-{deleted[0]}" if n == 1 else f"-{deleted[0]} to -{deleted[-1]}"
            out.append(f"{span} deleted" + (f" ({n} bases)" if n > 1 else ""))
            deleted.clear()

    for qc, sc in zip(q, s, strict=True):
        if qc == "-":
            if deleted:
                flush()
            ins += 1
            continue
        if ins:
            flush()
        pos += 1
        at = length - pos + 1
        if sc == "-":
            deleted.append(at)
            continue
        if deleted:
            flush()
        if sc == ".":
            out.append(f"-{at} unaligned")
        elif qc in _COMP and sc in _COMP:
            if qc != sc:
                out.append(f"-{at} {qc}-{_COMP[sc]}")
        elif not iupac.compatible(qc, sc):
            out.append(f"-{at} {qc}/{sc}")
    flush()
    return ", ".join(out) or "none"


def _perfect(row: Any) -> bool:
    return row.grade == "perfect" or (row.grade is None and not row.n_mismatch and not row.n_gap)


@dataclass
class OligoView:
    role: str
    total: int
    n_perfect: int
    rows: list[Any]  # listed variants
    lumped: int  # tolerated variants in the summary row
    lumped_records: int
    # variants that are not tolerated but seen in a single record: one row per class, with
    # (class, variants, their most frequent organisms)
    singles: list[tuple[str | None, int, list[tuple[str, int]]]] = field(default_factory=list)


def oligo_view(o: Any, *, top_tolerated: int = 5, min_records: int = 2) -> OligoView:
    """Advisor subagent, 2026-09-25: the whole-fragment table is the main view; per oligo only
    the variants that are not perfect, worst class first, then by records. Variants at risk,
    likely to fail, indeterminate or without a class are listed when seen in at least
    ``min_records`` records; those seen once are one row per class (user, 2026-09-25: most of
    them occur in one record). Tolerated variants: the ``top_tolerated`` most frequent, the rest
    in one summary row. Every variant stays in the workbook."""
    other = sorted(
        [r for r in o.rows if not _perfect(r)],
        key=lambda r: (_CLASS_ORDER.get(r.grade, 3), -r.count),
    )
    tolerated = [r for r in other if r.grade == "tolerated"]
    lumped = tolerated[top_tolerated:]
    single = [r for r in other if r.grade != "tolerated" and r.count < min_records]
    classes: dict[str | None, list[Any]] = defaultdict(list)
    for r in single:
        classes[r.grade].append(r)
    singles = []
    for grade, rs in sorted(classes.items(), key=lambda x: _CLASS_ORDER.get(x[0], 3)):
        orgs: Counter = Counter(r.example_organism or "unknown organism" for r in rs)
        singles.append((grade, len(rs), orgs.most_common(3)))
    skip = {id(r) for r in (*lumped, *single)}
    return OligoView(
        role=o.role,
        total=o.total_measured,
        n_perfect=sum(r.count for r in o.rows if _perfect(r)),
        rows=[r for r in other if id(r) not in skip],
        lumped=len(lumped),
        lumped_records=sum(r.count for r in lumped),
        singles=singles,
    )


def site_frequency(oligos: list[Any]) -> dict[tuple[str, str, str], float]:
    """(role, oligo alignment, site alignment) -> % of that oligo's records with this variant,
    for the frequency next to each site in the whole-fragment table."""
    return {(o.role, r.q_aln, r.s_aln): r.percent for o in oligos for r in o.rows}


# ---------------------------------------------------------------- specificity at a glance
TIER_TITLE = {"near_neighbours": "Near neighbours", "exclusivity": "Clinical organism list",
              "background": "Background", "out_of_scope": "Out of scope"}  # fmt: skip
_ROLES = ("forward", "reverse", "probe")


@dataclass
class TierOverview:
    tier: str
    title: str
    n_taxa: int
    products: int
    detected: int  # products the probe would detect
    closest: dict[str, Any]  # role -> closest site in the tier (None if no site)
    by_design: list[str]  # roles with a perfect site in the tier
    discriminating: list[str]  # primer roles without a perfect site
    incomplete: list[str]  # oligos whose hits were cut (cap) or whose hit list was full
    discriminating_complete: bool = True  # none of the incomplete oligos discriminates


def _perfect_site(s: Any) -> bool:
    return not s.n_mismatch and not s.n_gap and not s.n_unaligned


def spec_overview(spec: Any, assay: Any, search_rows: list[dict[str, Any]]) -> list[TierOverview]:
    """The answer to "is my assay still specific?" per searched tier (advisor subagent,
    2026-09-25): products yes or no, which primers carry the discrimination, their closest site,
    and whether anything was left unassessed. Site counts stay in the findings below."""
    out: list[TierOverview] = []
    tiers = [t["tier"] for t in search_rows if t["tier"] != "target"]
    for tier in sorted(tiers, key=lambda t: TIER_ORDER.get(t, 5)):
        row = next(t for t in search_rows if t["tier"] == tier)
        amps = {(a.accession, a.start, a.end, a.roles) for a in spec.amplicons if a.tier == tier}
        detected = {
            (a.accession, a.start, a.end, a.roles)
            for a in spec.amplicons
            if a.tier == tier and a.classification == "likely_detected"
        }
        closest: dict[str, Any] = {}
        for role in _ROLES:
            sites = [s for s in spec.sites if s.tier == tier and s.role == role]
            closest[role] = min(sites, key=_closeness) if sites else None
        by_design = [r for r in _ROLES if closest[r] is not None and _perfect_site(closest[r])]
        cut = {c.query for c in spec.counts if c.tier == tier and c.truncated}
        incomplete = sorted(cut | set(row["saturated"]))
        discriminating = [r for r in ("forward", "reverse") if r not in by_design]
        title = TIER_TITLE.get(tier, tier)
        if tier == "near_neighbours" and assay.target.must_not_detect_taxids:
            title = "Must not detect"
        out.append(
            TierOverview(
                tier=tier, title=title, n_taxa=len(row["taxids"]), products=len(amps),
                detected=len(detected), closest=closest, by_design=by_design,
                discriminating=discriminating, incomplete=incomplete,
                discriminating_complete=not any(
                    assay.role_of(q) in discriminating for q in incomplete
                ),
            )  # fmt: skip
        )
    return out


# ---------------------------------------------------------------- history: off-target site changes
_LEVEL_RANK = {"critical": 0, "warning": 1, "minor": 2, None: 3}


@dataclass
class SiteChangeGroup:
    kind: str  # new | resolved | changed
    tier: str
    organism: str
    n_sites: int = 0
    records: set[str] = field(default_factory=set)
    roles: Counter = field(default_factory=Counter)
    levels: Counter = field(default_factory=Counter)  # the level that matters: after, or before
    example: Any = None


@dataclass
class SiteChangeView:
    groups: list[SiteChangeGroup]
    minor: Counter  # kind -> changes at minor level only


def site_change_view(new: list[Any], resolved: list[Any], changed: list[Any]) -> SiteChangeView:
    """Changes in off-target sites since the previous run, one row per change, tier and
    organism (user, 2026-09-25: 1,450 single rows made the report 800 kB). Changes that stay at
    minor level are only counted: the report keeps the closest minor sites per oligo, so those
    come and go between runs. Every change stays in the workbook (sheet "History")."""
    groups: dict[tuple[str, str, str], SiteChangeGroup] = {}
    minor: Counter = Counter()
    for kind, items in (("new", new), ("resolved", resolved), ("changed", changed)):
        for s in items:
            levels = {s.level_before, s.level_after} - {None}
            if levels <= {"minor"}:
                minor[kind] += 1
                continue
            level = s.level_before if kind == "resolved" else s.level_after
            org = s.organism or "unknown organism"
            g = groups.setdefault((kind, s.tier, org), SiteChangeGroup(kind, s.tier, org))
            g.n_sites += 1
            g.records.add(s.accession)
            g.roles[s.role] += 1
            g.levels[level] += 1
            if g.example is None or _LEVEL_RANK.get(level, 3) < _LEVEL_RANK.get(
                g.example.level_before if kind == "resolved" else g.example.level_after, 3
            ):
                g.example = s
    order = {"new": 0, "changed": 1, "resolved": 2}
    return SiteChangeView(
        groups=sorted(
            groups.values(),
            key=lambda g: (order[g.kind], TIER_ORDER.get(g.tier, 5), -g.levels["critical"],
                           -g.n_sites, g.organism),
        ),
        minor=minor,
    )  # fmt: skip
