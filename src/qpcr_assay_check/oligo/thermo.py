"""Thermodynamic calculations (primer3-py) and a small nearest-neighbour ΔG helper.

Unit conventions: temperatures in °C, concentrations as configured (mM / nM), and all free
energies and enthalpies in **kcal/mol**. primer3-py itself reports cal/mol; the conversion
happens exactly once, in :func:`_wrap`.
"""

from __future__ import annotations

from dataclasses import dataclass

import primer3

from ..config import ReactionConditions

# SantaLucia (1998) unified nearest-neighbour ΔG°37 (kcal/mol), keyed by 5'->3' dinucleotide.
_NN_DG37: dict[str, float] = {
    "AA": -1.00, "TT": -1.00,
    "AT": -0.88,
    "TA": -0.58,
    "CA": -1.45, "TG": -1.45,
    "GT": -1.44, "AC": -1.44,
    "CT": -1.28, "AG": -1.28,
    "GA": -1.30, "TC": -1.30,
    "CG": -2.17,
    "GC": -2.24,
    "GG": -1.84, "CC": -1.84,
}  # fmt: skip


@dataclass(frozen=True)
class Conditions:
    """Reaction conditions in the form primer3 expects."""

    mv_conc: float
    dv_conc: float
    dntp_conc: float
    primer_nM: float
    probe_nM: float
    temp_c: float
    tm_method: str
    salt_correction: str

    @classmethod
    def from_reaction(cls, r: ReactionConditions) -> Conditions:
        """Build from the validated configuration."""
        return cls(
            mv_conc=r.na_mM,
            dv_conc=r.mg_mM,
            dntp_conc=r.dntp_mM,
            primer_nM=r.primer_nM,
            probe_nM=r.probe_nM,
            temp_c=r.annealing_temp_C,
            tm_method=r.tm_method,
            salt_correction=r.salt_correction,
        )


@dataclass(frozen=True)
class StructureCalc:
    """Outcome of a hairpin/dimer calculation. Energies in kcal/mol; None when no structure."""

    found: bool
    tm_c: float | None
    dg_kcal: float | None
    dh_kcal: float | None
    ds_cal_per_k: float | None
    ascii_lines: tuple[str, ...]


def melting_temp(seq: str, cond: Conditions, *, nM: float) -> float:
    """Melting temperature (°C) of a concrete oligo at oligo concentration ``nM``."""
    return float(
        primer3.calc_tm(
            seq,
            mv_conc=cond.mv_conc,
            dv_conc=cond.dv_conc,
            dntp_conc=cond.dntp_conc,
            dna_conc=nM,
            tm_method=cond.tm_method,
            salt_corrections_method=cond.salt_correction,
        )
    )


def _wrap(result: object, ascii_lines: tuple[str, ...] = ()) -> StructureCalc:
    """Convert a primer3 ThermoResult; cal/mol -> kcal/mol happens here."""
    found = bool(result.structure_found)  # type: ignore[attr-defined]
    if not found:
        return StructureCalc(False, None, None, None, None, ())
    return StructureCalc(
        found=True,
        tm_c=float(result.tm),  # type: ignore[attr-defined]
        dg_kcal=float(result.dg) / 1000.0,  # type: ignore[attr-defined]
        dh_kcal=float(result.dh) / 1000.0,  # type: ignore[attr-defined]
        ds_cal_per_k=float(result.ds),  # type: ignore[attr-defined]
        ascii_lines=ascii_lines,
    )


def _ascii(result: object) -> tuple[str, ...]:
    if not getattr(result, "structure_found", False):
        return ()
    lines = getattr(result, "ascii_structure_lines", None) or []
    return tuple(str(line) for line in lines)


def _common(cond: Conditions, nM: float) -> dict[str, float]:
    return {
        "mv_conc": cond.mv_conc,
        "dv_conc": cond.dv_conc,
        "dntp_conc": cond.dntp_conc,
        "dna_conc": nM,
        "temp_c": cond.temp_c,
    }


def hairpin(seq: str, cond: Conditions, *, nM: float) -> StructureCalc:
    """Most stable hairpin of one oligo at the annealing temperature."""
    res = primer3.calc_hairpin(seq, output_structure=True, **_common(cond, nM))
    return _wrap(res, _ascii(res))


def homodimer(seq: str, cond: Conditions, *, nM: float) -> StructureCalc:
    """Most stable self-dimer of one oligo."""
    res = primer3.calc_homodimer(seq, output_structure=True, **_common(cond, nM))
    return _wrap(res, _ascii(res))


def heterodimer(a: str, b: str, cond: Conditions, *, nM: float) -> StructureCalc:
    """Most stable dimer between two different oligos."""
    res = primer3.calc_heterodimer(a, b, output_structure=True, **_common(cond, nM))
    return _wrap(res, _ascii(res))


def end_dimer(a: str, b: str, cond: Conditions, *, nM: float) -> StructureCalc:
    """Most stable dimer in which the 3' end of ``a`` is paired to ``b`` (extendable mispriming)."""
    res = primer3.calc_end_stability(a, b, **_common(cond, nM))
    return _wrap(res)


def nn_dg37(seq: str) -> float:
    """Sum of nearest-neighbour ΔG°37 (kcal/mol) over a perfectly paired duplex of ``seq``.

    Helix initiation and symmetry terms are omitted, so this is a relative measure of 3'-end
    stability (more negative = more stable), not an absolute duplex free energy.
    """
    return sum(_NN_DG37[seq[i : i + 2]] for i in range(len(seq) - 1))
