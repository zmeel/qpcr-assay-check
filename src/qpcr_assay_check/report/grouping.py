"""Condensed report tables: off-target products and sites per tier and species.

Every product and site stays in the workbook and hits.tsv; the HTML shows one row per tier and
species, most concerning first (must-not-detect tiers before background, out of scope last),
with the counts it summarises. Advice of the advisor subagent (2026-09-25): state the
denominator on every row and never hide a WARN or FAIL in a collapsed block. Rows that can
fail the verdict (must-not-detect tiers, products the probe would detect, critical sites) are
always shown; only the remaining rows beyond a fixed number go to the workbook.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from ..oligo import iupac
from ..oligo.grade import OUTCOMES, combination_outcome
from ..specificity.closest import closest_key
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
    channels: Counter = field(default_factory=Counter)  # detecting channel -> products

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
        g.channels.update(a.channels)
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


def _closeness(s: SiteResult) -> tuple[Any, ...]:
    """The shared rule (:mod:`..specificity.closest`): highest level, then the closest."""
    return closest_key(s)


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
    # per outcome, what is not listed (:class:`Folded`)
    attention_grouped: list[Folded]
    detectable_top: list[tuple[Any, str, bool]]
    detectable_rest: int  # combinations
    detectable_rest_records: int
    detectable_rest_types: list[tuple[str, int, int]]  # (name, records, strain names merged)
    # site variants that occur only in folded combinations, so no listed row shows them: per
    # folded outcome (and "detectable"), as the per-oligo table selected them (report review
    # 2026-11-20, second round: the per-oligo table merged into this one)
    hidden: dict[str, HiddenSites] = field(default_factory=dict)
    rule: Any = None  # the listing rule applied (report.needs_attention)
    listing: dict[int, str] = field(default_factory=dict)  # id(combination) -> listed or why not


@dataclass
class Folded:
    """The combinations of one outcome that are not listed, counted (user and advisor,
    2026-11-27: the folded row names the bar, the share, the largest one left out and where they
    fail)."""

    outcome: str
    kinds: list[tuple[str, int, int]]  # the 3 main types (name, records, strain names)
    n: int  # combinations
    records: int
    n_kinds: int  # types
    largest: int  # records of the largest combination left out
    fail_by_role: dict[str, int]  # records whose site of that role is not detectable
    over_cap: int = 0  # of them, at or above the bar but beyond max_rows


@dataclass
class HiddenSites:
    """Site variants of folded combinations that no listed row shows."""

    listed: list[tuple[str, Any]]  # (role, per-oligo variant row: count over all records)
    singles: dict[str, int]  # class -> variants seen in one record only
    tolerated_more: int = 0  # tolerated variants beyond the most frequent shown
    more: dict[str, tuple[int, int, int]] = field(default_factory=dict)  # class -> (variants,
    # records, largest) of those below the bar, summarised (user and advisor, 2026-11-27)


def share(value: float) -> str:
    """A percentage as the bars compare it (user and advisor, 2026-11-27: 154 of 176,383 records
    printed as "0.1%", so a row "at 0.1%" sat below a 0.1% bar): from 1% one decimal, below it
    two significant digits, below 0.001% "<0.001%"."""
    if value <= 0:
        return "0%"
    if value < 0.001:
        return "<0.001%"
    if value < 1:
        return f"{value:.2g}%"
    return f"{value:.1f}%"


_STRAIN = re.compile(r"^([^()]+?)\s+\((.+)\)$")


def strains(orgs: Iterable[tuple[Any, ...]]) -> list[tuple[str, int, int]]:
    """Organism names with the strain in brackets merged per name, most records first:
    "Influenza A virus (A/swine/Oklahoma/A01798209/2015(H1N1))" counts under "Influenza A virus
    (N strain names)" (user and advisor, 2026-11-27: the Types column of the influenza report
    wrapped letter by letter). ``(name, records, strain names merged)``; a list already merged
    passes through. The full names stay in the workbook."""
    total: Counter = Counter()
    named: dict[str, set[str]] = defaultdict(set)
    merged: Counter = Counter()
    for name, n, *k in orgs:
        m = _STRAIN.match(name)
        base = m.group(1) if m else name
        total[base] += n
        merged[base] += k[0] if k else 0
        if m:
            named[base].add(name)
    return [(b, n, len(named[b]) + merged[b]) for b, n in total.most_common()]


def _hidden(
    folded: list[Any],
    shown: set[tuple[str, str, str]],
    by_key: dict[tuple[str, str, str], Any],
    top_tolerated: int = 5,
    min_records: int = 2,
    *,
    with_tolerated: bool = True,
    top_per_class: int = 5,
    min_percent: float = 0.0,
) -> HiddenSites | None:
    """The site variants of folded combinations that no listed row shows. A variant that is not
    tolerated is named when it is one of the ``top_per_class`` most frequent of its class or at
    least ``min_percent`` of its oligo's records (and in ``min_records``); the others are summed
    per class. Tolerated variants only where ``with_tolerated`` (the detectable row): they are not
    why a combination fails (user and advisor, 2026-11-27)."""
    keys: dict[tuple[str, str, str], None] = {}
    for f in folded:
        for role, v in (("forward", f.forward), ("probe", f.probe), ("reverse", f.reverse)):
            k = (role, v.q_aln, v.s_aln)
            if k not in shown and k in by_key and not is_perfect_row(by_key[k]):
                keys[k] = None
    rows = sorted(((k[0], by_key[k]) for k in keys),
                  key=lambda x: (_CLASS_ORDER.get(x[1].grade, 3), -x[1].count))  # fmt: skip
    if not with_tolerated:
        rows = [x for x in rows if x[1].grade != "tolerated"]
    if not rows:
        return None
    tolerated = [x for x in rows if x[1].grade == "tolerated"]
    singles: Counter = Counter(
        x[1].grade or "not classified" for x in rows
        if x[1].grade != "tolerated" and x[1].count < min_records
    )  # fmt: skip
    listed: list[tuple[str, Any]] = []
    more: dict[str, list[int]] = {}
    seen_per_class: Counter = Counter()
    for x in rows:
        grade = x[1].grade or "not classified"
        if grade == "tolerated" or x[1].count < min_records:
            continue
        seen_per_class[grade] += 1
        if seen_per_class[grade] <= top_per_class or (x[1].percent or 0) >= min_percent:
            listed.append(x)
        else:
            m = more.setdefault(grade, [0, 0, 0])
            m[0] += 1
            m[1] += x[1].count
            m[2] = max(m[2], x[1].count)
    listed += tolerated[:top_tolerated]
    return HiddenSites(listed=listed, singles=dict(singles),
                       tolerated_more=max(0, len(tolerated) - top_tolerated),
                       more={k: (v[0], v[1], v[2]) for k, v in more.items()})  # fmt: skip


def fragment_view(
    fragments: list[Any],
    total: int,
    bulges: bool = False,
    *,
    top: int = 10,
    rule: Any = None,
    oligos: list[Any] | None = None,
) -> FragmentView:
    """Part A (needs attention: every combination that is not detectable) and Part B
    (detectable: the ``top`` most frequent, the rest in one summary row); advisor subagent,
    2026-09-25.

    A combination that is not detectable gets a row of its own when it is one of the
    ``rule.top_per_outcome`` most frequent of its outcome, or at least ``rule.min_percent`` of
    the records with all three sites (likely failure: ``rule.likely_failure_min_percent``) and in
    at least ``rule.min_records`` records; at most ``rule.max_rows`` rows, the top ones first, then
    likely failure, then by records (user and advisor, 2026-11-27: influenza A listed 30 of 272
    combinations, most under 0.1%). A problem in many genomes is never pushed out by smaller ones
    (user, 2026-09-25): the top of each outcome always shows, and a row at or above the bar that
    does not fit is named in its outcome's folded row. Listed rows are shown worst outcome first;
    the others are one row per outcome (:class:`Folded`). Combinations without a class (sites not
    graded) are never shown as detectable: they go to Part A as "not classified"."""
    from ..config import NeedsAttention

    rule = rule or NeedsAttention()
    rows = [(f, *fragment_outcome(f, bulges)) for f in fragments]
    records: Counter = Counter()
    for f, outcome, _pair in rows:
        moved = getattr(f, "unassembled", 0) if outcome != "detectable" else 0
        parts = 0 if getattr(f, "from_parts_counted", True) else getattr(f, "from_parts", 0)
        records[outcome or "not classified"] += f.count - moved - parts
        if moved:  # draft genomes whose copies are possibly unassembled: undetermined
            records["possibly unassembled"] += moved
        if parts:  # judged from cut copies and not counted as detected
            records["detectable from parts"] += parts
    by_count = sorted([r for r in rows if r[1] != "detectable"], key=lambda r: -r[0].count)
    tops = [r for outcome in _ORDER
            for r in [x for x in by_count if x[1] == outcome][: rule.top_per_outcome]]  # fmt: skip
    top_ids = {id(r) for r in tops}
    bar = rule.min_percent / 100.0 * total
    lf_bar = rule.likely_failure_min_percent / 100.0 * total

    def at_bar(r: tuple[Any, str, bool]) -> bool:
        n = r[0].count
        return n >= rule.min_records and (n >= bar or (r[1] == "likely failure" and n >= lf_bar))

    barred = sorted((r for r in by_count if id(r) not in top_ids and at_bar(r)),
                    key=lambda r: (r[1] != "likely failure", -r[0].count))  # fmt: skip
    order = [*tops, *barred]
    keep = {id(r) for r in order[: rule.max_rows]}
    over = {id(r) for r in order[rule.max_rows :]}
    listing = {
        id(r[0]): (f"yes: one of the {rule.top_per_outcome} most frequent of its outcome"
                   if id(r) in top_ids else "yes: at or above the bar") if id(r) in keep
        else "no: over the row cap" if id(r) in over else "no: below the bar"
        for r in by_count
    }  # fmt: skip
    attention = sorted(
        [r for r in by_count if id(r) in keep], key=lambda r: (_ORDER.index(r[1]), -r[0].count)
    )
    n_combos: Counter = Counter()
    n_records: Counter = Counter()
    largest: Counter = Counter()
    n_over: Counter = Counter()
    fails: dict[str, Counter] = defaultdict(Counter)
    kinds: dict[str, Counter] = defaultdict(Counter)
    for r in by_count:
        if id(r) in keep:
            continue
        f, outcome, _pair = r
        n_combos[outcome] += 1
        n_records[outcome] += f.count
        largest[outcome] = max(largest[outcome], f.count)
        n_over[outcome] += id(r) in over
        for role, v in (("forward", f.forward), ("probe", f.probe), ("reverse", f.reverse)):
            if v.grade not in ("perfect", "tolerated"):
                fails[outcome][role] += f.count
        kinds[outcome].update(dict(f.organisms) if f.organisms else {"unknown": f.count})
    detectable = sorted([r for r in rows if r[1] == "detectable"], key=lambda r: -r[0].count)
    rest = detectable[top:]
    types: Counter = Counter()
    for f, _o, _p in rest:
        types.update(dict(f.organisms))
    by_key = {(o.role, r.q_aln, r.s_aln): r for o in (oligos or []) for r in o.rows}
    shown = (
        set()
        if not oligos
        else {
            (role, v.q_aln, v.s_aln)
            for f, _o, _p in [*attention, *detectable[:top]]
            for role, v in (("forward", f.forward), ("probe", f.probe), ("reverse", f.reverse))
        }
    )
    hidden: dict[str, HiddenSites] = {}
    for outcome in n_combos if oligos else ():
        h = _hidden([r[0] for r in by_count if id(r) not in keep and r[1] == outcome],
                    shown, by_key, min_records=rule.min_records, with_tolerated=False,
                    min_percent=rule.min_percent)  # fmt: skip
        if h:
            hidden[outcome] = h
    h = _hidden([f for f, _o, _p in rest], shown, by_key) if oligos else None
    if h:
        hidden["detectable"] = h
    return FragmentView(
        hidden=hidden,
        total=total,
        records=records,
        attention=attention,
        attention_grouped=[
            Folded(outcome=o, kinds=strains(kinds[o].items())[:3],
                   n=n_combos[o], records=n_records[o],
                   n_kinds=len(strains(kinds[o].items())), largest=largest[o],
                   fail_by_role={r: fails[o][r] for r in ("forward", "probe", "reverse")
                                 if fails[o][r]},
                   over_cap=n_over[o])
            for o in sorted(n_combos, key=_ORDER.index)
        ],
        rule=rule,
        listing=listing,
        detectable_top=detectable[:top],
        detectable_rest=len(rest),
        detectable_rest_records=sum(f.count for f, _o, _p in rest),
        detectable_rest_types=strains(types.items())[:5],
    )  # fmt: skip


# ---------------------------------------------------------------- compact per-oligo variants
_CLASS_ORDER = {"likely_failure": 0, "at_risk": 1, "indeterminate": 2, None: 3, "tolerated": 4}
_COMP = {"A": "T", "C": "G", "G": "C", "T": "A"}


def site_changes(row: Any) -> str:
    """The differences of a site from its oligo, short: position from the 3' end and the type
    primer-template (as in the class notes, Stadhouders' convention), e.g. "-3 C-A, -12 G-T".
    An incompatible degenerate or ambiguous base is written oligo/site; one that still matches is
    written oligo=site ("-9 Y=T": the oligo is degenerate there and this template takes T, so the
    position is a match but not the same base). Runs of inserted or deleted bases are written once
    ("2-base insertion between -11 and -10", "-12 to -11 deleted")."""
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
        elif qc != sc:  # compatible through a degenerate code: a match, but not the same base
            out.append(f"-{at} {qc}={sc}")
    flush()
    return ", ".join(out) or "none"


def is_perfect_row(row: Any) -> bool:
    """A variant row that binds perfectly (a graded record, or an ungraded one without a
    mismatch or gap)."""
    return row.grade == "perfect" or (row.grade is None and not row.n_mismatch and not row.n_gap)


def site_frequency(oligos: list[Any]) -> dict[tuple[str, str, str], float]:
    """(role, oligo alignment, site alignment) -> % of that oligo's records with this variant,
    for the frequency next to each site in the whole-fragment table."""
    return {(o.role, r.q_aln, r.s_aln): r.percent for o in oligos for r in o.rows}


# ---------------------------------------------------------------- specificity at a glance
def tier_name(tier: str) -> str:
    """A tier as the reader knows it ("Near neighbours"), not its configuration key."""
    return TIER_TITLE.get(tier, tier.replace("_", " ").capitalize())


_TIER_LIST = re.compile(
    r"((?:tiers? assessed|not searched(?: in this run)?): )([a-z_]+(?:, [a-z_]+)*)"
)


def plain_tiers(text: str) -> str:
    """Tier keys in a finding's text in the reader's words: "Tier 'background'" becomes
    "Background", and the lists after "tiers assessed:" or "not searched:" are named alike
    (third report review, 2026-11-25: configuration keys survived on paper)."""
    text = re.sub(r"Tier '([a-z_]+)'", lambda m: tier_name(m.group(1)), text)
    return _TIER_LIST.sub(
        lambda m: m.group(1) + ", ".join(tier_name(k) for k in m.group(2).split(", ")), text
    )


def gap_text(short: str, about: list[str]) -> str:
    """A gap's short wording with what it is about: in place of ``{about}`` ("A, B and C"),
    else in brackets after it. Tier keys among them are named as the reader knows them."""
    about = [TIER_TITLE.get(a, a) for a in about]
    if "{about}" in short:
        names = (
            ", ".join(about[:-1]) + (" and " if len(about) > 1 else "") + about[-1]
            if about
            else "?"
        )
        return short.replace("{about}", names)
    return f"{short} ({', '.join(about)})" if about else short


TIER_TITLE = {"near_neighbours": "Near neighbours", "exclusivity": "Clinical organism list",
              "background": "Background", "out_of_scope": "Out of scope"}  # fmt: skip
_ROLES = ("forward", "reverse", "probe")
AMPLICON_ROLES = ("forward", "probe", "reverse")
_T = TypeVar("_T")


def amplicon_order(items: Iterable[_T]) -> list[_T]:
    """Items with a ``role`` in their order on the amplicon (forward, probe, reverse), keeping the
    order within a role: how the report and the workbook list oligos (user, 2026-11-20)."""
    return sorted(items, key=lambda o: AMPLICON_ROLES.index(o.role))  # type: ignore[attr-defined]


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
            # only sites that can prime or bind (warning or critical): a minor site is closer
            # by mismatches at times but cannot act, and the tier's counts leave it out (user,
            # 2026-11-25: a 2-clean-3'-nt site was shown as the clinical list's closest)
            sites = [s for s in spec.sites if s.tier == tier and s.role == role
                     and s.level in ("warning", "critical")]  # fmt: skip
            closest[role] = min(sites, key=_closeness) if sites else None
        by_design = [r for r in _ROLES if closest[r] is not None and _perfect_site(closest[r])]
        cut = {c.query for c in spec.counts if c.tier == tier and c.truncated}
        incomplete = sorted(cut | set(row["saturated"]))
        discriminating = [r for r in ("forward", "reverse") if r not in by_design]
        title = tier_name(tier)
        if tier == "near_neighbours" and assay.target.must_not_detect_taxids:
            title = "Must not detect"
        out.append(
            TierOverview(
                tier=tier,
                title=title,
                n_taxa=len(row["taxids"]),
                products=len(amps),
                detected=len(detected),
                closest=closest,
                by_design=by_design,
                discriminating=discriminating,
                incomplete=incomplete,
                discriminating_complete=not any(
                    assay.role_of(q) in discriminating for q in incomplete
                ),
            )  # fmt: skip
        )
    return out
