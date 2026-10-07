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
from typing import Any

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
KWOK = "Kwok 1990, Table III"
HUANG = "Huang 1992"
KUTYAVIN = "Kutyavin 2000"
# Terminal G2 (T-T/T-C/C-T): Stadhouders "avoid" (3.77-4.75 Ct with Taq on DNA, pp. 111-113), but
# Kwok et al. 1990 (Nucleic Acids Res 18:999, Table III p. 1001) amplified all three as well as a
# perfect match and Huang et al. 1992 (Nucleic Acids Res 20:4567, p. 4570) found C-T the most
# easily extended mispair (f_ext 2e-2): a delay rather than a block, so at risk (user,
# 2026-10-02), not likely failure.
_TERMINAL_G2_NOTE = (
    f"terminal G2: {STADHOUDERS} 'avoid' (3.8-4.8 Ct), but {KWOK} amplified it like a match and "
    f"{HUANG} found C-T the most easily extended mispair: at risk"
)
# Terminal G3 (C-A/A-C/G-T/T-G): Stadhouders and Kwok (yield 1.0) agree it is acceptable; Huang
# measured 1e-3 to 1e-4 single-step extension (kinetics, not PCR yield, p. 4567): printed only.
_TERMINAL_G3_NOTE = (
    f"terminal G3: acceptable in {STADHOUDERS} and {KWOK}; {HUANG} measured 1e-3 to 1e-4 "
    "single-step extension efficiency (enzyme kinetics, not PCR yield)"
)
# Kutyavin et al. 2000 (Nucleic Acids Res 28:655): the 3'-MGB folds into the minor groove of the
# terminal 5-6 bp (p. 655) and can slide 1-2 bp toward the 5' end (pp. 657, 661); a mismatch
# there is much more destabilising (T/G: dTm 15 vs 6 C, ddG 5.6 vs 2.0 kcal/mol, p. 657; 7 nt
# from the 3' end dTm 11 vs 6.5 C, p. 660), a 12-mer with a mismatch 5 nt from the 3' end lost
# its signal at 55-70 C (Fig. 7, p. 659); at 11 nt from the 3' end the MGB added nothing
# (p. 661). Exceptions the authors could not explain: A/C at the terminal base and C/A at
# position 6 discriminated less (p. 657).
MGB_REGION = 7
KLUNGTHONG = "Klungthong 2010"
# Unmodified probes: from this many mismatches on, no stable probe duplex is expected (user
# decision 2026-10-07, after an 11-mismatch unmodified probe site was graded only at risk in the
# Legionella run of 2026-10-02). Expert judgement, the same standing as the MGB rule above; the
# only measurement nearby is Klungthong et al. 2010 (J Clin Virol 48:91-95), where an unmodified
# 30-mer probe with two mismatches still detected every sample but its mean Ct gap to the
# reference target widened from 5.58 to 9.28 (Table 3, p. 93), which is why two is at risk.
UNMODIFIED_PROBE_FAIL = 3
# Probe lengths and chemistry the probe-deletion data (R5c) cover: Otwell et al. 2025 measured
# 25-28 nt linear ZEN/IBFQ probes only, at 55 C annealing over 50 cycles.
R5C_MIN_PROBE_NT = 25
# Deletion lengths Otwell's workbook has no template for (1, 3, 4, 6, 7 and 8 nt were
# measured): the class for these is interpolated, not measured.
UNTESTED_DELETIONS = frozenset({2, 5})
LEFEVER = "Lefever 2013"
OTWELL = "Otwell 2025"
# Lefever 2013 tested mismatches in the 3'-most 16 nt of 20-mers (p. 1472); Otwell et al. 2025
# (Front Cell Infect Microbiol 15:1524025, supplementary Table 2, 55 C annealing, 900 nM primers)
# measured primers whose extra mismatches lay beyond that region: 3-4 of them alone shifted Ct by
# at most 2.2, while 4 mismatches with 3 at the 5' end (-20..-22) and one within the region
# shifted Ct by -0.1 to +6.4 (mostly +3 to +6), never undetected at 50 copies.
TESTED_REGION = 16
OUTER_MEASURED = 4  # Otwell 2025 measured 3-4 mismatches beyond -16; more: at least at risk
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
    cls = (FAILURE if m.pos == 1 and group != "G2" else AT_RISK) if avoid else TOLERATED
    note = f"{m.kind or 'unknown type'} at -{m.pos} ({group}; {STADHOUDERS})"
    if m.pos == 1 and group == "G2":
        note += f"; {_TERMINAL_G2_NOTE}"
    elif m.pos == 1 and group == "G3":
        note += f"; {_TERMINAL_G3_NOTE}"
    if m.pos == 4:
        note += "; position -4 was not tested (interpolated from positions 3 and 5)"
    return Grade(cls, "R1", note)


def _terminal_gap_columns(q_aln: str, s_aln: str) -> set[int]:
    """Columns where an oligo base at either end has no partner in the genome (the alignment
    starts or ends with genome gaps): read as mismatches at those positions, not as a gap
    (user, 2026-09-26: a 5'-terminal overhang made a poly-A 7->8 site 'indeterminate')."""
    q, s = q_aln.upper(), s_aln.upper()
    cols: set[int] = set()
    for order in (range(len(q)), range(len(q) - 1, -1, -1)):
        for i in order:
            if q[i] == "-":
                break
            if s[i] != "-":
                break
            cols.add(i)
    return cols


def _mismatches(q_aln: str, s_aln: str) -> tuple[list[_Mismatch], list[_Mismatch], bool]:
    """Mismatches by position from the 3' end; ambiguity codes in the site that are compatible
    with the oligo and fall in the last 5 nt (a match or a mismatch, the genome does not say);
    whether there is a gap. An ambiguity code further from the 3' end is read as a match; one
    that cannot pair with the oligo base is a mismatch. An unaligned end of a worst-case site
    ('.', the window could not be fetched) is a mismatch of unknown type."""
    length = sum(c != "-" for c in q_aln)
    ends = _terminal_gap_columns(q_aln, s_aln)
    pos = 0
    out: list[_Mismatch] = []
    amb: list[_Mismatch] = []
    gap = False
    for i, (qc, sc) in enumerate(zip(q_aln.upper(), s_aln.upper(), strict=True)):
        if qc == "-":
            gap = True
            continue
        pos += 1
        from_3 = length - pos + 1
        if sc == "-":
            if i in ends:  # an oligo end without a partner base: a mismatch there, not a gap
                out.append(_Mismatch(from_3, ""))
            else:
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


def _with_ambiguity(
    grade: Callable[[list[_Mismatch]], Grade], mm: list[_Mismatch], amb: list[_Mismatch]
) -> Grade:
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


def _with_gap(by_mismatches: Grade, note: str) -> Grade:
    """R5 with mismatches: a gap can only make a site worse, so a class that is already not
    detectable from the mismatches alone stands (user, 2026-09-26: 7 mismatches and a gap were
    'indeterminate'); otherwise the gap leaves the site indeterminate."""
    if by_mismatches.cls in (AT_RISK, FAILURE):
        return Grade(by_mismatches.cls, by_mismatches.rule,
                     f"{by_mismatches.note}; plus a gap")  # fmt: skip
    return Grade(INDETERMINATE, "R5", note)


def _grade_primer_mm(mm: list[_Mismatch]) -> Grade:
    """R1-R3 on the mismatches within the tested region (the 3'-most ``TESTED_REGION`` nt);
    mismatches beyond it only raise the class to at risk, and alone leave it tolerated
    (R3b, Otwell 2025; the user's decision after comparing the classes with its data)."""
    inner = [m for m in mm if m.pos <= TESTED_REGION]
    outer = [m for m in mm if m.pos > TESTED_REGION]
    beyond_data = len(outer) > OUTER_MEASURED
    unmeasured = (
        f"; more than {OUTER_MEASURED} beyond -{TESTED_REGION} lies outside the measured data"
        if beyond_data else ""
    )  # fmt: skip
    if outer and not inner:
        cls = AT_RISK if beyond_data else TOLERATED
        return Grade(cls, "R3b", f"{len(outer)} mismatch(es) only beyond -{TESTED_REGION}, "
                     f"outside the region {LEFEVER} tested; {OTWELL}: 3-4 such mismatches shifted "
                     "Ct by at most 2.2 (one test setup, permissive conditions)"
                     + unmeasured)  # fmt: skip
    g = _grade_inner(inner, adjacent_exception=not outer)
    if not outer:
        return g
    note = (
        f"{g.note}; plus {len(outer)} mismatch(es) beyond -{TESTED_REGION} ({OTWELL}: with one "
        "mismatch within the region, mostly +3 to +6 Ct)" + unmeasured
    )
    return Grade(worst(g.cls, AT_RISK), f"{g.rule}+R3b" if g.rule else "R3b", note)


def _grade_inner(mm: list[_Mismatch], adjacent_exception: bool = True) -> Grade:
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
        # none in the last 5 nt: at risk until 2026-09-30; Lefever Fig. 6 median about 15 dCq
        # (read from the figure) and Otwell 2025 +6 to +7 Ct, 2 of 3 missed at 50 copies
        return Grade(FAILURE, "R3", f"3 mismatches within the 3'-most {TESTED_REGION} nt "
                     f"({LEFEVER}; {OTWELL}: +6 to +7 Ct without one in the last 5 nt)"
                     f"{low_input}")  # fmt: skip
    positions = sorted(m.pos for m in mm)
    adjacent = positions[-1] - positions[0] == len(positions) - 1
    # Lefever's exception is 4 mismatches in all; with more beyond the tested region it does not
    # apply (Otwell 2025: 4 adjacent at -13..-16 plus 3 at the 5' end, +13.6 Ct)
    if len(mm) == 4 and adjacent and not last5 and adjacent_exception:
        return Grade(AT_RISK, "R3", f"4 adjacent mismatches away from the 3' end ({LEFEVER} "
                     f"exception, seen near the 5' end; class ours){low_input}")  # fmt: skip
    return Grade(FAILURE, "R3", f"{len(mm)} mismatches ({LEFEVER}: blocked almost completely)")


@dataclass(frozen=True)
class _Bulge:
    size: int  # bases inserted in or missing from the genome's run
    run_end_from_3: int  # position (from the 3' end) of the run's 3'-most base in the oligo


def _homopolymer_bulge(q_aln: str, s_aln: str, min_run: int = 3) -> _Bulge | None:
    """The gap, if it is one block that only changes the length of a single-base run of at least
    ``min_run`` bases in the oligo (the position of such a gap within the run is arbitrary)."""
    q, s = q_aln.upper(), s_aln.upper()
    ends = _terminal_gap_columns(q_aln, s_aln)
    cols = [i for i, (a, b) in enumerate(zip(q, s, strict=True))
            if (a == "-" or b == "-") and i not in ends]  # fmt: skip
    if not cols or cols[-1] - cols[0] + 1 != len(cols):
        return None
    in_q = q[cols[0]] == "-"
    if any((q[i] == "-") != in_q for i in cols):
        return None  # gaps on both sides: not a simple bulge
    gapped = {(s if in_q else q)[i] for i in cols}
    if len(gapped) != 1 or not gapped <= set("ACGT"):
        return None
    base = gapped.pop()
    oligo = q.replace("-", "")
    before = sum(c != "-" for c in q[: cols[0]])  # oligo bases 5' of the gap
    # the run of `base` in the oligo that the gap touches
    lo = hi = before
    if not in_q:
        hi = before + len(cols)
    while lo > 0 and oligo[lo - 1] == base:
        lo -= 1
    while hi < len(oligo) and oligo[hi] == base:
        hi += 1
    run = hi - lo
    if run < min_run or (not in_q and run <= len(cols)):
        return None
    return _Bulge(len(cols), len(oligo) - (hi - 1))


def grade_primer(q_aln: str, s_aln: str) -> Grade:
    """The class of one primer site (rules R1-R3, R5, R6)."""
    mm, amb, gap = _mismatches(q_aln, s_aln)
    if gap:
        bulge = _homopolymer_bulge(q_aln, s_aln)
        if bulge is None:
            return _with_gap(_with_ambiguity(_grade_primer_mm, mm, amb), "gap or bulge: neither "
                             "source tested insertions or deletions")  # fmt: skip
        # R5b (advisor subagent, 2026-09-26; class ours): no PCR study measured a homopolymer
        # length difference in a primer site; bulges inside a run are comparatively stable
        # (Zhu & Wartell 1999) and primers are seen to slip across such runs (Elbrecht 2018)
        near_3 = bulge.run_end_from_3 <= 3
        cls = AT_RISK if bulge.size == 1 and not near_3 else FAILURE
        what = f"{bulge.size}-base homopolymer length difference" + (
            ", run reaching the last 3 nt" if near_3 else f", run ending at -{bulge.run_end_from_3}"
        )
        if mm:
            other = _with_ambiguity(_grade_primer_mm, mm, amb)
            cls = worst(cls, other.cls)
            what += f", plus {len(mm)} mismatch(es)"
        return Grade(cls, "R5b", f"{what}: no PCR study measured this (class ours; a wet-lab "
                     "check decides)")  # fmt: skip
    return _with_ambiguity(_grade_primer_mm, mm, amb)


def grade_probe(q_aln: str, s_aln: str, *, mgb: bool) -> Grade:
    """R9. MGB probes (the MGB at the 3' end, as in Kutyavin 2000 and TaqMan MGB probes): one
    mismatch in the 3'-most ``MGB_REGION`` nt likely failure (Kutyavin 2000; user, 2026-10-02),
    further toward the 5' end undetermined; 2 or more likely failure (expert judgement). Other
    probes: 1 mismatch outside the last 5 nt tolerated, else at risk (expert judgement)."""
    mm, amb, gap = _mismatches(q_aln, s_aln)

    def by_mismatches(mm: list[_Mismatch]) -> Grade:
        if not mm:
            return Grade(PERFECT, "", "")
        if mgb and len(mm) == 1 and mm[0].pos <= MGB_REGION:
            return Grade(FAILURE, "R9", f"one mismatch at -{mm[0].pos}, under the MGB (the "
                         f"3'-most {MGB_REGION} nt): MGB probes discriminate such a mismatch "
                         f"strongly, a 12-mer lost its signal at 55-70 C ({KUTYAVIN}, pp. 657-660, "
                         "Fig. 7); A/C at the terminal base and C/A at -6 discriminated less "
                         "there")  # fmt: skip
        if mgb and len(mm) == 1:
            return Grade(INDETERMINATE, "R9", f"one mismatch at -{mm[0].pos} in an MGB probe, "
                         f"outside the MGB region (the 3'-most {MGB_REGION} nt): the MGB adds no "
                         f"discrimination there ({KUTYAVIN}, p. 661), whether the short probe "
                         "still binds is not known; undetermined")  # fmt: skip
        if mgb:
            return Grade(FAILURE, "R9", f"{len(mm)} mismatches in a short MGB probe: no stable "
                         "probe duplex expected; expert judgement from MGB probe chemistry, no "
                         "quantitative source")  # fmt: skip
        if len(mm) == 1 and mm[0].pos > 5:
            return Grade(TOLERATED, "R9", "one probe mismatch outside the last 5 nt: a longer "
                         "unmodified probe usually tolerates it; expert judgement, no "
                         "quantitative source")  # fmt: skip
        if len(mm) >= UNMODIFIED_PROBE_FAIL:
            return Grade(FAILURE, "R9", f"{len(mm)} mismatches in an unmodified probe: no stable "
                         f"probe duplex expected from {UNMODIFIED_PROBE_FAIL} mismatches on; "
                         "expert judgement, no quantitative source (user decision 2026-10-07; "
                         f"{KLUNGTHONG} measured two, still detected)")  # fmt: skip
        return Grade(AT_RISK, "R9", "one probe mismatch in the last 5 nt, or two anywhere: "
                     f"expert judgement; {KLUNGTHONG} measured two mismatches in an unmodified "
                     "30-mer probe, every sample still detected but the Ct gap widened from "
                     "5.58 to 9.28")  # fmt: skip

    if gap:
        deleted, inserted = _probe_gap_bases(q_aln, s_aln)
        if deleted and not inserted:
            return _probe_deletion(
                deleted,
                mm,
                _with_ambiguity(by_mismatches, mm, amb),
                mgb=mgb,
                probe_nt=len(q_aln.replace("-", "")),
            )
        return _with_gap(_with_ambiguity(by_mismatches, mm, amb), "gap or bulge in the probe site")
    return _with_ambiguity(by_mismatches, mm, amb)


def _probe_gap_bases(q_aln: str, s_aln: str) -> tuple[int, int]:
    """Probe bases without a template partner (a deletion in the template, not at the probe's
    ends) and template bases without a probe partner (an insertion in the template)."""
    ends = _terminal_gap_columns(q_aln, s_aln)
    deleted = sum(1 for i, (q, s) in enumerate(zip(q_aln, s_aln, strict=True))
                  if s == "-" and q != "-" and i not in ends)  # fmt: skip
    inserted = sum(1 for q in q_aln if q == "-")
    return deleted, inserted


def _r5c_scope(mgb: bool, probe_nt: int) -> str:
    """What the probe-deletion data do not cover for this probe (empty when they do).

    Otwell et al. 2025 measured 25-28 nt linear ZEN/IBFQ probes at 55 C over 50 cycles; there is
    no measurement of a deletion under an MGB or other Tm-raising probe, nor under a probe
    shorter than that (advisor's literature search, 2026-10-07: searches of PubMed and Europe PMC
    for a probe-site deletion return that study alone).
    """
    if mgb:
        return ("; no measured data: the deletion classes come from unmodified 25-28 nt probes, "
                "and no study measured a deletion under an MGB probe")  # fmt: skip
    if probe_nt < R5C_MIN_PROBE_NT:
        return (f"; no measured data for a probe of {probe_nt} nt: the deletion classes come from "
                f"{R5C_MIN_PROBE_NT}-28 nt probes, which keep longer paired arms either side of "
                "the gap")  # fmt: skip
    return ""


def _probe_deletion(
    deleted: int, mm: list[_Mismatch], by_mismatches: Grade, *, mgb: bool = False, probe_nt: int = 0
) -> Grade:
    """R5c: a deletion in the template within the probe site (probe bases without a partner),
    graded from the deletions Otwell et al. 2025 measured in probe sites (section "mismatches in
    probe binding region"): C4 ORF8 (26-nt probe site) <= 6 nt deleted: Ct shift <= 5, no
    failed detection even at 50 copies; 7 nt: mean Ct > 40 at 50 copies; 8 nt: not detected at
    any level. ncov_n_gene, 3 nt: about +3 Ct, detected. Young-S, 3 nt plus three mismatches:
    not detected at any level. Yale 69/70 del, 6 nt: not detected at any level. Where the
    assays disagree (6 nt) the worse outcome is taken. Insertions in the template were not
    tested and stay R5 indeterminate."""
    where = f"{deleted} base(s) of the probe site deleted in the template"
    if by_mismatches.cls == FAILURE:
        return Grade(FAILURE, by_mismatches.rule, f"{by_mismatches.note}; plus {where}")
    if deleted >= 6:
        return Grade(FAILURE, "R5c", f"{where}: {OTWELL} measured 6 nt not detected (Yale 69/70 "
                     "del; tolerated in C4 ORF8, the worse is taken), 7 nt Ct > 40 at 50 "
                     "copies and 8 nt not detected (C4 ORF8)")  # fmt: skip
    if len(mm) >= 3:
        return Grade(FAILURE, "R5c", f"{where} and {len(mm)} mismatches: {OTWELL} measured "
                     "a 3-nt deletion with three mismatches not detected at any level "
                     "(Young-S)")  # fmt: skip
    note = (
        f"{where}: {OTWELL} measured Ct shifts of about 3 (3 nt, ncov_n_gene) to at most 5 "
        "(<= 6 nt, C4 ORF8), detected at 50 copies, at 55 C over 50 cycles"
    )
    if deleted in UNTESTED_DELETIONS:
        note += (f"; {deleted} nt was never tested (1, 3, 4 and 6 nt were), so this class is "
                 "interpolated")  # fmt: skip
    if mm:
        note += f"; with {len(mm)} mismatch(es) as well, a combination not measured"
    return Grade(AT_RISK, "R5c", note + _r5c_scope(mgb, probe_nt))


def tested_mismatches(site: Any) -> int:
    """Mismatches of a primer site within the 3'-most ``TESTED_REGION`` nt, the region the pair
    rule was measured on (a site without alignment strings: all its mismatches)."""
    q, s = getattr(site, "q_aln", None), getattr(site, "s_aln", None)
    if not q or not s:
        return int(site.n_mismatch)
    return sum(1 for m in _mismatches(q, s)[0] if m.pos <= TESTED_REGION)


def pair_fails(n_forward: int, n_reverse: int) -> bool:
    """R8 (Lefever 2013 p. 1478): 3 mismatches with >= 2 in the other primer, or 4 with >= 1,
    blocked amplification almost completely; counted within the 3'-most 16 nt."""
    lo, hi = sorted((n_forward, n_reverse))
    return (hi >= 3 and lo >= 2) or (hi >= 4 and lo >= 1)


def grade_fields(q_aln: str, s_aln: str, role: str, *, mgb: bool) -> dict[str, str]:
    """SiteResult fields ``grade``, ``grade_rule``, ``grade_note`` for a target-site alignment."""
    g = grade_probe(q_aln, s_aln, mgb=mgb) if role == "probe" else grade_primer(q_aln, s_aln)
    return {"grade": g.cls, "grade_rule": g.rule, "grade_note": g.note}


def is_mgb(modifications: list[str]) -> bool:
    return any(m.upper() == "MGB" for m in modifications)


# ------------------------------------------------------------------ genome outcome
OUTCOMES = ("likely failure", "at risk", "undetermined", "detectable")  # most concerning first


def combination_outcome(forward: Any, probe: Any, reverse: Any,
                        bulges: bool = False) -> tuple[str, bool]:  # fmt: skip
    """The outcome for a genome from its three best-copy sites (anything with ``grade``,
    ``grade_rule``, ``n_mismatch`` and ``note``), as the variant analysis judges a copy: the
    worst site state, and the primer-pair rule (R8). Also whether the pair rule decides it.
    Sites made before the classes (no grade) give ''."""
    sites = (forward, probe, reverse)
    if any(s.grade is None for s in sites):
        return "", False
    pair = pair_fails(tested_mismatches(forward), tested_mismatches(reverse))

    def state(s: Any) -> str:
        if bulges and s.note and s.n_mismatch == 0:  # run-length variant, lenient setting
            return "detectable"
        if s.grade in DETECTABLE:
            return "detectable"
        if s.grade == INDETERMINATE:
            if s.note:  # homopolymer bulge: its own setting
                return "detectable" if bulges and s.n_mismatch == 0 else "at risk"
            if s.grade_rule in UNDETERMINED_RULES:
                return "undetermined"
            return "at risk"  # an unexplained gap: not detected, no published size
        return "likely failure" if s.grade == FAILURE else "at risk"

    states = [state(s) for s in sites]
    if pair:
        states.append("likely failure")
    return min(states, key=OUTCOMES.index), pair and not any(
        x == "likely failure" for x in states[:3]
    )


# ------------------------------------------------------------------ lab evidence
def site_string(q_aln: str, s_aln: str) -> str:
    """The site as the report writes it against the oligo: '.' for a matching base (an
    ambiguity code that can pair counts as matching), the genome's base for a mismatch, '-' for
    a gap; the key of a lab-evidence entry."""
    out = []
    for qc, sc in zip(q_aln.upper(), s_aln.upper(), strict=True):
        if qc == "-" or sc == "-":
            out.append(sc if sc != "-" else "-")
        elif sc == "." or iupac.compatible(qc, sc):
            out.append(".")
        else:
            out.append(sc)
    return "".join(out)


def lab_fields(lab: Any, in_silico: dict[str, str]) -> dict[str, str]:
    """A laboratory result replaces the in silico class (rule LAB): detected = tolerated,
    not detected = likely failure; the in silico class stays in the note."""
    cls = TOLERATED if lab.outcome == "detected" else FAILURE
    was = in_silico["grade"].replace("_", " ")
    outcome = "detected" if lab.outcome == "detected" else "not detected"
    return {
        "grade": cls,
        "grade_rule": "LAB",
        "grade_note": f"laboratory result: {outcome} ({lab.note}); in silico: {was}",
    }
