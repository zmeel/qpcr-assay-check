"""Semi-global alignment of a whole oligo against a subject window, plus mismatch metrics.

The oligo is aligned end to end (every base is either paired or reported as a gap); the subject
window may have free overhangs on both sides. Scoring defaults follow the BLAST settings used for
the search (match 1, mismatch -3, gap open 5, gap extend 2 with a gap of length k costing
open + k * extend), so a re-alignment never contradicts the seed hit.

Positions along the oligo are 1-based from its 5' end, so "the last 5 nt" are always the 3' end
of the oligo, whatever the strand of the subject.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..oligo import iupac

NEG = -(10**9)


@dataclass(frozen=True)
class Scoring:
    """Alignment scores (gap of length k costs ``gap_open + k * gap_extend``)."""

    match: int = 1
    mismatch: int = -3
    gap_open: int = 5
    gap_extend: int = 2


@dataclass(frozen=True)
class Alignment:
    """An end-to-end alignment of the oligo; gaps are ``-``."""

    q_aln: str
    s_aln: str
    s_start: int  # 0-based index in the subject of the first paired base
    s_end: int  # exclusive
    score: int


@dataclass(frozen=True)
class Metrics:
    """Quality of an alignment along the oligo (positions counted from the 5' end)."""

    oligo_length: int
    n_match: int
    n_mismatch: int
    n_gap: int
    n_ambiguous: int
    defect_positions: tuple[int, ...]
    clean_3prime_nt: int
    mismatches_last5: int
    mismatches_last3: int
    terminal_defect: bool


def sanitise_subject(seq: str) -> str:
    """Upper-case and map anything that is not an IUPAC code to N."""
    return "".join(c if c in iupac.IUPAC_CODES else "N" for c in seq.upper())


def _score(a: str, b: str, sc: Scoring) -> int:
    return sc.match if iupac.compatible(a, b) else sc.mismatch


def align_semiglobal(oligo: str, subject: str, sc: Scoring | None = None) -> Alignment:
    """Align the whole oligo inside ``subject`` (affine gaps, free subject overhangs)."""
    sc = sc or Scoring()
    q, s = oligo.upper(), sanitise_subject(subject)
    n, m = len(q), len(s)
    if n == 0 or m == 0:
        raise ValueError("oligo and subject must not be empty")
    o, e = sc.gap_open, sc.gap_extend
    M = [[NEG] * (m + 1) for _ in range(n + 1)]  # noqa: N806 - matrix names follow the literature
    X = [[NEG] * (m + 1) for _ in range(n + 1)]  # noqa: N806 - oligo base against a gap
    Y = [[NEG] * (m + 1) for _ in range(n + 1)]  # noqa: N806 - subject base against a gap
    for j in range(m + 1):
        M[0][j] = 0  # the alignment may start anywhere in the subject
    for i in range(1, n + 1):
        X[i][0] = -(o + i * e)  # oligo prefix hanging over the start of the window
        for j in range(1, m + 1):
            M[i][j] = max(M[i - 1][j - 1], X[i - 1][j - 1], Y[i - 1][j - 1]) + _score(
                q[i - 1], s[j - 1], sc
            )
            X[i][j] = max(M[i - 1][j] - (o + e), X[i - 1][j] - e, Y[i - 1][j] - (o + e))
            Y[i][j] = max(M[i][j - 1] - (o + e), Y[i][j - 1] - e, X[i][j - 1] - (o + e))

    best, best_j, state = NEG, 0, "M"
    for j in range(m + 1):  # free end in the subject; leftmost best, M preferred over X
        for name, mat in (("M", M), ("X", X)):
            if mat[n][j] > best:
                best, best_j, state = mat[n][j], j, name

    qa: list[str] = []
    sa: list[str] = []
    i, j = n, best_j
    while i > 0:
        if state == "M":
            qa.append(q[i - 1])
            sa.append(s[j - 1])
            target = M[i][j] - _score(q[i - 1], s[j - 1], sc)
            prev = next(
                nm for nm, mat in (("M", M), ("X", X), ("Y", Y)) if mat[i - 1][j - 1] == target
            )
            i, j, state = i - 1, j - 1, prev
        elif state == "X":
            qa.append(q[i - 1])
            sa.append("-")
            cur = X[i][j]
            if cur == M[i - 1][j] - (o + e):
                prev = "M"
            elif cur == X[i - 1][j] - e:
                prev = "X"
            else:
                prev = "Y"
            i, state = i - 1, prev
        else:
            qa.append("-")
            sa.append(s[j - 1])
            cur = Y[i][j]
            if cur == M[i][j - 1] - (o + e):
                prev = "M"
            elif cur == Y[i][j - 1] - e:
                prev = "Y"
            else:
                prev = "X"
            j, state = j - 1, prev
    return Alignment("".join(reversed(qa)), "".join(reversed(sa)), j, best_j, best)


def measure(q_aln: str, s_aln: str) -> Metrics:
    """Mismatches, gaps and 3'-end quality of an alignment (oligo on top, subject below)."""
    if len(q_aln) != len(s_aln):
        raise ValueError("aligned strings must have equal length")
    length = sum(c != "-" for c in q_aln)
    n_match = n_mismatch = n_gap = n_amb = 0
    defects: set[int] = set()
    pos = 0  # oligo bases seen so far
    for qc, sc_ in zip(q_aln, s_aln, strict=True):
        if qc == "-":  # extra subject base between oligo bases
            n_gap += 1
            defects.add(min(pos + 1, length))
            continue
        pos += 1
        if sc_ == "-":  # oligo base without a partner
            n_gap += 1
            defects.add(pos)
        elif iupac.compatible(qc, sc_):
            n_match += 1
            if sc_ not in "ACGT":
                n_amb += 1
        else:
            n_mismatch += 1
            defects.add(pos)
    clean = 0
    for p in range(length, 0, -1):
        if p in defects:
            break
        clean += 1
    return Metrics(
        oligo_length=length,
        n_match=n_match,
        n_mismatch=n_mismatch,
        n_gap=n_gap,
        n_ambiguous=n_amb,
        defect_positions=tuple(sorted(defects)),
        clean_3prime_nt=clean,
        mismatches_last5=sum(p > length - 5 for p in defects),
        mismatches_last3=sum(p > length - 3 for p in defects),
        terminal_defect=length in defects,
    )


def midline(q_aln: str, s_aln: str) -> str:
    """``|`` for a match, ``:`` for a match through an ambiguity code, a space otherwise."""
    out = []
    for qc, sc_ in zip(q_aln, s_aln, strict=True):
        if qc == "-" or sc_ == "-" or not iupac.compatible(qc, sc_):
            out.append(" ")
        else:
            out.append("|" if sc_ in "ACGT" else ":")
    return "".join(out)


@dataclass(frozen=True)
class HomopolymerShift:
    """The subject differs from the oligo only by the length of one single-base run."""

    base: str
    oligo_run: int  # run length in the oligo
    subject_run: int  # run length in the subject
    alignment: Alignment

    @property
    def label(self) -> str:
        return (
            f"poly-{self.base} run {self.oligo_run}→{self.subject_run} (homopolymer length variant)"
        )


def homopolymer_shift(
    oligo: str, subject: str, *, min_run: int = 4, max_shift: int = 3
) -> HomopolymerShift | None:
    """If ``subject`` holds the oligo with one base run longer or shorter, align it that way.

    Such a site is otherwise aligned with mismatches at the end of the run (a gap costs more
    than two mismatches under BLAST-like scoring), which can look like a 3'-end defect although
    the 3' end pairs. Only an exact match of the run-length variant counts; the gap is placed at
    the 5' side of the run (any position in the run is equivalent), keeping the 3' end intact.
    The smallest shift wins.
    """
    q, s = oligo.upper(), subject.upper()
    runs = []
    i = 0
    while i < len(q):
        j = i
        while j < len(q) and q[j] == q[i]:
            j += 1
        if j - i >= min_run and q[i] in "ACGT":
            runs.append((i, j - i))
        i = j
    for shift in sorted((d for d in range(-max_shift, max_shift + 1) if d), key=abs):
        for start, length in runs:
            if length + shift < 2:
                continue
            variant = q[:start] + q[start] * (length + shift) + q[start + length :]
            at = s.find(variant)
            if at < 0:
                continue
            seg = s[at : at + len(variant)]
            if shift > 0:  # the subject's run is longer: extra subject bases against oligo gaps
                q_aln, s_aln = q[:start] + "-" * shift + q[start:], seg
            else:  # shorter: oligo bases against subject gaps
                q_aln, s_aln = q, seg[:start] + "-" * (-shift) + seg[start:]
            aln = Alignment(q_aln, s_aln, at, at + len(variant), 0)
            return HomopolymerShift(q[start], length, length + shift, aln)
    return None
