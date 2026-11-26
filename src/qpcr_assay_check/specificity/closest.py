"""Which off-target site counts as the closest: one rule for every table and figure (code review
2026-11-26: about seven copies had drifted, so the same organism's "closest site" depended on
whether charts were switched on)."""

from __future__ import annotations

from typing import Any

LEVEL_RANK = {"critical": 0, "warning": 1, "minor": 2}


def closeness(s: Any) -> tuple[Any, ...]:
    """Fewest mismatches and gaps, then the longest clean 3' end, then the site id."""
    return (s.n_mismatch + s.n_gap, -s.clean_3prime_nt, s.id)


def closest_key(s: Any) -> tuple[Any, ...]:
    """The highest level first, then :func:`closeness` (user, 2026-11-26: by mismatches alone a
    minor site with no clean 3' end stood for an organism with 577 warning sites)."""
    return (LEVEL_RANK.get(s.level, 3), *closeness(s))


def drawable_primer_site(s: Any) -> bool:
    """A primer site with a full alignment (worst-case partial sites have none to show)."""
    return s.role != "probe" and s.source != "blast_partial_worst_case" and bool(s.q_aln)
