"""Seed and alignment helpers shared by the chain locator (:mod:`.chain`).

``_occurrences`` finds exact k-mers with ``str.find`` (C speed); :func:`find_masked` finds a
fragment with no exact k-mer left through N-tolerant seeds (reported as hidden by N, never as a
match); :func:`amplicon_identity` measures how closely a region matches a reference fragment
(banded alignment). The copy finding itself is in :mod:`.chain` (overhaul, 2026-09-29).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

from ..oligo import iupac

INDEL_TOLERANCE = 20  # N-tolerant seeds this close together are one locus; alignment band
MAX_OCCURRENCES_PER_SEED = 50  # repeated k-mers beyond this are not informative


@dataclass(frozen=True)
class Locus:
    """One copy of the amplicon region in a genome, read in the reference amplicon's sense."""

    contig: str
    strand: Literal["+", "-"]
    start: int  # 1-based, on the contig's forward strand, of the returned region
    end: int  # inclusive
    region: str  # amplicon +- flanks (+ indel padding), in the amplicon's sense orientation
    offset: int  # index in ``region`` where the amplicon is expected to start
    n_seeds: int
    truncated: bool  # the contig ends inside the amplicon (a draft-assembly contig break)


def seeds(amplicon: str, length: int, step: int) -> list[tuple[int, str]]:
    """``(offset, k-mer)`` pairs along the amplicon; always includes the last full k-mer."""
    amp = amplicon.upper()
    if len(amp) < length:
        return [(0, amp)] if amp else []
    starts = list(range(0, len(amp) - length + 1, step))
    if starts[-1] != len(amp) - length:
        starts.append(len(amp) - length)
    return [(i, amp[i : i + length]) for i in starts if set(amp[i : i + length]) <= set("ACGT")]


def _occurrences(seq: str, kmer: str) -> list[int]:
    out, i = [], seq.find(kmer)
    while i != -1 and len(out) <= MAX_OCCURRENCES_PER_SEED:
        out.append(i)
        i = seq.find(kmer, i + 1)
    return out if len(out) <= MAX_OCCURRENCES_PER_SEED else []


def _clusters(starts: list[int]) -> list[list[int]]:
    groups: list[list[int]] = []
    for s in starts:
        if groups and s - groups[-1][-1] <= INDEL_TOLERANCE:
            groups[-1].append(s)
        else:
            groups.append([s])
    return groups


def _cut(
    contig: str, seq: str, strand: Literal["+", "-"], cluster: list[int], n: int, flank: int
) -> Locus:
    """The region around one seed cluster, in the amplicon's sense orientation."""
    start0 = sorted(cluster)[len(cluster) // 2]  # median implied amplicon start (0-based, fwd)
    pad = flank + INDEL_TOLERANCE
    lo, hi = max(0, start0 - pad), min(len(seq), start0 + n + pad)
    truncated = start0 < 0 or start0 + n > len(seq)
    window = seq[lo:hi]
    if strand == "+":
        region, offset = window, start0 - lo
    else:
        region, offset = iupac.reverse_complement(window), hi - (start0 + n)
    return Locus(
        contig=contig, strand=strand, start=lo + 1, end=hi, region=region,
        offset=max(0, offset), n_seeds=len(cluster), truncated=truncated,
    )  # fmt: skip


def find_masked(
    contigs: dict[str, str],
    amplicon: str,
    *,
    seed_length: int,
    seed_step: int,
    flank: int,
) -> list[Locus]:
    """Where :func:`find_loci` found nothing: is the region there, but hidden by N?

    Low-coverage genomes carry runs of N. Each seed is matched with N allowed at any position,
    but a match counts only when at least half of its bases are real (so a plain N-run matches
    nothing), and a locus needs at least two agreeing seeds. A region found this way is reported
    as masked by N, never assessed: an N is neither a match nor a variant.
    """
    amp = amplicon.upper()
    n = len(amp)
    pairs = seeds(amp, seed_length, seed_step)
    need = seed_length // 2
    loci: list[Locus] = []
    for name, seq in contigs.items():
        if "N" not in seq:
            continue
        votes: dict[str, list[int]] = defaultdict(list)
        for off, kmer in pairs:
            for strand, k in (("+", kmer), ("-", iupac.reverse_complement(kmer))):
                pattern = re.compile("(?=(" + "".join(f"[{b}N]" for b in k) + "))")
                for m in pattern.finditer(seq):
                    if len(m.group(1)) - m.group(1).count("N") < need:
                        continue
                    pos = m.start()
                    votes[strand].append(pos - off if strand == "+" else pos + len(k) + off - n)
        for strand, starts in votes.items():
            for cluster in _clusters(sorted(starts)):
                if len(cluster) >= 2:
                    loci.append(_cut(name, seq, strand, cluster, n, flank))  # type: ignore[arg-type]
    loci.sort(key=lambda lc: (-lc.n_seeds, lc.contig, lc.start))
    return loci


def amplicon_identity(
    region: str, amplicon: str, offset: int, band: int = INDEL_TOLERANCE
) -> tuple[float, int]:
    """``(identity, covered)``: how closely the region matches the reference amplicon placed at
    ``offset`` (may be negative for a copy cut before its start). Identity is the matching bases
    of a banded semi-global alignment (match +1, mismatch -1, gap -2; the region's ends free)
    divided by the part of the amplicon the region covers (advisor subagent, 2026-09-28: true
    Legionella copies 0.99-1.00, an unrelated region found through one chance seed 0.57, random
    windows 0.56 +- 0.02)."""
    n = len(amplicon)
    first, last = max(0, -offset), min(n, len(region) - offset)
    if last <= first:
        return 0.0, 0
    lo = max(0, offset + first - band)
    hi = min(len(region), offset + last + band)
    matches = _banded_matches(
        amplicon[first:last].upper(), region[lo:hi].upper(), offset + first - lo, band
    )
    return matches / (last - first), last - first


@lru_cache(maxsize=20_000)  # identities are also kept per stored locus
def _banded_matches(q: str, s: str, d0: int, band: int) -> int:
    """Matching bases on the best banded alignment of all of ``q`` inside ``s`` (q[i] lies near
    s[d0 + i]); ties go to more matches. Cached: the same regions recur across genomes."""
    neg = (-(10**9), 0)
    prev = dict.fromkeys(range(max(0, d0 - band), min(len(s), d0 + band) + 1), (0, 0))
    for i in range(1, len(q) + 1):
        row: dict[int, tuple[int, int]] = {}
        centre = d0 + i
        for j in range(max(0, centre - band), min(len(s), centre + band) + 1):
            best = neg
            if j >= 1 and j - 1 in prev:
                sc, m = prev[j - 1]
                same = q[i - 1] == s[j - 1] and q[i - 1] != "N"
                best = max(best, (sc + (1 if same else -1), m + same))
            if j in prev:
                sc, m = prev[j]
                best = max(best, (sc - 2, m))
            if j - 1 in row:
                sc, m = row[j - 1]
                best = max(best, (sc - 2, m))
            row[j] = best
        prev = row
    return max(prev.values())[1] if prev else 0
