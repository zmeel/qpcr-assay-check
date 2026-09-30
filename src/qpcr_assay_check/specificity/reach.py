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


def floors(
    records: list[SearchRecord], oligos: dict[str, str], tiers: list[str], s: SearchSettings
) -> list[ScoreFloor]:
    """One entry per searched tier and oligo: the highest floor of its searches (the least
    sensitive one decides what is guaranteed) and the searches without statistics."""
    worst: dict[tuple[str, str], int] = {}
    unknown: dict[tuple[str, str], int] = defaultdict(int)
    full: set[tuple[str, str]] = set()
    for r in records:
        if r.tier not in tiers:
            continue
        full |= {(r.tier, q.label) for q in r.saturation if q.list_full}
        for label in r.n_hits:
            key = (r.tier, label)
            st = r.stats.get(label)
            if st is None:
                unknown[key] += 1
                continue
            f = score_floor(st.eff_space, st.kappa, st.lambda_, s.expect)
            worst[key] = max(worst.get(key, f), f)
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
            )
        )
    return out


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
                )
        out.append(
            Finding(
                severity="INFO",
                message=(
                    f"Tier '{tier}': with the E-value cut-off {expect:g} this search reports only "
                    f"alignments scoring at least: {'; '.join(parts)}. Sites with more mismatches "
                    "or a gap can be missing unless found by the partner scan."
                ),
                topic="search",
            )
        )
    return out
