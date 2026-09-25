"""Diff this run's already-computed evidence against the previous run for the same assay.

Sites and amplicons are matched across runs by a natural key (accession, orientation, position),
not by their run-local ``id``, which is only stable within one run (see ``history/models.py``).

This is called from ``pipeline.evaluate()`` *before* the overall verdict is combined, because
"history" is itself one of the combined sections. It therefore compares the other sections'
already-known verdicts to the previous run's, rather than a circular "overall verdict before vs
after" (which would need this section's own verdict to exist first).
"""

from __future__ import annotations

from ..inclusivity.aggregate import detectable_percent
from ..inclusivity.models import InclusivityResult, WindowStats
from ..results import RunResult
from ..specificity.models import AmpliconResult, SiteResult
from ..specificity.variants import VariantRow, VariantSummary
from ..verdict import Verdict
from .models import (
    AmpliconChange,
    HistoryResult,
    InclusivityYearChange,
    SectionChange,
    SiteChange,
    VariantChange,
)

_RANK: dict[Verdict, int] = {
    Verdict.PASS: 0,
    Verdict.WARN: 1,
    Verdict.INCOMPLETE: 2,
    Verdict.FAIL: 3,
}


def _site_key(s: SiteResult) -> tuple:
    return (s.tier, s.role, s.accession, s.orientation, s.subject_start, s.subject_end)


def _amplicon_key(a: AmpliconResult) -> tuple:
    return (a.tier, a.accession, a.start, a.end, a.roles)


def _new_site(s: SiteResult) -> SiteChange:
    return SiteChange(
        kind="new", tier=s.tier, role=s.role, accession=s.accession, orientation=s.orientation,
        subject_start=s.subject_start, subject_end=s.subject_end, organism=s.organism,
        level_after=s.level, n_mismatch_after=s.n_mismatch,
    )  # fmt: skip


def _resolved_site(s: SiteResult) -> SiteChange:
    return SiteChange(
        kind="resolved", tier=s.tier, role=s.role, accession=s.accession, orientation=s.orientation,
        subject_start=s.subject_start, subject_end=s.subject_end, organism=s.organism,
        level_before=s.level, n_mismatch_before=s.n_mismatch,
    )  # fmt: skip


def _changed_site(curr: SiteResult, prev: SiteResult) -> SiteChange:
    return SiteChange(
        kind="changed", tier=curr.tier, role=curr.role, accession=curr.accession,
        orientation=curr.orientation, subject_start=curr.subject_start,
        subject_end=curr.subject_end, organism=curr.organism,
        level_before=prev.level, level_after=curr.level,
        n_mismatch_before=prev.n_mismatch, n_mismatch_after=curr.n_mismatch,
    )  # fmt: skip


def _new_amplicon(a: AmpliconResult) -> AmpliconChange:
    return AmpliconChange(
        kind="new", tier=a.tier, accession=a.accession, start=a.start, end=a.end,
        roles=a.roles, organism=a.organism, classification=a.classification,
    )  # fmt: skip


def _resolved_amplicon(a: AmpliconResult) -> AmpliconChange:
    return AmpliconChange(
        kind="resolved", tier=a.tier, accession=a.accession, start=a.start, end=a.end,
        roles=a.roles, organism=a.organism, classification=a.classification,
    )  # fmt: skip


def _pct(w: WindowStats) -> float | None:
    return detectable_percent(w)


def _inclusivity_changes(
    previous: InclusivityResult | None, current: InclusivityResult | None
) -> list[InclusivityYearChange]:
    """Per (role, year) window present in both runs, only where something actually differs."""
    prev_windows = {
        (o.role, w.year): w for o in (previous.oligos if previous else []) for w in o.windows
    }
    curr_windows = {
        (o.role, w.year): w for o in (current.oligos if current else []) for w in o.windows
    }
    out: list[InclusivityYearChange] = []
    for role, year in sorted(prev_windows.keys() & curr_windows.keys()):
        pw, cw = prev_windows[(role, year)], curr_windows[(role, year)]
        if pw.sample_size == 0 and cw.sample_size == 0:
            continue
        pct_before, pct_after = _pct(pw), _pct(cw)
        if pct_before == pct_after and pw.sample_size == cw.sample_size:
            continue
        new_positions = (
            [
                i + 1
                for i, (before, after) in enumerate(
                    zip(pw.per_position_mismatches, cw.per_position_mismatches, strict=False)
                )
                if before == 0 and after > 0
            ]
            if pw.sample_size > 0 and cw.sample_size > 0
            else []
        )
        out.append(
            InclusivityYearChange(
                role=role, year=year, percent_before=pct_before, percent_after=pct_after,
                sample_size_before=pw.sample_size, sample_size_after=cw.sample_size,
                new_mismatch_positions=new_positions,
            )
        )  # fmt: skip
    return out


def _concern(role: str, row: VariantRow) -> bool:
    defects = row.n_mismatch + row.n_gap
    if role == "probe":
        return defects >= 2
    return defects >= 2 or (defects >= 1 and row.clean_3prime_nt < 5)


def _variant_changes(
    previous: VariantSummary | None, current: VariantSummary | None, previous_date: str
) -> tuple[list[VariantChange], bool, str]:
    """Per oligo: variants seen now but not in the previous run, and the reverse."""
    if previous is None and current is None:
        return [], False, ""
    if previous is None or current is None:
        return [], False, "Variants not compared: only one of the two runs has a variant summary."
    if previous.source != current.source:
        return (
            [],
            False,
            (
                f"Variants not compared: the previous run used '{previous.source}', this run "
                f"'{current.source}' as the source, so differences would reflect the method."
            ),
        )
    cutoff = previous_date[:10]
    out: list[VariantChange] = []
    for role in ("forward", "probe", "reverse"):
        prev = {r.s_aln: r for o in previous.oligos if o.role == role for r in o.rows}
        curr = {r.s_aln: r for o in current.oligos if o.role == role for r in o.rows}
        for key, row in curr.items():
            if key not in prev:
                out.append(VariantChange(
                    kind="new", role=role, q_aln=row.q_aln, s_aln=row.s_aln,  # type: ignore[arg-type]
                    midline=row.midline, count_after=row.count, percent_after=row.percent,
                    n_mismatch=row.n_mismatch, n_gap=row.n_gap,
                    clean_3prime_nt=row.clean_3prime_nt, first_seen=row.first_seen,
                    example_accession=row.example_accession,
                    newly_released=(row.first_seen > cutoff) if row.first_seen else None,
                    concern=_concern(role, row),
                ))  # fmt: skip
        for key, row in prev.items():
            if key not in curr:
                out.append(VariantChange(
                    kind="gone", role=role, q_aln=row.q_aln, s_aln=row.s_aln,  # type: ignore[arg-type]
                    midline=row.midline, count_before=row.count, n_mismatch=row.n_mismatch,
                    n_gap=row.n_gap, clean_3prime_nt=row.clean_3prime_nt,
                    first_seen=row.first_seen, example_accession=row.example_accession,
                ))  # fmt: skip
    return out, True, ""


def _rationale(
    h: HistoryResult, section_changes: list[SectionChange], previous_generated_at: str
) -> list[str]:
    lines: list[str] = []
    if h.inputs_changed:
        lines.append(
            f"The assay definition or configuration changed since the previous run "
            f"({previous_generated_at})."
        )
    for sc in section_changes:
        if sc.changed:
            before = sc.verdict_before.value if sc.verdict_before else "not evaluated"
            after = sc.verdict_after.value if sc.verdict_after else "not evaluated"
            lines.append(f"{sc.title}: {before} -> {after}.")
    if h.new_sites:
        lines.append(f"{len(h.new_sites)} new off-target site(s) since the previous run.")
    if h.resolved_sites:
        lines.append(f"{len(h.resolved_sites)} off-target site(s) no longer found.")
    if h.changed_sites:
        lines.append(
            f"{len(h.changed_sites)} previously-seen off-target site(s) changed level or "
            "mismatch count."
        )
    if h.new_amplicons:
        lines.append(f"{len(h.new_amplicons)} new predicted off-target product(s).")
    if h.resolved_amplicons:
        lines.append(
            f"{len(h.resolved_amplicons)} predicted off-target product(s) no longer found."
        )
    new_variants = [v for v in h.variant_changes if v.kind == "new"]
    if new_variants:
        emerging = sum(1 for v in new_variants if v.newly_released)
        concern = sum(1 for v in new_variants if v.concern)
        lines.append(
            f"{len(new_variants)} oligo sequence variant(s) not seen in the previous run"
            + (f", {emerging} in assemblies released since then (emerging)" if emerging else "")
            + (f"; {concern} with a primer 3'-end mismatch or 2+ mismatches" if concern else "")
            + "."
        )
    gone = [v for v in h.variant_changes if v.kind == "gone"]
    if gone:
        lines.append(f"{len(gone)} oligo sequence variant(s) of the previous run no longer seen.")
    if h.variants_note:
        lines.append(h.variants_note)
    for c in h.inclusivity_changes:
        if (
            c.percent_before is not None
            and c.percent_after is not None
            and round(c.percent_before) != round(c.percent_after)
        ):  # a shift below 1 point (e.g. only more records assessed) stays in the table
            lines.append(
                f"Inclusivity, {c.role} {c.year}: {c.percent_before:.0f}% -> "
                f"{c.percent_after:.0f}% detectable."
            )
    if not lines:
        lines.append(f"No meaningful change since the previous run ({previous_generated_at}).")
    return lines


def compute_history(
    previous: RunResult | None,
    *,
    inputs_hash: str,
    section_verdicts: dict[str, Verdict | None],
    section_titles: dict[str, str],
    sites: list[SiteResult],
    amplicons: list[AmpliconResult],
    inclusivity: InclusivityResult | None,
    variant_summary: VariantSummary | None = None,
) -> HistoryResult:
    """Diff this run's already-computed sections/evidence against the previous run, if any."""
    if previous is None:
        return HistoryResult(
            has_previous=False,
            verdict=Verdict.INCOMPLETE,
            rationale=["First run for this assay: no previous run was found to compare against."],
        )

    prev_section_verdicts = {s.key: s.verdict for s in previous.sections}
    section_changes = [
        SectionChange(
            key=key,
            title=section_titles.get(key, key),
            verdict_before=prev_section_verdicts.get(key),
            verdict_after=verdict_after,
            changed=prev_section_verdicts.get(key) != verdict_after,
        )
        for key, verdict_after in section_verdicts.items()
    ]
    section_regressed = any(
        sc.verdict_before is not None
        and sc.verdict_after is not None
        and _RANK[sc.verdict_after] > _RANK[sc.verdict_before]
        for sc in section_changes
    )

    prev_sites = {
        _site_key(s): s for s in (previous.specificity.sites if previous.specificity else [])
    }
    curr_sites = {_site_key(s): s for s in sites}
    new_sites = [_new_site(s) for key, s in curr_sites.items() if key not in prev_sites]
    resolved_sites = [_resolved_site(s) for key, s in prev_sites.items() if key not in curr_sites]
    changed_sites = [
        _changed_site(curr_sites[key], prev_sites[key])
        for key in curr_sites.keys() & prev_sites.keys()
        if curr_sites[key].level != prev_sites[key].level
        or curr_sites[key].n_mismatch != prev_sites[key].n_mismatch
        or curr_sites[key].n_gap != prev_sites[key].n_gap
    ]

    prev_amps = {
        _amplicon_key(a): a
        for a in (previous.specificity.amplicons if previous.specificity else [])
    }
    curr_amps = {_amplicon_key(a): a for a in amplicons}
    new_amplicons = [_new_amplicon(a) for key, a in curr_amps.items() if key not in prev_amps]
    resolved_amplicons = [
        _resolved_amplicon(a) for key, a in prev_amps.items() if key not in curr_amps
    ]

    inclusivity_changes = _inclusivity_changes(previous.inclusivity, inclusivity)
    inclusivity_regressed = any(
        c.percent_after is not None
        and c.percent_before is not None
        and c.percent_after < c.percent_before
        for c in inclusivity_changes
    )

    variant_changes, variants_compared, variants_note = _variant_changes(
        previous.variant_summary, variant_summary, previous.generated_at
    )

    regressed = (
        section_regressed
        or any(v.kind == "new" and v.concern for v in variant_changes)
        or any(s.level_after in ("critical", "warning") for s in new_sites)
        or bool(new_amplicons)
        or inclusivity_regressed
    )

    h = HistoryResult(
        has_previous=True,
        previous_run_id=previous.run_id,
        previous_generated_at=previous.generated_at,
        inputs_changed=previous.inputs_hash != inputs_hash,
        verdict_before=previous.overall.verdict,
        section_changes=section_changes,
        new_sites=new_sites,
        resolved_sites=resolved_sites,
        changed_sites=changed_sites,
        new_amplicons=new_amplicons,
        resolved_amplicons=resolved_amplicons,
        inclusivity_changes=inclusivity_changes,
        variant_changes=variant_changes,
        variants_compared=variants_compared,
        variants_note=variants_note,
        verdict=Verdict.WARN if regressed else Verdict.PASS,
        rationale=[],
    )
    h.rationale = _rationale(h, section_changes, previous.generated_at)
    return h
