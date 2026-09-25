"""Locate oligos in a reference amplicon and check the amplicon geometry.

Coordinates are 1-based on the sense strand of the reference amplicon. A '+' site means the
oligo sequence is identical to the sense strand; a '-' site means its reverse complement is.
IUPAC codes (in the oligo or the amplicon) match whenever their base sets intersect.
"""

from __future__ import annotations

from ..config import AmpliconThresholds, Config
from ..models import Assay, Oligo, Status
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


def _label(o: Oligo) -> str:
    kind = {"forward": "Forward", "reverse": "Reverse", "probe": "Probe"}[o.role]
    return kind if o.name == o.role else f"{kind} {o.name}"


def _site_check(
    o: Oligo,
    site: SiteInfo | None,
    ref: str | None,
    max_mm: int,
    expect: str | None,
    alternative_found: bool,
    n_refs: int,
) -> CheckResult:
    """Where the oligo sits in the reference amplicon it fits best.

    An alternative that fits no reference is a WARN (it may be meant for a lineage without a
    reference here) as long as another oligo of its role fits; otherwise not found is a FAIL.
    """
    name = f"{_label(o)} site in reference amplicon"
    where = f" in {ref}" if ref and n_refs > 1 else ""
    rule = f"PASS exact match; WARN up to {max_mm} mismatch(es); FAIL if not found"
    if site is None:
        return CheckResult(
            id=f"{o.name}.site",
            subject=o.name,
            name=name,
            status=Status.WARN if alternative_found else Status.FAIL,
            display="not found",
            message=(
                f"The {o.name} oligo was not found in "
                + ("any reference amplicon" if n_refs > 1 else "the reference amplicon")
                + f" with at most {max_mm} mismatch(es)"
                + (f" on the expected ({expect}) strand." if expect else ".")
                + (" Another oligo of the same role fits; add the reference amplicon of the "
                   "lineage this one is meant for." if alternative_found else "")
            ),
            rule=rule,
        )  # fmt: skip
    status = Status.PASS if site.mismatches == 0 else Status.WARN
    return CheckResult(
        id=f"{o.name}.site",
        subject=o.name,
        name=name,
        status=status,
        display=f"{site.start}–{site.end} ({site.strand}){where}, {site.mismatches} mismatch(es)",
        value=float(site.mismatches),
        message=""
        if status is Status.PASS
        else f"The {o.name} oligo differs from the reference amplicon{where} at "
        f"{site.mismatches} position(s).",
        rule=rule,
    )


def _overlap(a: SiteInfo, b: SiteInfo) -> int:
    return max(0, min(a.end, b.end) - max(a.start, b.start) + 1)


_EXPECT = {"forward": "+", "reverse": "-", "probe": None}


def analyse(assay: Assay, cfg: Config) -> tuple[AmpliconSummary, list[CheckResult]]:
    """Amplicon geometry checks against the reference amplicon(s).

    Each oligo is placed in the reference it fits best. Product length and GC are checked for
    every reference in which a forward and a reverse primer fit; each probe is checked against
    the primers of the reference it fits. The summary describes the first such reference.
    """
    refs = assay.reference_amplicons
    if not refs:  # guarded by the caller
        raise ValueError("no reference_amplicon")
    t = cfg.thresholds.amplicon
    max_mm = t.max_site_mismatches
    checks: list[CheckResult] = []

    def sites_in(o: Oligo, seq: str) -> list[SiteInfo]:
        found = find_sites(seq, o.sequence, o.name, max_mismatches=max_mm)
        want = _EXPECT[o.role]
        return [x for x in found if x.strand == want] if want else found

    per_ref: dict[str, dict[str, SiteInfo]] = {}  # reference -> oligo name -> best site there
    for ref in refs:
        per_ref[ref.name] = {
            o.name: x[0] for o in assay.oligo_list if (x := sites_in(o, ref.sequence))
        }
    best: dict[str, tuple[str, SiteInfo]] = {}
    for o in assay.oligo_list:
        options = [(per_ref[r.name][o.name], i, r.name) for i, r in enumerate(refs)
                   if o.name in per_ref[r.name]]  # fmt: skip
        if options:
            site, _i, ref_name = min(options, key=lambda x: (x[0].mismatches, x[1]))
            best[o.name] = (ref_name, site)
    for o in assay.oligo_list:
        ref_name, site = best.get(o.name, (None, None))
        found_alt = any(x.name in best for x in assay.by_role(o.role) if x.name != o.name)
        checks.append(
            _site_check(o, site, ref_name, max_mm, _EXPECT[o.role] and
                        ("sense" if o.role == "forward" else "antisense"), found_alt, len(refs))
        )  # fmt: skip

    def pick(ref_name: str, role: str) -> SiteInfo | None:
        options = [per_ref[ref_name][o.name] for o in assay.by_role(role)
                   if o.name in per_ref[ref_name]]  # fmt: skip
        return min(options, key=lambda x: x.mismatches) if options else None

    summary: AmpliconSummary | None = None
    primers: dict[str, tuple[SiteInfo, SiteInfo]] = {}
    for ref in refs:
        fwd, rev = pick(ref.name, "forward"), pick(ref.name, "reverse")
        suffix = f" ({ref.name})" if len(refs) > 1 else ""
        sid = f".{ref.name}" if len(refs) > 1 else ""
        this = AmpliconSummary(input_length_nt=len(ref.sequence), forward_site=fwd,
                               reverse_site=rev, probe_site=pick(ref.name, "probe"))  # fmt: skip
        if (fwd is None or rev is None) and len(refs) > 1:
            missing = " and ".join(r for r, x in (("forward", fwd), ("reverse", rev)) if x is None)
            checks.append(
                CheckResult(
                    id=f"amplicon.primers{sid}",
                    subject="amplicon",
                    name=f"Primer pair in reference amplicon{suffix}",
                    status=Status.WARN,
                    display=f"no {missing} primer site",
                    message=(
                        f"No {missing} primer fits {ref.name} with at most {max_mm} mismatch(es) "
                        "(an ungapped search), so product length and the position of probes "
                        f"placed in {ref.name} are not checked. The primers may still bind with "
                        "a gap or bulge; the variant analysis aligns them in full."
                    ),
                    rule="WARN if a reference amplicon has no forward or no reverse primer site",
                )
            )
        if fwd is not None and rev is not None:
            if fwd.start >= rev.end or rev.start <= fwd.start:
                checks.append(
                    CheckResult(
                        id=f"amplicon.orientation{sid}",
                        subject="amplicon",
                        name=f"Primer orientation{suffix}",
                        status=Status.FAIL,
                        display=f"forward {fwd.start}–{fwd.end}, reverse {rev.start}–{rev.end}",
                        message="The primers do not face each other on the reference amplicon.",
                        rule="The forward primer must lie 5' of the reverse primer site",
                    )
                )
            else:
                primers[ref.name] = (fwd, rev)
                checks += _product_checks(this, ref.sequence, fwd, rev, t, suffix, sid)
        if summary is None or (summary.product_length_nt is None and this.product_length_nt):
            summary = this

    for o in assay.probe:
        if o.name not in best or best[o.name][0] not in primers:
            continue
        ref_name, probe = best[o.name]
        fwd, rev = primers[ref_name]
        checks += _probe_geometry(o, probe, fwd, rev, t, summary if summary and
                                  summary.probe_site == probe else None)  # fmt: skip
    assert summary is not None
    return summary, checks


def _product_checks(
    summary: AmpliconSummary,
    target: str,
    fwd: SiteInfo,
    rev: SiteInfo,
    t: AmpliconThresholds,
    suffix: str,
    sid: str,
) -> list[CheckResult]:
    checks: list[CheckResult] = []
    product = target[fwd.start - 1 : rev.end]
    summary.product_length_nt = len(product)
    summary.product_gc_percent = 100.0 * sum(c in "GC" for c in product) / len(product)
    summary.flank_5_nt = fwd.start - 1
    summary.flank_3_nt = len(target) - rev.end
    length_status = t.length_bp.grade(len(product))
    checks.append(
        CheckResult(
            id=f"amplicon.length{sid}",
            subject="amplicon",
            name=f"Amplicon length{suffix}",
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
            id=f"amplicon.gc{sid}",
            subject="amplicon",
            name=f"Amplicon GC content{suffix}",
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
                id=f"amplicon.flanks{sid}",
                subject="amplicon",
                name=f"Reference amplicon flanks{suffix}",
                status=Status.INFO,
                display=f"{summary.flank_5_nt} nt 5', {summary.flank_3_nt} nt 3'",
                message="reference_amplicon extends beyond the primer sites; length and GC use "
                "only the primer-defined product.",
            )
        )
    return checks


def _probe_geometry(
    o: Oligo,
    probe: SiteInfo,
    fwd: SiteInfo,
    rev: SiteInfo,
    t: AmpliconThresholds,
    summary: AmpliconSummary | None,
) -> list[CheckResult]:
    """Probe between the primers, overlap and position, in the reference it fits best."""
    pid, cap = o.name, _label(o)
    checks: list[CheckResult] = []
    inside = probe.start >= fwd.start and probe.end <= rev.end
    checks.append(
        CheckResult(
            id=f"{pid}.within_amplicon",
            subject=pid,
            name=f"{cap} inside primer-defined product",
            status=Status.PASS if inside else Status.FAIL,
            display=f"{probe.start}–{probe.end} ({probe.strand})",
            message="" if inside else "The probe site lies outside the region between the primers.",
            rule="The probe must bind between the primers",
        )
    )
    ov_f, ov_r = _overlap(probe, fwd), _overlap(probe, rev)
    overlap = ov_f + ov_r
    overlap_status = Status.PASS if overlap == 0 or t.allow_probe_primer_overlap else Status.WARN
    checks.append(
        CheckResult(
            id=f"{pid}.primer_overlap",
            subject=pid,
            name=f"{cap}/primer overlap",
            status=overlap_status,
            display=f"{ov_f} nt with forward, {ov_r} nt with reverse",
            value=float(overlap),
            message=""
            if overlap_status is Status.PASS
            else "The probe overlaps a primer binding site, which can interfere with "
            "primer extension and probe hybridisation.",
            rule="No overlap unless allow_probe_primer_overlap is set",
        )
    )
    gap_f, gap_r = max(0, probe.start - fwd.end - 1), max(0, rev.start - probe.end - 1)
    if summary is not None:
        summary.overlap_forward_nt, summary.overlap_reverse_nt = ov_f, ov_r
        if inside:
            summary.gap_forward_probe_nt, summary.gap_probe_reverse_nt = gap_f, gap_r
    if inside:
        checks.append(
            CheckResult(
                id=f"{pid}.position",
                subject=pid,
                name=f"{cap} position",
                status=Status.INFO,
                display=f"{gap_f} nt from forward primer, {gap_r} nt from reverse primer; "
                f"sequence matches the {'sense' if probe.strand == '+' else 'antisense'} strand",
            )
        )
    return checks
