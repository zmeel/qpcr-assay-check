"""Full-length assessment of target-tier candidates for inclusivity (always re-aligned).

Unlike the off-target assessment (``specificity/sites.py``'s ``can_reach_warning`` pruning, which
exists to avoid an ``efetch`` call for hits that cannot matter to a specificity verdict),
inclusivity needs an accurate mismatch count for every sampled hit to compute its
perfect/1-mismatch/2+-mismatch statistics, so a partial hit is always fetched and re-aligned. A
fetch failure is the only reason to fall back to the worst-case estimate, and that hit is flagged
(``source == "blast_partial_worst_case"``) rather than silently counted as an exact measurement.
"""

from __future__ import annotations

import itertools

from ..align import realign
from ..config import SiteRules
from ..specificity.fetch import WindowFetcher
from ..specificity.models import SiteResult
from ..specificity.sites import (
    Candidate,
    oriented_window,
    site_from_alignment,
    site_from_bound,
    site_from_full,
    window_for,
)


def assess_candidates(
    candidates: list[Candidate],
    rules: SiteRules,
    fetcher: WindowFetcher,
    scoring: realign.Scoring,
    window_padding_nt: int,
    ids: itertools.count,
) -> list[SiteResult]:
    """One :class:`SiteResult` per candidate; partial hits are always fetched and re-aligned."""
    out: list[SiteResult] = []
    for c in candidates:
        if not c.partial:
            out.append(site_from_full(c, rules, f"I{next(ids)}"))
            continue
        window = None
        lo = None
        if c.accession != "unknown":
            lo, hi = window_for(c, window_padding_nt, c.hit.length)
            window = fetcher.get(c.accession, lo, hi)
        if window is None:
            out.append(site_from_bound(c, rules, f"I{next(ids)}"))
        else:
            oriented = oriented_window(window, c.orientation)
            aln = realign.align_semiglobal(c.oligo, oriented, scoring)
            out.append(site_from_alignment(c, aln, window, lo, rules, f"I{next(ids)}"))
    return out
