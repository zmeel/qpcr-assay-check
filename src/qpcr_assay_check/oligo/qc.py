"""Oligo quality control: PASS/WARN/FAIL against configurable thresholds.

Degenerate oligos are expanded into all concrete variants. Every check is evaluated for every
variant and the **worst** result decides the status, so a single poor variant is never hidden.
"""

from __future__ import annotations

import itertools
import logging
from collections.abc import Callable, Sequence

from ..config import Config
from ..models import Assay, Status, worst
from ..results import CheckResult, OligoInfo, QCReport, StructureResult
from . import amplicon as amplicon_mod
from . import iupac, thermo

log = logging.getLogger(__name__)

#: Modification names that make nearest-neighbour Tm and dimer estimates unreliable.
TM_UNRELIABLE_TOKENS = ("MGB", "LNA", "ZEN", "PNA", "BNA")

Grader = Callable[[float], Status]


def _fmt_range(values: Sequence[float], fmt: str = "{:.1f}") -> str:
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 1e-9:
        return fmt.format(lo)
    return f"{fmt.format(lo)}–{fmt.format(hi)}"


def _numeric_check(
    *,
    id: str,
    subject: str,
    name: str,
    values: Sequence[float],
    grade: Grader,
    unit: str = "",
    rule: str = "",
    fmt: str = "{:.1f}",
    hint: Callable[[float], str] | None = None,
) -> CheckResult:
    """Grade every value (one per degenerate variant); the worst status wins."""
    graded = [(grade(v), v) for v in values]
    status = worst(s for s, _ in graded)
    display = _fmt_range(values, fmt)
    message = ""
    if status in (Status.WARN, Status.FAIL):
        offender = next(v for s, v in graded if s is status)
        message = hint(offender) if hint else f"{name}: {display}{(' ' + unit) if unit else ''}."
    same = abs(max(values) - min(values)) < 1e-9
    return CheckResult(
        id=id,
        subject=subject,
        name=name,
        status=status,
        display=display,
        value=values[0] if same else None,
        value_min=min(values),
        value_max=max(values),
        unit=unit,
        message=message,
        rule=rule,
    )


def _info(grade_value: float) -> Status:  # noqa: ARG001 - matches the Grader signature
    return Status.INFO


def _cap_at_warn(grader: Grader) -> Grader:
    def capped(v: float) -> Status:
        s = grader(v)
        return Status.WARN if s is Status.FAIL else s

    return capped


def _primer_checks(
    role: str, variants: list[str], tms: list[float], cfg: Config
) -> list[CheckResult]:
    t = cfg.thresholds.primer
    cap = role.capitalize()
    out = [
        _numeric_check(
            id=f"{role}.length",
            subject=role,
            name=f"{cap} primer length",
            values=[float(len(v)) for v in variants],
            grade=t.length_nt.grade,
            unit="nt",
            rule=t.length_nt.describe("nt"),
            fmt="{:.0f}",
            hint=lambda v: f"{v:.0f} nt is outside the preferred primer length.",
        ),
        _numeric_check(
            id=f"{role}.gc",
            subject=role,
            name=f"{cap} primer GC content",
            values=[iupac.gc_percent(v) for v in variants],
            grade=t.gc_percent.grade,
            unit="%",
            rule=t.gc_percent.describe("%"),
            hint=lambda v: f"GC content of {v:.1f}% is outside the preferred range.",
        ),
        _numeric_check(
            id=f"{role}.tm",
            subject=role,
            name=f"{cap} primer Tm",
            values=tms,
            grade=t.tm_c.grade,
            unit="°C",
            rule=t.tm_c.describe("°C"),
            hint=lambda v: f"Tm of {v:.1f} °C is outside the preferred range.",
        ),
        _numeric_check(
            id=f"{role}.gc_last5",
            subject=role,
            name=f"{cap} primer G/C in last 5 nt (3' end)",
            values=[float(sum(c in "GC" for c in v[-5:])) for v in variants],
            grade=t.gc_in_last5.grade,
            unit="G/C",
            rule=t.gc_in_last5.describe("G/C"),
            fmt="{:.0f}",
            hint=lambda v: (
                "No G/C in the last 5 nt: no GC clamp at the 3' end."
                if v < t.gc_in_last5.min
                else f"{v:.0f} G/C in the last 5 nt: the 3' end may be too stable "
                "(mispriming risk)."
            ),
        ),
        _numeric_check(
            id=f"{role}.three_prime_dg",
            subject=role,
            name=f"{cap} primer 3' end stability (last 5 nt, nearest-neighbour ΔG°37)",
            values=[thermo.nn_dg37(v[-5:]) for v in variants],
            grade=_info,
            unit="kcal/mol",
            rule="Informational (more negative = more stable 3' end)",
            fmt="{:.2f}",
        ),
        _numeric_check(
            id=f"{role}.max_run",
            subject=role,
            name=f"{cap} primer longest single-base run",
            values=[float(iupac.longest_run(v)) for v in variants],
            grade=t.max_run.grade,
            unit="nt",
            rule=t.max_run.describe("nt"),
            fmt="{:.0f}",
            hint=lambda v: f"A run of {v:.0f} identical bases can cause slippage/mispriming.",
        ),
        _numeric_check(
            id=f"{role}.max_g_run",
            subject=role,
            name=f"{cap} primer longest G run",
            values=[float(iupac.longest_run(v, "G")) for v in variants],
            grade=t.max_g_run.grade,
            unit="nt",
            rule=t.max_g_run.describe("nt"),
            fmt="{:.0f}",
            hint=lambda v: f"A run of {v:.0f} G can form stable secondary structures.",
        ),
    ]
    return out


def _probe_checks(
    assay: Assay,
    variants: list[str],
    probe_tms: list[float],
    fwd_tms: list[float],
    rev_tms: list[float],
    unreliable: list[str],
    cfg: Config,
) -> list[CheckResult]:
    t = cfg.thresholds.probe
    out = [
        _numeric_check(
            id="probe.length",
            subject="probe",
            name="Probe length",
            values=[float(len(v)) for v in variants],
            grade=t.length_nt.grade,
            unit="nt",
            rule=t.length_nt.describe("nt"),
            fmt="{:.0f}",
            hint=lambda v: f"{v:.0f} nt is outside the preferred probe length.",
        ),
        _numeric_check(
            id="probe.gc",
            subject="probe",
            name="Probe GC content",
            values=[iupac.gc_percent(v) for v in variants],
            grade=t.gc_percent.grade,
            unit="%",
            rule=t.gc_percent.describe("%"),
            hint=lambda v: f"GC content of {v:.1f}% is outside the preferred range.",
        ),
        _numeric_check(
            id="probe.tm",
            subject="probe",
            name="Probe Tm",
            values=probe_tms,
            grade=_info,
            unit="°C",
            rule="Informational; see probe Tm relative to the primers",
        ),
    ]

    diff_grader: Grader = t.tm_minus_mean_primer_c.grade
    if unreliable:
        diff_grader = _cap_at_warn(diff_grader)
    lo = min(probe_tms) - (max(fwd_tms) + max(rev_tms)) / 2
    hi = max(probe_tms) - (min(fwd_tms) + min(rev_tms)) / 2
    out.append(
        _numeric_check(
            id="probe.tm_minus_primers",
            subject="probe",
            name="Probe Tm minus mean primer Tm",
            values=[lo, hi],
            grade=diff_grader,
            unit="°C",
            rule=t.tm_minus_mean_primer_c.describe("°C")
            + ("; capped at WARN because the probe is modified" if unreliable else ""),
            hint=lambda v: (
                f"Probe Tm is {v:.1f} °C above the mean primer Tm, outside the preferred range."
            ),
        )
    )
    out += [
        _numeric_check(
            id="probe.max_run",
            subject="probe",
            name="Probe longest single-base run",
            values=[float(iupac.longest_run(v)) for v in variants],
            grade=t.max_run.grade,
            unit="nt",
            rule=t.max_run.describe("nt"),
            fmt="{:.0f}",
            hint=lambda v: f"A run of {v:.0f} identical bases in the probe.",
        ),
        _numeric_check(
            id="probe.max_g_run",
            subject="probe",
            name="Probe longest G run",
            values=[float(iupac.longest_run(v, "G")) for v in variants],
            grade=t.max_g_run.grade,
            unit="nt",
            rule=t.max_g_run.describe("nt"),
            fmt="{:.0f}",
            hint=lambda v: f"A run of {v:.0f} G in the probe.",
        ),
    ]

    if t.warn_if_more_g_than_c:
        excess = [float(v.count("G") - v.count("C")) for v in variants]
        out.append(
            _numeric_check(
                id="probe.g_minus_c",
                subject="probe",
                name="Probe G count minus C count",
                values=excess,
                grade=lambda v: Status.WARN if v > 0 else Status.PASS,
                unit="nt",
                rule="WARN if the probe has more G than C",
                fmt="{:.0f}",
                hint=lambda v: (
                    f"The probe has {v:.0f} more G than C, which can quench the reporter."
                ),
            )
        )

    out.append(_five_prime_g_check(assay, variants, cfg))

    if unreliable:
        out.append(
            CheckResult(
                id="probe.tm_reliability",
                subject="probe",
                name="Probe Tm reliability",
                status=Status.WARN,
                display=", ".join(unreliable),
                message=(
                    f"The probe carries {', '.join(unreliable)}. Nearest-neighbour Tm and dimer "
                    "estimates do not model these modifications; use vendor-specific Tm values."
                ),
                rule="Any declared modification (MGB, LNA, ZEN, ...) triggers this warning",
            )
        )
    return out


def _five_prime_g_check(assay: Assay, variants: list[str], cfg: Config) -> CheckResult:
    """A 5' G next to the reporter quenches fluorescence for FAM-type dyes."""
    reporter = (assay.probe_reporter or "").strip()
    sensitive = any(
        tok.upper() in reporter.upper() for tok in cfg.thresholds.probe.g_sensitive_reporters
    )
    has_g = any(v[0] == "G" for v in variants)
    base = {
        "id": "probe.five_prime_g",
        "subject": "probe",
        "name": "Probe 5' base",
        "display": "/".join(sorted({v[0] for v in variants})),
        "rule": "WARN if the 5' base is G and the reporter is FAM-type (or unspecified)",
    }
    if not has_g:
        return CheckResult(status=Status.PASS, **base)
    if sensitive:
        return CheckResult(
            status=Status.WARN,
            message=f"A 5' G next to the {reporter} reporter quenches the fluorescence.",
            **base,
        )
    if not reporter:
        return CheckResult(
            status=Status.WARN,
            message="The 5' base is G and no reporter is specified. A 5' G next to FAM quenches "
            "the signal.",
            **base,
        )
    return CheckResult(
        status=Status.INFO,
        message=f"The 5' base is G; the FAM-specific rule is not applied to reporter {reporter}.",
        **base,
    )


def _pair_checks(fwd_tms: list[float], rev_tms: list[float], cfg: Config) -> list[CheckResult]:
    t = cfg.thresholds.pair.primer_tm_diff_c
    worst_diff = max(max(fwd_tms) - min(rev_tms), max(rev_tms) - min(fwd_tms), 0.0)
    return [
        _numeric_check(
            id="pair.primer_tm_diff",
            subject="pair",
            name="Primer Tm difference (forward vs reverse)",
            values=[worst_diff],
            grade=t.grade,
            unit="°C",
            rule=t.describe("°C"),
            hint=lambda v: f"The primers differ by {v:.1f} °C in Tm; they anneal unevenly.",
        )
    ]


def _grade_structure(calc: thermo.StructureCalc, warn: float, fail: float) -> Status:
    if not calc.found or calc.tm_c is None:
        return Status.PASS
    if calc.tm_c >= fail:
        return Status.FAIL
    if calc.tm_c >= warn:
        return Status.WARN
    return Status.PASS


def _tm_key(calc: thermo.StructureCalc) -> float:
    return calc.tm_c if calc.found and calc.tm_c is not None else float("-inf")


def _structure_result(
    kind: str,
    label: str,
    subjects: list[str],
    calcs: list[tuple[str, thermo.StructureCalc]],
    n_total: int,
    cfg: Config,
) -> StructureResult:
    """Keep the worst (highest-Tm) structure across degenerate variants."""
    variant, pick = max(calcs, key=lambda vc: _tm_key(vc[1]))
    status = _grade_structure(pick, cfg.thresholds.structures.warn_tm_c, cfg.structure_fail_tm_c)
    return StructureResult(
        kind=kind,  # type: ignore[arg-type]
        label=label,
        subjects=subjects,
        found=pick.found,
        tm_c=pick.tm_c,
        dg_kcal=pick.dg_kcal,
        temp_c=cfg.reaction.annealing_temp_C,
        status=status,
        variant=variant if variant and len(calcs) > 1 else None,
        n_evaluated=len(calcs),
        n_total=n_total,
        ascii_lines=list(pick.ascii_lines) if status in (Status.WARN, Status.FAIL) else [],
    )


def _structures(
    variants: dict[str, list[str]], cfg: Config, cond: thermo.Conditions
) -> list[StructureResult]:
    out: list[StructureResult] = []
    primer_nM, probe_nM = cfg.reaction.primer_nM, cfg.reaction.probe_nM
    cap = cfg.oligo.max_pair_combinations

    def nm_for(*roles: str) -> float:
        return probe_nM if "probe" in roles else primer_nM

    for role, vs in variants.items():
        nM = nm_for(role)
        out.append(
            _structure_result(
                "hairpin",
                f"{role} hairpin",
                [role],
                [(v, thermo.hairpin(v, cond, nM=nM)) for v in vs],
                len(vs),
                cfg,
            )
        )
        out.append(
            _structure_result(
                "homodimer",
                f"{role} self-dimer",
                [role],
                [(v, thermo.homodimer(v, cond, nM=nM)) for v in vs],
                len(vs),
                cfg,
            )
        )

    def combos(a: str, b: str) -> tuple[list[tuple[str, str]], int]:
        total = len(variants[a]) * len(variants[b])
        pairs = list(itertools.islice(itertools.product(variants[a], variants[b]), cap))
        return pairs, total

    for a, b in (("forward", "reverse"), ("forward", "probe"), ("reverse", "probe")):
        pairs, total = combos(a, b)
        nM = nm_for(a, b)
        out.append(
            _structure_result(
                "heterodimer",
                f"{a} / {b} dimer",
                [a, b],
                [(f"{x} + {y}", thermo.heterodimer(x, y, cond, nM=nM)) for x, y in pairs],
                total,
                cfg,
            )
        )

    for a, b in (
        ("forward", "forward"),
        ("forward", "reverse"),
        ("forward", "probe"),
        ("reverse", "reverse"),
        ("reverse", "forward"),
        ("reverse", "probe"),
    ):
        pairs, total = combos(a, b)
        nM = nm_for(a, b)
        out.append(
            _structure_result(
                "end_dimer",
                f"3' end of {a} on {b}",
                [a, b],
                [(f"{x} + {y}", thermo.end_dimer(x, y, cond, nM=nM)) for x, y in pairs],
                total,
                cfg,
            )
        )
    return out


def _oligo_info(role: str, seq: str, variants: list[str], tms: list[float]) -> OligoInfo:
    gcs = [iupac.gc_percent(v) for v in variants]
    return OligoInfo(
        role=role,
        sequence=seq,
        length_nt=len(seq),
        degenerate=iupac.is_degenerate(seq),
        n_variants=len(variants),
        variants=variants,
        gc_percent_min=min(gcs),
        gc_percent_max=max(gcs),
        tm_c_min=min(tms),
        tm_c_max=max(tms),
    )


def run_oligo_qc(assay: Assay, cfg: Config) -> QCReport:
    """Run all oligo QC checks for one assay."""
    cond = thermo.Conditions.from_reaction(cfg.reaction)
    variants = {
        role: iupac.expand(seq, cfg.oligo.max_degenerate_expansions)
        for role, seq in assay.oligos.items()
    }
    nM = {
        "forward": cfg.reaction.primer_nM,
        "reverse": cfg.reaction.primer_nM,
        "probe": cfg.reaction.probe_nM,
    }
    tms = {
        role: [thermo.melting_temp(v, cond, nM=nM[role]) for v in vs]
        for role, vs in variants.items()
    }
    unreliable = assay.declared_modifications(TM_UNRELIABLE_TOKENS)
    log.info(
        "Oligo QC for %r: %s",
        assay.assay_name,
        {r: len(v) for r, v in variants.items()},
    )

    checks: list[CheckResult] = []
    for role in ("forward", "reverse"):
        checks += _primer_checks(role, variants[role], tms[role], cfg)
    checks += _probe_checks(
        assay, variants["probe"], tms["probe"], tms["forward"], tms["reverse"], unreliable, cfg
    )
    checks += _pair_checks(tms["forward"], tms["reverse"], cfg)

    structures = _structures(variants, cfg, cond)

    summary = None
    amplicon_note = ""
    if assay.reference_amplicon:
        summary, amp_checks = amplicon_mod.analyse(assay, cfg)
        checks += amp_checks
    else:
        amplicon_note = (
            "No reference_amplicon was provided, so amplicon length, GC content and probe/primer "
            "overlap were not evaluated. From v0.4.0 the reference amplicon is derived "
            "automatically from the reference accession."
        )

    status = worst([c.status for c in checks] + [s.status for s in structures])
    return QCReport(
        oligos=[_oligo_info(r, assay.oligos[r], variants[r], tms[r]) for r in assay.oligos],
        checks=checks,
        structures=structures,
        amplicon=summary,
        amplicon_note=amplicon_note,
        tm_unreliable_reasons=unreliable,
        status=status,
    )
