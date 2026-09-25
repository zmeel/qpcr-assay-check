"""Graded mismatch classes for an oligo binding site (docs/MISMATCH_CLASSES.md).

Classes: perfect, tolerated, at_risk, likely_failure, indeterminate. Every rule is taken from
Stadhouders et al., J Mol Diagn 2010;12:109-117 (single mismatches in the last 5 nt, Table 1,
Taq polymerase on DNA) or Lefever et al., Clin Chem 2013;59:1470-1480 (positions beyond 5 and
numbers of mismatches), both read in full (FEATURE_IDEAS #9). Where neither paper gives a basis
(gaps/bulges, ambiguity codes in the genome, probe mismatches), the class is ``indeterminate`` or
the rule says so; nothing here predicts a Cq value.

The alignment is read in oligo orientation (5'->3'), the site in the same sense as the oligo.
A mismatch type is written primer-template (Stadhouders' convention): the primer base, then the
base on the template strand facing it, i.e. the complement of the site base.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import iupac

PERFECT, TOLERATED, AT_RISK, FAILURE, INDETERMINATE = (
    "perfect", "tolerated", "at_risk", "likely_failure", "indeterminate",
)  # fmt: skip
ORDER = {PERFECT: 0, TOLERATED: 1, AT_RISK: 2, FAILURE: 3, INDETERMINATE: 4}
DETECTABLE = (PERFECT, TOLERATED)
UNDETERMINED_RULES = ("R6", "R9")  # indeterminate sites counted neither detected nor escaped

# Stadhouders 2010, Table 1 (p. 116), Taq DNA polymerase on DNA ("standard"), both primers:
# type groups x position groups -> "avoid" (True) or "acceptable" (False; effect "generally
# <2,0 Ct"). G1 A-A/A-G/G-A/G-G/C-C; G2 T-T/T-C/C-T; G3 C-A/A-C/G-T/T-G.
_GROUP = {
    **dict.fromkeys(("A-A", "A-G", "G-A", "G-G", "C-C"), "G1"),
    **dict.fromkeys(("T-T", "T-C", "C-T"), "G2"),
    **dict.fromkeys(("C-A", "A-C", "G-T", "T-G"), "G3"),
}
_AVOID = {
    ("G1", "terminal"): True, ("G1", "penultimate"): True, ("G1", "3-5"): False,
    ("G2", "terminal"): True, ("G2", "penultimate"): False, ("G2", "3-5"): False,
    ("G3", "terminal"): False, ("G3", "penultimate"): False, ("G3", "3-5"): False,
}  # fmt: skip
_COMPLEMENT = {"A": "T", "C": "G", "G": "C", "T": "A"}

STADHOUDERS = "Stadhouders 2010, Table 1 (Taq on DNA)"
LEFEVER = "Lefever 2013"
CAVEAT = (
    "Classes follow Stadhouders 2010 Table 1 for Taq polymerase on DNA and Lefever 2013; the "
    "size of a mismatch effect differs between master mixes, and in one-step RT-PCR a mismatch "
    "in the reverse (RT) primer can matter less or more than on DNA. A wet-lab check decides."
)


@dataclass(frozen=True)
class Grade:
    cls: str
    rule: str  # e.g. "R1", "R3"
    note: str


@dataclass(frozen=True)
class _Mismatch:
    pos: int  # 1 = the 3'-terminal base
    kind: str  # primer-template, e.g. "C-A"; "" if a base is degenerate or ambiguous


def worst(*classes: str) -> str:
    return max(classes, key=lambda c: ORDER[c])


def _position_group(pos: int) -> str:
    return "terminal" if pos == 1 else "penultimate" if pos == 2 else "3-5"


def _single_in_last5(m: _Mismatch) -> Grade:
    """R1: one mismatch in the last 5 nt, Stadhouders Table 1 (Taq on DNA)."""
    group = _GROUP.get(m.kind, "G1")  # unknown type (degenerate base): the severe group
    avoid = _AVOID[(group, _position_group(m.pos))]
    cls = (FAILURE if m.pos == 1 else AT_RISK) if avoid else TOLERATED
    note = f"{m.kind or 'unknown type'} at -{m.pos} ({group}; {STADHOUDERS})"
    if m.pos == 4:
        note += "; position -4 was not tested (interpolated from positions 3 and 5)"
    return Grade(cls, "R1", note)


def _mismatches(q_aln: str, s_aln: str) -> tuple[list[_Mismatch], list[_Mismatch], bool]:
    """Mismatches by position from the 3' end; ambiguity codes in the site that are compatible
    with the oligo and fall in the last 5 nt (a match or a mismatch, the genome does not say);
    whether there is a gap. An ambiguity code further from the 3' end is read as a match; one
    that cannot pair with the oligo base is a mismatch. An unaligned end of a worst-case site
    ('.', the window could not be fetched) is a mismatch of unknown type."""
    length = sum(c != "-" for c in q_aln)
    pos = 0
    out: list[_Mismatch] = []
    amb: list[_Mismatch] = []
    gap = False
    for qc, sc in zip(q_aln.upper(), s_aln.upper(), strict=True):
        if qc == "-":
            gap = True
            continue
        pos += 1
        from_3 = length - pos + 1
        if sc == "-":
            gap = True
            continue
        if sc == ".":
            out.append(_Mismatch(from_3, ""))
            continue
        if iupac.compatible(qc, sc):
            if sc not in "ACGT" and from_3 <= 5:
                amb.append(_Mismatch(from_3, ""))
            continue
        kind = f"{qc}-{_COMPLEMENT[sc]}" if qc in "ACGT" and sc in "ACGT" else ""
        out.append(_Mismatch(from_3, kind))
    return out, amb, gap


def _with_ambiguity(grade: Callable[[list[_Mismatch]], Grade], mm: list[_Mismatch],
                    amb: list[_Mismatch]) -> Grade:
    """R6: grade with the ambiguity codes in the last 5 nt read as matches and as mismatches.
    Only when that decides between detectable and not is the site indeterminate; a class that
    holds either way is kept, so an ambiguity code never hides a real failure."""
    as_match = grade(mm)
    if not amb:
        return as_match
    as_mismatch = grade(sorted(mm + amb, key=lambda m: m.pos))
    if as_match.cls not in DETECTABLE:
        return Grade(as_match.cls, as_match.rule, as_match.note
                     + "; an ambiguity code in the last 5 nt may make it worse")  # fmt: skip
    if as_mismatch.cls in DETECTABLE:
        return as_mismatch
    return Grade(INDETERMINATE, "R6", "ambiguity code in the genome in the last 5 nt decides "
                 "whether the site is detectable")  # fmt: skip


def _grade_primer_mm(mm: list[_Mismatch]) -> Grade:
    if not mm:
        return Grade(PERFECT, "", "")
    last5 = [m for m in mm if m.pos <= 5]
    if len(mm) == 1:
        m = mm[0]
        if m.pos <= 5:
            return _single_in_last5(m)
        return Grade(TOLERATED, "R2", f"one mismatch at -{m.pos}: "
                     + ("moderate effect, can be tolerated" if m.pos <= 8 else "almost negligible")
                     + f" ({LEFEVER}; one mix)")  # fmt: skip
    low_input = "; worse near the limit of detection (Lefever 2013)"
    if any(m.pos == 1 for m in mm) and len(last5) >= 2:
        return Grade(FAILURE, "R3", f"3'-terminal mismatch plus another in the last 5 nt "
                     f"({STADHOUDERS}; {LEFEVER}){low_input}")  # fmt: skip
    singles = [_single_in_last5(m).cls for m in last5]
    if len(mm) == 2:
        return Grade(worst(AT_RISK, *singles), "R3", f"2 mismatches ({LEFEVER}){low_input}")
    if len(mm) == 3:
        cls = FAILURE if last5 else AT_RISK
        return Grade(cls, "R3", f"3 mismatches ({LEFEVER}: depends on position){low_input}")
    positions = sorted(m.pos for m in mm)
    adjacent = positions[-1] - positions[0] == len(positions) - 1
    if len(mm) == 4 and adjacent and not last5:
        return Grade(AT_RISK, "R3", f"4 adjacent mismatches away from the 3' end ({LEFEVER} "
                     f"exception, seen near the 5' end; class ours){low_input}")  # fmt: skip
    return Grade(FAILURE, "R3", f"{len(mm)} mismatches ({LEFEVER}: blocked almost completely)")


def grade_primer(q_aln: str, s_aln: str) -> Grade:
    """The class of one primer site (rules R1-R3, R5, R6)."""
    mm, amb, gap = _mismatches(q_aln, s_aln)
    if gap:
        return Grade(INDETERMINATE, "R5", "gap or bulge: neither source tested insertions or "
                     "deletions")  # fmt: skip
    return _with_ambiguity(_grade_primer_mm, mm, amb)


def grade_probe(q_aln: str, s_aln: str, *, mgb: bool) -> Grade:
    """R9: neither source tested probe mismatches. The current rule is kept (at most 1 mismatch,
    none in the last 5 nt, no gap = tolerated); MGB probes with one mismatch are indeterminate."""
    mm, amb, gap = _mismatches(q_aln, s_aln)
    if gap:
        return Grade(INDETERMINATE, "R5", "gap or bulge in the probe site")

    def by_mismatches(mm: list[_Mismatch]) -> Grade:
        if not mm:
            return Grade(PERFECT, "", "")
        if mgb and len(mm) == 1:
            return Grade(INDETERMINATE, "R9", "one mismatch in an MGB probe site: no source "
                         "for its effect (MGB probes are more mismatch-selective); "
                         "undetermined")  # fmt: skip
        if len(mm) == 1 and mm[0].pos > 5:
            return Grade(TOLERATED, "R9", "one probe mismatch outside the last 5 nt (current "
                         "rule; no source)")  # fmt: skip
        return Grade(AT_RISK, "R9", "probe mismatches beyond the current rule (no source)")

    return _with_ambiguity(by_mismatches, mm, amb)


def pair_fails(n_forward: int, n_reverse: int) -> bool:
    """R8 (Lefever 2013 p. 1478): 3 mismatches with >= 2 in the other primer, or 4 with >= 1,
    blocked amplification almost completely."""
    lo, hi = sorted((n_forward, n_reverse))
    return (hi >= 3 and lo >= 2) or (hi >= 4 and lo >= 1)


def grade_fields(q_aln: str, s_aln: str, role: str, *, mgb: bool) -> dict[str, str]:
    """SiteResult fields ``grade``, ``grade_rule``, ``grade_note`` for a target-site alignment."""
    g = grade_probe(q_aln, s_aln, mgb=mgb) if role == "probe" else grade_primer(q_aln, s_aln)
    return {"grade": g.cls, "grade_rule": g.rule, "grade_note": g.note}


def is_mgb(modifications: list[str]) -> bool:
    return any(m.upper() == "MGB" for m in modifications)
