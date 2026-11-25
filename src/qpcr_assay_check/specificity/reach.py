"""What a BLAST search could have reported: the score floor set by the E-value cut-off.

NCBI reports, per query, the Karlin-Altschul statistics of the search (``search.stat``: the
effective search space, lambda and kappa). An alignment with raw score ``S`` has the expected
value ``E = kappa * eff_space * exp(-lambda * S)``, so with the cut-off ``expect`` the smallest
reportable score is ``ceil(ln(kappa * eff_space / expect) / lambda)``.

Checked against real searches (smoke test, NG-F, 17 nt, *N. meningitidis*, search space
8.1e8): the formula gives 10, 8 and 7 for EXPECT 1000, 10000 and 100000; the lowest raw scores
NCBI actually reported were 10, 8 and 7.
"""

from __future__ import annotations

import math
from collections import defaultdict

from ..config import SearchSettings
from ..search.orchestrate import SearchRecord
from .models import Finding, ScoreFloor


def score_floor(eff_space: float, kappa: float, lam: float, expect: float) -> int:
    """Smallest raw score with ``E <= expect`` in a search with these statistics."""
    if min(eff_space, kappa, lam, expect) <= 0:
        raise ValueError("search statistics and the E-value cut-off must be positive")
    return max(1, math.ceil(math.log(kappa * eff_space / expect) / lam - 1e-9))


def always_reported(length: int, floor: int, reward: int, penalty: int, word_size: int) -> int:
    """Most mismatches (no gaps) a full-length site of an oligo may carry and still always be
    reported; -1 when not even a perfect site is.

    Two conditions: the full-length alignment scores at least ``floor`` (``reward`` per match,
    ``penalty`` per mismatch; the best local alignment scores at least as much), and some run of
    identical bases is as long as the BLAST word (``m`` mismatches leave a run of at least
    ``ceil((length - m) / (m + 1))`` bases). Both only get harder with more mismatches.
    """
    best = -1
    for m in range(length + 1):
        score = reward * (length - m) + penalty * m
        run = math.ceil((length - m) / (m + 1))
        if score < floor or run < word_size:
            break
        best = m
    return best


def probe_bound(
    tier: str,
    probes: dict[str, tuple[str, bool]],
    entries: list[ScoreFloor],
    truncated: set[tuple[str, str]],
    min_identical: int,
    gapped_can_bind: bool,
) -> tuple[bool, str]:
    """Can a product of ``tier`` without a re-aligned probe still be called not detected?

    Tiers review 2026-11-20, F3: yes when every probe site that could give signal would have
    been reported by BLAST in that tier, so its absence is evidence. ``probes``: query label ->
    (sequence, MGB probe). Under R9 an ungapped probe site binds with at most 2 mismatches (an
    MGB probe 1), 3 (2) or more being a likely failure. Four conditions: (1) the tier's searches
    always report full-length sites with that many mismatches (its score floor); (2) no hit list
    was full and no assessment cut; (3) the oligo is long enough that such a site survives the
    relevance filter: its best local alignment scores at least the full-length one, L - 4m, and
    has at least that many identical bases; (4) a gapped probe site cannot bind in this tier
    (``gapped_can_bind``: a cautious tier, or binding levels that admit gaps). Returns whether
    it holds and, if not, the first condition that fails.
    """
    if gapped_can_bind:
        return False, (
            "in this tier a probe site with a gap still counts as able to bind, and BLAST does "
            "not reliably report such sites"
        )
    by_label = {e.query: e for e in entries if e.tier == tier}
    for label, (seq, mgb) in sorted(probes.items()):
        limit = 1 if mgb else 2
        e = by_label.get(label)
        if e is None or e.min_score is None or e.searches_without_statistics:
            return False, f"no score floor is known for {label} in this tier"
        if e.list_full or (tier, label) in truncated:
            return False, f"the hit list or the assessment of {label} was cut"
        if e.max_mismatches_reported is None or e.max_mismatches_reported < limit:
            return False, (
                f"{label}: sites with {limit} mismatches are not always reported here (only up "
                f"to {e.max_mismatches_reported})"
            )
        if len(seq) - 4 * limit < min_identical:
            return False, (
                f"{label} ({len(seq)} nt) is too short for a site with {limit} mismatches to "
                f"always pass the relevance filter of {min_identical} identical bases"
            )
    return True, ""


_SOURCES = ["reported", "from_hits", "upper_bound"]  # most to least direct


def floors(
    records: list[SearchRecord], oligos: dict[str, str], tiers: list[str], s: SearchSettings
) -> list[ScoreFloor]:
    """One entry per searched tier and oligo: the highest floor of its searches (the least
    sensitive one decides what is guaranteed) and the searches without statistics."""
    worst: dict[tuple[str, str], int] = {}
    unknown: dict[tuple[str, str], int] = defaultdict(int)
    full: set[tuple[str, str]] = set()
    source: dict[tuple[str, str], str] = {}
    # per (tier, oligo): (taxa of a search, its floor), one entry per taxon group
    each: dict[tuple[str, str], dict[tuple[int, ...], int | None]] = defaultdict(dict)
    for r in records:
        if r.tier not in tiers:
            continue
        full |= {(r.tier, q.label) for q in r.saturation if q.list_full}
        for label in r.n_hits:
            key = (r.tier, label)
            st = r.stats.get(label)
            group = tuple(r.taxids)
            if st is None:
                unknown[key] += 1
                each[key].setdefault(group, None)
                continue
            f = score_floor(st.eff_space, st.kappa, st.lambda_, s.expect)
            prior = each[key].get(group)
            each[key][group] = f if prior is None else max(prior, f)
            worst[key] = max(worst.get(key, f), f)
            if _SOURCES.index(st.space_source) > _SOURCES.index(source.get(key, "reported")):
                source[key] = st.space_source
    out: list[ScoreFloor] = []
    for tier, label in sorted({*worst, *unknown}, key=lambda k: (tiers.index(k[0]), k[1])):
        f = worst.get((tier, label))
        oligo = oligos.get(label, "")
        out.append(
            ScoreFloor(
                tier=tier,
                query=label,
                length=len(oligo),
                min_score=f,
                max_mismatches_reported=(
                    always_reported(len(oligo), f, s.reward, s.penalty, s.word_size)
                    if f is not None and oligo
                    else None
                ),
                searches_without_statistics=unknown.get((tier, label), 0),
                list_full=(tier, label) in full,
                space_source=source.get((tier, label), "reported"),
                per_search=[(list(g), v) for g, v in each.get((tier, label), {}).items()],
            )
        )
    return out


_SOURCE_NOTE = {
    "from_hits": " (search space derived from the reported alignments)",
    "upper_bound": " (search space bounded from above: no alignment to derive it from)",
}


def floor_findings(entries: list[ScoreFloor], expect: float) -> list[Finding]:
    """One INFO line per tier: which oligos are covered to how many mismatches."""
    by_tier: dict[str, list[ScoreFloor]] = defaultdict(list)
    for e in entries:
        by_tier[e.tier].append(e)
    out: list[Finding] = []
    for tier, members in by_tier.items():
        parts = []
        for e in members:
            if e.min_score is None:
                parts.append(f"{e.query}: not known (no search statistics in the report)")
            elif e.max_mismatches_reported is None or e.max_mismatches_reported < 0:
                parts.append(
                    f"{e.query} ({e.length} nt): score >= {e.min_score}, not even a "
                    "perfect site is certain to be reported"
                )
            else:
                parts.append(
                    f"{e.query} ({e.length} nt): score >= {e.min_score}, sites with up to "
                    f"{e.max_mismatches_reported} mismatch(es) always reported"
                    + (" unless cut from the full hit list" if e.list_full else "")
                    + _SOURCE_NOTE.get(e.space_source, "")
                )
        out.append(
            Finding(
                severity="INFO",
                message=(
                    f"Tier '{tier}': with the E-value cut-off {expect:g} this search reports only "
                    f"alignments scoring at least: {'; '.join(parts)}. Sites with more mismatches "
                    "or a gap can be missing unless found by the check for the opposite primer."
                    + _per_search(members)
                ),
                topic="search",
            )
        )
    return out


def _per_search(members: list[ScoreFloor]) -> str:
    """For a tier of several searches: each search's taxa and score floors (lowest to highest
    over the oligos), since the least sensitive one sets the tier's figures (F6)."""
    groups: dict[tuple[int, ...], list[int]] = {}
    for e in members:
        for taxa, f in e.per_search:
            vals = groups.setdefault(tuple(taxa), [])
            if f is not None:
                vals.append(f)
    if len(groups) < 2:
        return ""
    parts = []
    for i, (taxa, vals) in enumerate(groups.items(), start=1):
        shown = ", ".join(map(str, taxa[:5])) + (f" +{len(taxa) - 5} more" if len(taxa) > 5 else "")
        if not vals:
            floor = "no statistics"
        elif min(vals) == max(vals):
            floor = f"score >= {min(vals)}"
        else:
            floor = f"score >= {min(vals)}-{max(vals)}"
        parts.append(f"search {i} ({len(taxa)} taxa: {shown}): {floor}")
    return (
        " The tier's figures are those of its least sensitive search; per search: "
        + "; ".join(parts)
        + "."
    )
