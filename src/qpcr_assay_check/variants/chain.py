"""Locate every copy of a locus by chains of exact blocks (overhaul step 3; not wired in yet).

The reference is the locus fragment, optionally with the sequence on either side of it (its
context, e.g. the 23S rRNA before and the 5S after a spacer). Exact ``k``-mers of the reference
(every ``step`` bases in the fragment, every ``CONTEXT_STEP`` in the context) are found in the
genome with ``str.find``, merged into maximal exact blocks per diagonal, and blocks that lie in
the same order on the reference and the genome (strand-consistent, their offsets differing by
at most ``max_indel``) are chained. One chain is one candidate copy.

Measured live before this was built (scripts/measure_locator.py, 2026-09-29): the previous
locator grouped seeds within 20 nt and placed every oligo from one median offset, so it split
190 of 283 Legionella copies whose spacer differs from the reference by more than 20 nt and
misplaced 518 of 1,132 oligo sites; the chain found each of them as one copy and never lost a
copy the old locator had. Chance chains reached at most 18 anchored bases (402 + 225 decoys).

Coordinates are on the copy's sense sequence (the contig, or its reverse complement for a copy
on the minus strand) and are signed: a copy cut by a contig end starts before 0 or ends past
the sequence end, and is never clamped. Whether a candidate is a copy is decided by
:func:`is_copy`, so the rule can change without scanning again.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Literal

from ..oligo import iupac
from .locate import INDEL_TOLERANCE, _occurrences, amplicon_identity, find_masked

ACGT = frozenset("ACGT")
CONTEXT_STEP = 8  # seed step in the context, near a hit (conserved flanks need few seeds)
COARSE_CONTEXT_STEP = 32  # over the whole genome: any exact flank stretch of 47+ nt is hit
DEFAULT_STEP = 2  # measured: step 2 finds what step 1 finds; step 4 missed divergent opa copies
DEFAULT_MAX_INDEL = 150  # largest length difference to the reference within one chain
CONTEXT_LENGTH = 1000  # flank taken on each side of the fragment in the context record


@dataclass(frozen=True)
class Reference:
    """A locus reference: its fragment and, when known, the sequence on each side of it."""

    fragment: str
    left: str = ""
    right: str = ""

    @property
    def sequence(self) -> str:
        return (self.left + self.fragment + self.right).upper()

    @property
    def span(self) -> tuple[int, int]:
        """Where the fragment lies in :attr:`sequence`."""
        return len(self.left), len(self.left) + len(self.fragment)


@dataclass
class Block:
    """An exact match: reference ``[r0, r1)`` equals sequence ``[s0, s0 + r1 - r0)``."""

    r0: int
    r1: int
    s0: int

    @property
    def s1(self) -> int:
        return self.s0 + self.r1 - self.r0

    @property
    def diag(self) -> int:
        return self.s0 - self.r0


@dataclass(frozen=True)
class Candidate:
    """One chain on a genome sequence, with everything the copy rule and the assessment need.

    ``anchors`` are ``(fragment position, sense position, length)`` of each exact block, the
    fragment position counted from the fragment's first base (negative in the left context).
    ``region`` is the sense sequence around the implied fragment (flanks and indel padding
    included), starting at sense position ``region_start``.
    """

    contig: str
    strand: Literal["+", "-"]
    contig_length: int
    ref: int  # index of the reference that found it
    start: int  # implied fragment start on the sense sequence (signed)
    end: int  # implied fragment end, exclusive (signed)
    fragment_length: int
    anchors: tuple[tuple[int, int, int], ...]
    anchored: int  # M: fragment bases covered by exact blocks
    context_left: int  # context bases anchored before the fragment
    context_right: int  # context bases anchored after it
    identity: float | None  # along the chain, over the part the sequence covers; None if M = 0
    n_inside: int  # N inside the implied fragment
    n_left: int  # N-run just before it
    n_right: int  # N-run just after it
    region: str = field(repr=False)
    region_start: int = 0
    masked: bool = False  # found only through N-tolerant seeds (no exact block left)

    @property
    def cut_left(self) -> bool:
        return self.start < 0

    @property
    def cut_right(self) -> bool:
        return self.end > self.contig_length

    @property
    def cut(self) -> bool:
        """A contig end falls inside the fragment."""
        return self.cut_left or self.cut_right

    @property
    def length_difference(self) -> int:
        return (self.end - self.start) - self.fragment_length

    def place(self, pos: int) -> int:
        """Sense position of fragment position ``pos``, through the nearest anchor."""
        best = min(self.anchors, key=lambda a: _distance(pos, a[0], a[0] + a[2]))
        return best[1] + (pos - best[0])

    def forward_span(self) -> tuple[int, int]:
        """The implied fragment on the contig's forward strand (0-based, end exclusive)."""
        if self.strand == "+":
            return self.start, self.end
        return self.contig_length - self.end, self.contig_length - self.start


@dataclass(frozen=True)
class CopyRule:
    """When a candidate is a copy of the locus (advisor subagent, 2026-09-29; measured).

    (a) at least ``min_anchored`` fragment bases in exact blocks (chance: at most 18);
    (b) at least ``min_context`` context bases anchored on one side, and the fragment has a
        block, or both sides are anchored, or the fragment lies past a contig end (cut);
    (c) identity at least ``min_identity`` with at least ``min_identity_anchored`` fragment
        bases anchored (divergent members of a multi-copy family without shared context, such
        as the N. gonorrhoeae opa copy at identity 0.80 with 16-23 anchored bases).
    """

    min_anchored: int = 32
    min_context: int = 32
    min_identity: float = 0.75
    min_identity_anchored: int = 16


DEFAULT_RULE = CopyRule()


def is_copy(c: Candidate, rule: CopyRule = DEFAULT_RULE) -> bool:
    """Rule (a), (b) or (c) of :class:`CopyRule`; a copy found only through N-tolerant seeds
    counts too (it is judged 'hidden by N', never as a match)."""
    if c.masked or c.anchored >= rule.min_anchored:
        return True
    left, right = c.context_left >= rule.min_context, c.context_right >= rule.min_context
    if (left or right) and (c.anchored > 0 or (left and right) or c.cut):
        return True
    return (
        c.identity is not None
        and c.anchored >= rule.min_identity_anchored
        and c.identity >= rule.min_identity
    )


def locate(
    contigs: dict[str, str],
    references: Sequence[Reference],
    *,
    k: int = 16,
    step: int = DEFAULT_STEP,
    max_indel: int = DEFAULT_MAX_INDEL,
    flank: int = 50,
    masked_below: int = CopyRule.min_anchored,
) -> list[Candidate]:
    """Every candidate copy of the locus in ``contigs``, most anchored first.

    Every chain is kept (one exact block of ``k`` bases, in the fragment or its context), so
    the copy rule can be applied, and changed, after the scan. Where several references find
    the same place, the candidate with the most anchored fragment bases (then the highest
    identity) is kept. The N-tolerant search runs when no candidate has ``masked_below``
    anchored fragment bases; its candidates are kept beside the others (see
    :func:`copies_of`).
    """
    found: list[Candidate] = []
    for ri, ref in enumerate(references):
        seq_ref = ref.sequence
        lo, hi = ref.span
        fine = seed_positions(len(seq_ref), k, lo, hi, step)
        coarse = seed_positions(len(seq_ref), k, lo, hi, step, COARSE_CONTEXT_STEP)
        # blocks as far apart as the whole reference may chain (flanks either side of a long
        # N-run over the fragment); their offsets must still agree within max_indel
        max_gap = reach = len(seq_ref) + max_indel
        for name, contig in contigs.items():
            contig = contig.upper()
            for strand, s in (("+", contig), ("-", iupac.reverse_complement(contig))):
                blocks = _two_pass(s, seq_ref, coarse, fine, k, reach)
                for ch in chain_blocks(blocks, max_indel, max_gap):
                    found.append(_candidate(name, strand, s, ri, ref, ch, flank, max_indel))  # type: ignore[arg-type]
    found = _best_per_place(found)
    # no copy by exact blocks (a chance 16-mer elsewhere does not count): look under the N
    if not any(c.anchored >= masked_below for c in found) and any(
        "N" in s.upper() for s in contigs.values()
    ):
        found += _best_per_place(_masked(contigs, references, k, step, flank))
    return found


def _masked(
    contigs: dict[str, str], references: Sequence[Reference], k: int, step: int, flank: int
) -> list[Candidate]:
    """Where no exact block of the fragment is left: its place through N-tolerant seeds
    (locate.find_masked: at least two agreeing seeds, half of each a real base)."""
    out: list[Candidate] = []
    for ri, ref in enumerate(references):
        n = len(ref.fragment)
        for lc in find_masked(contigs, ref.fragment, seed_length=k, seed_step=step, flank=flank):
            length = len(contigs[lc.contig])
            r0 = lc.start - 1 if lc.strand == "+" else length - lc.end
            start = r0 + lc.offset
            inside = lc.region[lc.offset : lc.offset + n]
            out.append(Candidate(
                contig=lc.contig, strand=lc.strand, contig_length=length, ref=ri, start=start,
                end=start + n, fragment_length=n, anchors=((0, start, 0),), anchored=0,
                context_left=0, context_right=0, identity=None, n_inside=inside.count("N"),
                n_left=0, n_right=0, region=lc.region, region_start=r0, masked=True,
            ))  # fmt: skip
    return out


def _candidate(
    name: str, strand: Literal["+", "-"], s: str, ri: int, ref: Reference, blocks: list[Block],
    flank: int, max_indel: int,
) -> Candidate:  # fmt: skip
    lo, hi = ref.span
    n = hi - lo
    anchors = tuple((b.r0 - lo, b.s0, b.r1 - b.r0) for b in blocks)
    probe = Candidate(
        contig=name, strand=strand, contig_length=len(s), ref=ri, start=0, end=0,
        fragment_length=n, anchors=anchors, anchored=0, context_left=0, context_right=0,
        identity=None, n_inside=0, n_left=0, n_right=0, region="",
    )  # fmt: skip
    start, end = probe.place(0), probe.place(n)
    m = _union(blocks, lo, hi)
    pad = abs((end - start) - n) + INDEL_TOLERANCE
    r0 = max(0, start - flank - pad)
    r1 = min(len(s), max(r0, end + flank + pad))
    region = s[r0:r1]
    identity = None
    if m:
        band = max(INDEL_TOLERANCE, abs((end - start) - n) + INDEL_TOLERANCE)
        identity = round(amplicon_identity(region, ref.fragment, start - r0, band)[0], 3)
    return Candidate(
        contig=name, strand=strand, contig_length=len(s), ref=ri, start=start, end=end,
        fragment_length=n, anchors=anchors, anchored=m,
        context_left=_union(blocks, 0, lo), context_right=_union(blocks, hi, len(ref.sequence)),
        identity=identity, n_inside=s[max(0, start) : max(0, min(len(s), end))].count("N"),
        n_left=_n_run(s, start, -1), n_right=_n_run(s, end, 1), region=region, region_start=r0,
    )  # fmt: skip


def copies_of(candidates: Sequence[Candidate], rule: CopyRule = DEFAULT_RULE) -> list[Candidate]:
    """The candidates that are copies under ``rule``, one per place: a copy found through
    N-tolerant seeds is dropped where a copy by exact blocks covers the same place, and kept
    where only a candidate that is not a copy does (code review 2026-09-29)."""
    copies = [c for c in candidates if is_copy(c, rule)]
    exact = [c for c in copies if not c.masked]
    return exact + [m for m in copies if m.masked and not any(_overlap(m, c) for c in exact)]


def _overlap(a: Candidate, b: Candidate) -> bool:
    return (
        a.contig == b.contig and a.strand == b.strand and min(a.end, b.end) > max(a.start, b.start)
    )


def _best_per_place(found: list[Candidate]) -> list[Candidate]:
    """One candidate per place on the genome (several references may find the same copy)."""
    order = sorted(found, key=lambda c: (-c.anchored, -(c.identity or 0.0), c.ref))
    kept: list[Candidate] = []
    for c in order:
        if not any(_overlap(k, c) for k in kept):
            kept.append(c)
    return kept


# ------------------------------------------------------------------ seeds, blocks, chains
def seed_positions(
    ref_len: int, k: int, lo: int, hi: int, step: int, context_step: int = CONTEXT_STEP
) -> list[int]:
    """Seed starts: every ``step`` in the fragment ``[lo, hi)`` (plus its last k-mer), every
    ``context_step`` in the context on either side."""
    pos = set(range(lo, hi - k + 1, step))
    if hi - k >= lo:
        pos.add(hi - k)
    pos |= set(range(0, lo - k + 1, context_step))
    pos |= set(range(hi, ref_len - k + 1, context_step))
    return sorted(pos)


def _two_pass(
    s: str, ref: str, coarse: list[int], fine: list[int], k: int, reach: int
) -> list[Block]:
    """Blocks from the fine seeds, searched only within ``reach`` of a coarse hit: the
    context's sparse seeds find a flank anywhere in the genome, the dense ones measure it
    (without context both lists are the same and one pass is enough)."""
    blocks = find_blocks(s, ref, coarse, k)
    if coarse == fine or not blocks:
        return blocks
    windows: list[list[int]] = []
    for b in sorted(blocks, key=lambda x: x.s0):
        w0, w1 = max(0, b.s0 - reach), min(len(s), b.s1 + reach)
        if windows and w0 <= windows[-1][1]:
            windows[-1][1] = max(windows[-1][1], w1)
        else:
            windows.append([w0, w1])
    out: list[Block] = []
    for w0, w1 in windows:
        out += [Block(b.r0, b.r1, b.s0 + w0) for b in find_blocks(s[w0:w1], ref, fine, k)]
    return out


def find_blocks(seq: str, ref: str, positions: Iterable[int], k: int) -> list[Block]:
    """Exact seed hits of ``ref`` in ``seq``, merged into maximal blocks per diagonal (k-mers
    occurring more than locate.MAX_OCCURRENCES_PER_SEED times are not informative)."""
    hits: list[tuple[int, int]] = []
    for p in positions:
        kmer = ref[p : p + k]
        if len(kmer) < k or not set(kmer) <= ACGT:
            continue
        hits.extend((s - p, p) for s in _occurrences(seq, kmer))
    hits.sort()
    blocks: list[Block] = []
    for d, p in hits:
        last = blocks[-1] if blocks else None
        if last is not None and last.diag == d and p <= last.r1:
            last.r1 = max(last.r1, p + k)
        else:
            blocks.append(Block(p, p + k, p + d))
    return blocks


def chain_blocks(blocks: list[Block], max_indel: int, max_gap: int) -> list[list[Block]]:
    """Chains of co-linear blocks, most anchored first, within local groups (blocks more than
    ``max_gap`` apart on the genome never share a chain)."""
    out: list[list[Block]] = []
    group: list[Block] = []
    end = 0
    for b in sorted(blocks, key=lambda x: (x.s0, x.r0)):
        if group and b.s0 - end > max_gap:
            out += _chains(group, max_indel)
            group = []
        end = b.s1 if not group else max(end, b.s1)
        group.append(b)
    if group:
        out += _chains(group, max_indel)
    return out


def _chains(group: list[Block], max_indel: int) -> list[list[Block]]:
    """Greedy: the best chain (most reference bases), then the best of what is left."""
    left = list(group)
    out: list[list[Block]] = []
    while left:
        n = len(left)
        score = [b.r1 - b.r0 for b in left]
        prev = [-1] * n
        for j in range(n):
            bj = left[j]
            for i in range(j):
                bi = left[i]
                if bj.r0 <= bi.r0 or bj.s0 <= bi.s0 or abs(bj.diag - bi.diag) > max_indel:
                    continue
                gain = (bj.r1 - bj.r0) - max(0, bi.r1 - bj.r0, bi.s1 - bj.s0)
                if gain > 0 and score[i] + gain > score[j]:
                    score[j], prev[j] = score[i] + gain, i
        j = max(range(n), key=lambda x: score[x])
        picked: list[int] = []
        while j != -1:
            picked.append(j)
            j = prev[j]
        taken = set(picked)
        out.append([left[i] for i in reversed(picked)])
        left = [b for i, b in enumerate(left) if i not in taken]
    return out


def _union(blocks: list[Block], lo: int, hi: int) -> int:
    """Reference bases in ``[lo, hi)`` covered by the blocks."""
    total, end = 0, lo
    for a, b in sorted((max(lo, x.r0), min(hi, x.r1)) for x in blocks):
        a = max(a, end)
        if b > a:
            total, end = total + b - a, b
    return total


def _n_run(s: str, at: int, direction: int) -> int:
    """Length of the N-run next to position ``at`` (-1: just before it, 1: from it on)."""
    i = (min(max(at, 0), len(s)) - 1) if direction < 0 else max(min(at, len(s)), 0)
    n = 0
    while 0 <= i < len(s) and s[i] == "N":
        n, i = n + 1, i + direction
    return n


def _distance(pos: int, a: int, b: int) -> int:
    return 0 if a <= pos < b else min(abs(pos - a), abs(pos - b))


@dataclass(frozen=True)
class Context:
    """The sequence on either side of a locus fragment, cut from a context record around the
    fragment's best copy there (so the fragment need not occur in it exactly)."""

    left: str
    right: str
    contig: str
    start: int  # fragment start on the copy's sense sequence
    anchored: int
    identity: float | None


def context_from(
    seqs: dict[str, str], fragment: str, *, length: int = CONTEXT_LENGTH,
    rule: CopyRule = DEFAULT_RULE,
) -> Context | None:  # fmt: skip
    """Flanks of ``fragment`` from its best whole copy in ``seqs`` (most anchored bases, then
    identity); None when no whole copy reaches rule (a). User, 2026-09-29: the Legionella
    reference fragment is not in NC_002942.5 base for base, so an exact match gave no context."""
    found = [c for c in locate(seqs, [Reference(fragment)], flank=0)
             if c.anchored >= rule.min_anchored and not c.cut]  # fmt: skip
    if not found:
        return None
    best = max(found, key=lambda c: (c.anchored, c.identity or 0.0))
    s = seqs[best.contig].upper()
    s = s if best.strand == "+" else iupac.reverse_complement(s)
    return Context(
        left=s[max(0, best.start - length) : best.start], right=s[best.end : best.end + length],
        contig=best.contig, start=best.start, anchored=best.anchored, identity=best.identity,
    )  # fmt: skip
