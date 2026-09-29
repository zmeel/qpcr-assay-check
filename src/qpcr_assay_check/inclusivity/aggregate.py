"""Per-year statistics of one oligo's sites on the target's genomes (exhaustive analysis).

The sampled inclusivity built from the target tier's own BLAST hits was removed in the overhaul
(user decision, 2026-09-29); every figure now comes from the exhaustive variant analysis.
"""

from __future__ import annotations

from collections import defaultdict

from ..oligo.grade import DETECTABLE, INDETERMINATE, UNDETERMINED_RULES
from ..specificity.models import SiteResult
from .models import WindowStats


def detectable_percent(w: WindowStats) -> float | None:
    """Share of the window's records that the oligo is expected to detect: the graded classes
    perfect + tolerated, or (records made before the classes) 0-1 mismatch, clean 3' end.
    Undetermined records are left out; None when no record is left (or the window is empty)."""
    if w.sample_size == 0:
        return None
    if w.n_detectable is not None:
        good = w.n_detectable
        base = w.sample_size - w.n_undetermined
        return 100.0 * good / base if base > 0 else None
    else:
        good = max(0, w.n_perfect + w.n_one_mismatch - w.n_three_prime_mismatch)
    return 100.0 * good / w.sample_size


def _stats(
    sites: list[SiteResult], year: int, population: int | None, oligo_len: int
) -> WindowStats:
    per_position = [0] * oligo_len
    n_perfect = n_one = n_two_plus = n_three_prime = n_failed = 0
    for s in sites:
        # in inclusivity's own assess_candidates, worst-case only happens when a fetch failed
        # (there is no can_reach_warning-style pruning here, unlike the off-target assessment)
        if s.source == "blast_partial_worst_case":
            n_failed += 1
        for p in s.defect_positions:
            if 1 <= p <= oligo_len:
                per_position[p - 1] += 1
        if s.n_gap or s.n_mismatch >= 2:
            n_two_plus += 1
        elif s.n_mismatch == 1:
            n_one += 1
        else:
            n_perfect += 1
        if s.mismatches_last5:
            n_three_prime += 1
    graded = bool(sites) and all(s.grade is not None for s in sites)
    # MGB-probe mismatches and ambiguity codes (R9, R6): no published basis, left out of the %
    n_undetermined = sum(
        1 for s in sites if s.grade == INDETERMINATE and s.grade_rule in UNDETERMINED_RULES
    )
    by_grade: dict[str, int] = defaultdict(int)
    for s in sites:
        if s.grade is not None:
            by_grade[s.grade] += 1
    return WindowStats(
        year=year,
        population_size=population,
        sample_size=len(sites),
        n_perfect=n_perfect,
        n_one_mismatch=n_one,
        n_two_plus_mismatch=n_two_plus,
        n_three_prime_mismatch=n_three_prime,
        per_position_mismatches=per_position,
        n_fetch_failed=n_failed,
        n_detectable=sum(by_grade[g] for g in DETECTABLE) if graded else None,
        n_by_grade=dict(by_grade),
        n_undetermined=n_undetermined,
    )
