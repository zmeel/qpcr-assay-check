"""Locate oligos in a reference amplicon and check the amplicon geometry.

Coordinates are 1-based on the sense strand of the reference amplicon. A '+' site means the
oligo sequence is identical to the sense strand; a '-' site means its reverse complement is.
IUPAC codes (in the oligo or the amplicon) match whenever their base sets intersect.
"""

from __future__ import annotations

from ..config import Config
from ..models import Assay, Status
from ..results import AmpliconSummary, CheckResult, SiteInfo
from . import iupac


def find_sites(target: str, oligo: str, role: str, *, max_mismatches: int) -> list[SiteInfo]:
    """All sites on both strands with at most ``max_mismatches``, best first."""
    length = len(oligo)
    rc = iupac.reverse_complement(oligo)
    hits: list[SiteInfo] = []
    for i in range(len(target) - length + 1):
        window = target[i : i + length]
        for strand, probe in (("+", oligo), ("-", rc)):
            mm = iupac.count_mismatches(probe, window)
            if mm <= max_mismatches:
                hits.append(
                    SiteInfo(
                        oligo=role,
                        strand=strand,  # type: ignore[arg-type]
                        start=i + 1,
                        end=i + length,
                        mismatches=mm,
                    )
                )
    hits.sort(key=lambda h: (h.mismatches, h.strand != "+", h.start))
    return hits


def _site_check(role: str, site: SiteInfo | None, max_mm: int, expect: str | None) -> CheckResult:
    name = f"{role.capitalize()} site in reference amplicon"
    rule = f"PASS exact match; WARN up to {max_mm} mismatch(es); FAIL if not found"
    if site is None:
        return CheckResult(
            id=f"{role}.site",
            subject=role,
            name=name,
            status=Status.FAIL,
            display="not found",
            message=(
                f"The {role} oligo was not found in the reference amplicon with at most "
                f"{max_mm} mismatch(es)"
                + (f" on the expected ({expect}) strand." if expect else ".")
            ),
            rule=rule,
        )
    status = Status.PASS if site.mismatches == 0 else Status.WARN
    return CheckResult(
        id=f"{role}.site",
        subject=role,
        name=name,
        status=status,
        display=f"{site.start}–{site.end} ({site.strand}), {site.mismatches} mismatch(es)",
        value=float(site.mismatches),
        message=""
        if status is Status.PASS
        else f"The {role} oligo differs from the reference amplicon at "
        f"{site.mismatches} position(s).",
        rule=rule,
    )


def _overlap(a: SiteInfo, b: SiteInfo) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start) + 1)


def analyse(assay: Assay, cfg: Config) -> tuple[AmpliconSummary, list[CheckResult]]:
    """Amplicon geometry checks against the optional ``reference_amplicon``."""
    target = assay.reference_amplicon
    if target is None:  # guarded by the caller
        raise ValueError("no reference_amplicon")
    t = cfg.thresholds.amplicon
    max_mm = t.max_site_mismatches
    checks: list[CheckResult] = []
    summary = AmpliconSummary(input_length_nt=len(target))

    def best(role: str, want: str | None) -> SiteInfo | None:
        sites = find_sites(target, assay.oligos[role], role, max_mismatches=max_mm)
        if want:
            sites = [s for s in sites if s.strand == want]
        return sites[0] if sites else None

    fwd, rev, probe = best("forward", "+"), best("reverse", "-"), best("probe", None)
    summary.forward_site, summary.reverse_site, summary.probe_site = fwd, rev, probe
    checks.append(_site_check("forward", fwd, max_mm, "sense"))
    checks.append(_site_check("reverse", rev, max_mm, "antisense"))
    checks.append(_site_check("probe", probe, max_mm, None))

    if fwd is None or rev is None:
        return summary, checks

    if fwd.start >= rev.end or rev.start <= fwd.start:
        checks.append(
            CheckResult(
                id="amplicon.orientation",
                subject="amplicon",
                name="Primer orientation",
                status=Status.FAIL,
                display=f"forward {fwd.start}–{fwd.end}, reverse {rev.start}–{rev.end}",
                message="The primers do not face each other on the reference amplicon.",
                rule="The forward primer must lie 5' of the reverse primer site",
            )
        )
        return summary, checks

    product = target[fwd.start - 1 : rev.end]
    summary.product_length_nt = len(product)
    summary.product_gc_percent = 100.0 * sum(c in "GC" for c in product) / len(product)
    summary.flank_5_nt = fwd.start - 1
    summary.flank_3_nt = len(target) - rev.end

    length_status = t.length_bp.grade(len(product))
    checks.append(
        CheckResult(
            id="amplicon.length",
            subject="amplicon",
            name="Amplicon length",
            status=length_status,
            display=str(len(product)),
            value=float(len(product)),
            unit="bp",
            message=""
            if length_status is Status.PASS
            else f"Amplicon of {len(product)} bp is outside the preferred range.",
            rule=t.length_bp.describe("bp"),
        )
    )
    gc_status = t.gc_percent.grade(summary.product_gc_percent)
    checks.append(
        CheckResult(
            id="amplicon.gc",
            subject="amplicon",
            name="Amplicon GC content",
            status=gc_status,
            display=f"{summary.product_gc_percent:.1f}",
            value=summary.product_gc_percent,
            unit="%",
            message=""
            if gc_status is Status.PASS
            else f"Amplicon GC of {summary.product_gc_percent:.1f}% is outside the preferred "
            "range.",
            rule=t.gc_percent.describe("%"),
        )
    )
    if summary.flank_5_nt or summary.flank_3_nt:
        checks.append(
            CheckResult(
                id="amplicon.flanks",
                subject="amplicon",
                name="Reference amplicon flanks",
                status=Status.INFO,
                display=f"{summary.flank_5_nt} nt 5', {summary.flank_3_nt} nt 3'",
                message="reference_amplicon extends beyond the primer sites; length and GC use "
                "only the primer-defined product.",
            )
        )

    if probe is not None:
        inside = probe.start >= fwd.start and probe.end <= rev.end
        checks.append(
            CheckResult(
                id="probe.within_amplicon",
                subject="probe",
                name="Probe inside primer-defined product",
                status=Status.PASS if inside else Status.FAIL,
                display=f"{probe.start}–{probe.end} ({probe.strand})",
                message=""
                if inside
                else "The probe site lies outside the region between the primers.",
                rule="The probe must bind between the primers",
            )
        )
        summary.overlap_forward_nt = _overlap(probe, fwd)
        summary.overlap_reverse_nt = _overlap(probe, rev)
        overlap = summary.overlap_forward_nt + summary.overlap_reverse_nt
        overlap_status = (
            Status.PASS if overlap == 0 or t.allow_probe_primer_overlap else Status.WARN
        )
        checks.append(
            CheckResult(
                id="probe.primer_overlap",
                subject="probe",
                name="Probe/primer overlap",
                status=overlap_status,
                display=f"{summary.overlap_forward_nt} nt with forward, "
                f"{summary.overlap_reverse_nt} nt with reverse",
                value=float(overlap),
                message=""
                if overlap_status is Status.PASS
                else "The probe overlaps a primer binding site, which can interfere with "
                "primer extension and probe hybridisation.",
                rule="No overlap unless allow_probe_primer_overlap is set",
            )
        )
        if inside:
            summary.gap_forward_probe_nt = max(0, probe.start - fwd.end - 1)
            summary.gap_probe_reverse_nt = max(0, rev.start - probe.end - 1)
            checks.append(
                CheckResult(
                    id="probe.position",
                    subject="probe",
                    name="Probe position",
                    status=Status.INFO,
                    display=f"{summary.gap_forward_probe_nt} nt from forward primer, "
                    f"{summary.gap_probe_reverse_nt} nt from reverse primer; sequence matches the "
                    f"{'sense' if probe.strand == '+' else 'antisense'} strand",
                )
            )
    return summary, checks
