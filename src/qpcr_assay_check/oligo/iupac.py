"""IUPAC nucleotide utilities: validation, degenerate expansion, complements, matching.

All sequences are DNA written 5'->3'. Uracil is deliberately not accepted: oligos for
RNA targets are still written as DNA.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable

from ..errors import InputError

IUPAC_CODES: dict[str, str] = {
    "A": "A",
    "C": "C",
    "G": "G",
    "T": "T",
    "R": "AG",
    "Y": "CT",
    "S": "CG",
    "W": "AT",
    "K": "GT",
    "M": "AC",
    "B": "CGT",
    "D": "AGT",
    "H": "ACT",
    "V": "ACG",
    "N": "ACGT",
}

_COMPLEMENT = str.maketrans("ACGTRYSWKMBDHVN", "TGCAYRSWMKVHDBN")


def normalise(raw: str) -> str:
    """Remove all whitespace and upper-case a sequence (papers often print codons/blocks)."""
    return "".join(raw.split()).upper()


def find_invalid(seq: str) -> list[tuple[int, str]]:
    """Return ``(1-based position, character)`` for every non-IUPAC character."""
    return [(i, c) for i, c in enumerate(seq, start=1) if c not in IUPAC_CODES]


def is_degenerate(seq: str) -> bool:
    """True if the sequence contains any code other than A, C, G, T."""
    return any(c not in "ACGT" for c in seq)


def combinations(seq: str) -> int:
    """Number of concrete sequences the (possibly degenerate) sequence expands to."""
    return math.prod(len(IUPAC_CODES[c]) for c in seq)


def expand(seq: str, cap: int) -> list[str]:
    """Expand a degenerate sequence into all concrete sequences (sorted, deterministic).

    Raises :class:`InputError` if the number of combinations exceeds ``cap``.
    """
    n = combinations(seq)
    if n > cap:
        raise InputError(
            f"Degenerate oligo {seq} expands to {n} sequences, above the configured cap of {cap} "
            "(oligo.max_degenerate_expansions). Raise the cap if this is intended."
        )
    return ["".join(p) for p in itertools.product(*(sorted(IUPAC_CODES[c]) for c in seq))]


def complement(seq: str) -> str:
    """IUPAC-aware complement (not reversed)."""
    return seq.translate(_COMPLEMENT)


def reverse_complement(seq: str) -> str:
    """IUPAC-aware reverse complement."""
    return seq.translate(_COMPLEMENT)[::-1]


def gc_percent(seq: str) -> float:
    """GC content (%) of a concrete sequence."""
    return 100.0 * sum(c in "GC" for c in seq) / len(seq)


def longest_run(seq: str, base: str | None = None) -> int:
    """Length of the longest homopolymer run (optionally restricted to ``base``)."""
    best = 0
    for b, group in itertools.groupby(seq):
        if base is None or b == base:
            best = max(best, sum(1 for _ in group))
    return best


def compatible(a: str, b: str) -> bool:
    """True if two IUPAC codes can represent the same base (their base sets intersect)."""
    return bool(set(IUPAC_CODES[a]) & set(IUPAC_CODES[b]))


def count_mismatches(oligo: str, window: str) -> int:
    """Hamming-style mismatches between an oligo and an equally long target window.

    An IUPAC position counts as a match if the two codes can represent the same base.
    """
    if len(oligo) != len(window):
        raise ValueError("oligo and window must have the same length")
    return sum(not compatible(a, b) for a, b in zip(oligo, window, strict=True))


def describe_invalid(invalid: Iterable[tuple[int, str]]) -> str:
    """Human-readable list of invalid characters, e.g. ``'U' at position 5, '-' at position 9``."""
    return ", ".join(f"'{c}' at position {i}" for i, c in invalid)
