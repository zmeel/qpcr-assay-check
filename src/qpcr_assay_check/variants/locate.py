"""Find the reference amplicon in a genome and cut out that region (plus flanks).

The amplicon is located by exact k-mer seeds taken along the reference amplicon on both strands
(``seed_length`` bases, every ``seed_step`` positions). Every seed occurrence implies where the
amplicon starts on the contig; occurrences that agree (within a small indel tolerance) form one
locus. Seeds are spread over the whole amplicon, so a variant with mismatches inside a primer or
probe site is still found through the unchanged stretches between them -- which is the point of
the analysis. A region with no exact ``seed_length``-mer left anywhere is reported as not found,
never guessed.

``str.find`` does the scanning (C speed), so a 5 Mb genome takes well under a second.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Literal

from ..oligo import iupac

INDEL_TOLERANCE = 20  # seed-implied starts this close together are one locus
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
        votes: dict[str, list[int]] = defaultdict(list)
        for off, kmer in pairs:
            for pos in _occurrences(seq, kmer):  # sense: amplicon starts at pos - off
                votes["+"].append(pos - off)
            rc = iupac.reverse_complement(kmer)
            for pos in _occurrences(seq, rc):  # antisense: amplicon ends at pos + k + off - 1
                votes["-"].append(pos + len(kmer) + off - n)
        for strand, starts in votes.items():
            for cluster in _clusters(sorted(starts)):
                loci.append(_cut(name, seq, strand, cluster, n, flank))  # type: ignore[arg-type]
    loci.sort(key=lambda lc: (-lc.n_seeds, lc.truncated, lc.contig, lc.start))
    return loci


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
