"""Find the reference amplicon in a genome and cut out that region (plus flanks).

The amplicon is located by exact k-mer seeds taken along the reference amplicon on both strands
(``seed_length`` bases, every ``seed_step`` positions). Every seed occurrence implies where the
amplicon starts on the contig; occurrences that agree (within a small indel tolerance) form one
locus. Seeds are spread over the whole amplicon, so a variant with mismatches inside a primer or
probe site is still found through the unchanged stretches between them -- which is the point of
the analysis. A region with no exact ``seed_length``-mer left anywhere is reported as not found,
never guessed. A region hidden by N is reported as masked: partly masked through N-tolerant seeds
(:func:`find_masked`), wholly masked through the reference sequence on either side of the
amplicon (:func:`find_masked_by_context`).

``str.find`` does the scanning (C speed), so a 5 Mb genome takes well under a second.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Any, Literal

from ..oligo import iupac

INDEL_TOLERANCE = 20  # seed-implied starts this close together are one locus
MAX_OCCURRENCES_PER_SEED = 50  # repeated k-mers beyond this are not informative
CONTEXT_NT = 1000  # reference sequence taken on each side of the amplicon to anchor a masked one
CONTEXT_SEED_STEP = 8
MIN_CONTEXT_SEEDS = 3  # agreeing context seeds needed to place the amplicon
MIN_MASKED_FRACTION = 0.5  # share of N in the expected amplicon window to call it masked


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


def find_loci(
    contigs: dict[str, str],
    amplicon: str,
    *,
    seed_length: int,
    seed_step: int,
    flank: int,
) -> list[Locus]:
    """Every copy of the amplicon region in ``contigs``, best supported first."""
    amp = amplicon.upper()
    n = len(amp)
    pairs = seeds(amp, seed_length, seed_step)
    loci: list[Locus] = []
    for name, seq in contigs.items():
        for strand, starts in _votes(seq, pairs, n).items():
            for cluster in _clusters(sorted(starts)):
                loci.append(_cut(name, seq, strand, cluster, n, flank))  # type: ignore[arg-type]
    loci.sort(key=lambda lc: (-lc.n_seeds, lc.truncated, lc.contig, lc.start))
    return loci


def _votes(seq: str, pairs: list[tuple[int, str]], n: int) -> dict[str, list[int]]:
    """Per strand, the forward-strand start each seed occurrence implies for an ``n``-long query."""
    votes: dict[str, list[int]] = defaultdict(list)
    for off, kmer in pairs:
        for pos in _occurrences(seq, kmer):  # sense: the query starts at pos - off
            votes["+"].append(pos - off)
        rc = iupac.reverse_complement(kmer)
        for pos in _occurrences(seq, rc):  # antisense: the query ends at pos + k + off - 1
            votes["-"].append(pos + len(kmer) + off - n)
    return votes


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


def find_masked_by_context(
    contigs: dict[str, str],
    amplicon: str,
    left: str,
    right: str,
    *,
    seed_length: int,
    flank: int,
) -> list[Locus]:
    """Where even :func:`find_masked` found nothing: is the whole region one run of N?

    A low-coverage genome can read N over the amplicon and far beyond it, leaving no real base to
    match (live: SARS-CoV-2 records with 1,144 N over the N1 region). ``left`` and ``right`` are
    the reference sequence just before and after the amplicon (sense orientation). Where either
    is found (exact seeds, at least ``MIN_CONTEXT_SEEDS`` agreeing), it tells where the amplicon
    should be; if at least half of that window is N, the region is reported as masked. A window
    of real bases that the amplicon's seeds did not match stays 'not found' (divergent or
    absent): only N counts as masked.
    """
    n = len(amplicon)
    loci: list[Locus] = []
    for name, seq in contigs.items():
        if seq.count("N") < n * MIN_MASKED_FRACTION:
            continue
        spans: list[tuple[int, str, int]] = []  # (support, strand, amplicon start, forward 0-based)
        for side, ctx in (("left", left.upper()), ("right", right.upper())):
            if len(ctx) < seed_length:
                continue
            pairs = seeds(ctx, seed_length, CONTEXT_SEED_STEP)
            for strand, starts in _votes(seq, pairs, len(ctx)).items():
                for cluster in _clusters(sorted(starts)):
                    if len(cluster) < MIN_CONTEXT_SEEDS:
                        continue
                    at = sorted(cluster)[len(cluster) // 2]  # context occupies [at, at + len)
                    sense_before = (side == "left") == (strand == "+")
                    start = at + len(ctx) if sense_before else at - n
                    spans.append((len(cluster), strand, start))
        seen: list[tuple[str, int]] = []
        for support, strand, start in sorted(spans, reverse=True):
            if any(s == strand and abs(start - x) <= INDEL_TOLERANCE for s, x in seen):
                continue
            seen.append((strand, start))
            lo, hi = max(0, start), min(len(seq), start + n)
            if hi - lo < n * MIN_MASKED_FRACTION:  # mostly beyond the record's end
                continue
            if seq[lo:hi].count("N") >= n * MIN_MASKED_FRACTION:
                lc = _cut(name, seq, strand, [start], n, flank)  # type: ignore[arg-type]
                loci.append(replace(lc, n_seeds=support))
    loci.sort(key=lambda lc: (-lc.n_seeds, lc.contig, lc.start))
    return loci


def implied_offset(region: str, amplicon: str, k: int) -> int | None:
    """Where ``amplicon`` starts in ``region`` (sense orientation), from its exact k-mers: the
    median implied start, negative when the region is cut before the amplicon's start (a
    :class:`Locus` stores such an offset as 0). None when no k-mer occurs."""
    region, amplicon = region.upper(), amplicon.upper()
    starts = []
    for i in range(0, len(amplicon) - k + 1):
        kmer = amplicon[i : i + k]
        j = region.find(kmer)
        while j != -1:
            starts.append(j - i)
            j = region.find(kmer, j + 1)
    if not starts:
        return None
    return sorted(starts)[len(starts) // 2]


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


@lru_cache(maxsize=200_000)
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


def locus_identity(locus: Any, amplicon: str, k: int) -> float:
    """Identity of a stored or found copy (:class:`Locus` or a stored locus) to ``amplicon``
    over the part it covers; a cut copy is placed again from its k-mers (its stored offset may
    be clamped to 0)."""
    region, offset = locus.region, locus.offset
    if locus.truncated:
        placed = implied_offset(region, amplicon, k)
        if placed is None:
            return 0.0
        offset = placed
    return amplicon_identity(region, amplicon, offset)[0]


def scan_region(
    contigs: dict[str, str],
    amplicon: str,
    context: Callable[[], tuple[str, str]] | None = None,
    *,
    seed_length: int,
    seed_step: int,
    flank: int,
    other_amplicons: Sequence[str] = (),
    min_identity: float = 0.0,
) -> tuple[list[Locus], list[Locus], int]:
    """``(loci, masked, ref)``: every clean copy of the region, or else where it is hidden by N.

    ``other_amplicons`` are the assay's further reference amplicons (other lineages): they are
    tried, in order, only when the first finds nothing; ``ref`` is the index of the reference
    whose copies were found (0 = ``amplicon``). ``context`` returns the reference sequence on
    each side of the amplicon; it is called only when nothing else was found, so it can fetch
    lazily. With ``min_identity``, a reference whose copies all fall below it (regions that only
    resemble the target) does not stop the search: the next reference is tried, and those
    regions are returned only when no reference finds a real copy.
    """
    kw = {"seed_length": seed_length, "flank": flank}
    related: tuple[list[Locus], int] | None = None
    for i, amp in enumerate([amplicon, *other_amplicons]):
        loci = find_loci(contigs, amp, seed_step=seed_step, **kw)
        if loci and (
            not min_identity
            or any(locus_identity(lc, amp, seed_length) >= min_identity for lc in loci)
        ):
            return loci, [], i
        if loci and related is None:
            related = (loci, i)
    if related is not None:
        return related[0], [], related[1]
    masked = find_masked(contigs, amplicon, seed_step=seed_step, **kw)
    if not masked and context is not None and any(ctx := context()):
        masked = find_masked_by_context(contigs, amplicon, *ctx, **kw)
    return [], masked, 0
