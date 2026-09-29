"""The summary at the top of the report: one table row per thing that was checked.

The tool re-checks an assay that is in use; it does not pass or fail it (user decision
2026-09-27, advisor subagent). So the report opens with what was checked, what was found (in
numbers), and whether a limit the laboratory configured
was crossed, instead of one verdict word above a list of sentences.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import Config
from ..inclusivity.models import fragment_window
from ..results import RunResult
from ..variants.exhaustive import channel_verdict, channels_shown
from ..verdict import STATUS_LABEL, Verdict
from .grouping import TIER_TITLE

_SEVERITY = {"FAIL": Verdict.FAIL, "INCOMPLETE": Verdict.INCOMPLETE, "WARN": Verdict.WARN}
_RANK = {Verdict.PASS: 0, Verdict.WARN: 1, Verdict.INCOMPLETE: 2, Verdict.FAIL: 3}


@dataclass
class SummaryRow:
    """One row of the "What was checked" table."""

    check: str
    scope: str
    result: str
    css: str  # chip class suffix: PASS, WARN, FAIL, INCOMPLETE or INFO
    label: str
    reason: str = ""
    anchor: str = ""


def _worst(levels: list[Verdict]) -> Verdict:
    return max(levels, key=_RANK.__getitem__) if levels else Verdict.PASS


def _row(
    check: str,
    scope: str,
    result: str,
    level: Verdict | None,
    reason: str = "",
    anchor: str = "",
    *,
    label: str | None = None,
) -> SummaryRow:
    if level is None:
        return SummaryRow(
            check, scope, result, "INCOMPLETE", label or "Not assessed", reason, anchor
        )
    return SummaryRow(
        check, scope, result, level.value, label or STATUS_LABEL[level], reason, anchor
    )


def _plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n:,} {one if n == 1 else (many or one + 's')}"


def _qc_row(result: RunResult) -> SummaryRow:
    qc = result.oligo_qc
    fail = [c for c in qc.checks if c.status.value == "FAIL"]
    warn = [c for c in qc.checks if c.status.value == "WARN"]
    flagged = [s for s in qc.structures if s.status.value in ("WARN", "FAIL")]
    res = (
        f"{len(fail)} outside the limit, {len(warn)} outside the preferred range; "
        f"{len(flagged)} of {len(qc.structures)} hairpins and dimers flagged"
    )
    reason = "; ".join(f"{c.name} ({c.display})" for c in fail or warn)
    if not reason and flagged:
        reason = "; ".join(s.label for s in flagged)
    if fail or warn:
        reason = ("outside the limit: " if fail else "outside the preferred range: ") + reason
    section = next(s for s in result.sections if s.key == "oligo_qc")
    return _row(
        "Oligo design (Tm, GC, runs, hairpins, dimers)",
        f"{_plural(len(qc.oligos), 'oligo')}, {len(qc.checks)} checks",
        res,
        section.verdict,
        reason,
        "oligo-qc",
    )


def _tier_rows(result: RunResult, cfg: Config, overview: list[Any]) -> list[SummaryRow]:
    spec = result.specificity
    if spec is None:
        section = next(s for s in result.sections if s.key == "specificity")
        return [_row("Off-target specificity", "–", section.note, None, "", "specificity")]
    rows: list[SummaryRow] = []
    for t in overview:
        marker = f"Tier '{t.tier}'"
        levels = [
            _SEVERITY[f.severity]
            for f in spec.findings
            if f.severity in _SEVERITY and marker in f.message
        ]
        amps = sorted(
            (a for a in spec.amplicons if a.tier == t.tier),
            key=lambda a: (a.classification != "likely_detected", a.length),
        )
        primer = [s for s in spec.sites if s.tier == t.tier and s.role != "probe"]
        crit = sum(s.level == "critical" for s in primer)
        warn = sum(s.level == "warning" for s in primer)
        if t.products:
            res = (
                f"{_plural(t.products, 'predicted product')}, {t.detected} of them detectable "
                "by the probe"
            )
        else:
            res = "no predicted product"
        res += f"; {crit} critical and {warn} warning primer sites"
        scope = _plural(t.n_taxa, "taxon", "taxa")
        if t.tier == "exclusivity" and result.exclusivity is not None:
            e = result.exclusivity
            scope = f"{e.n_resolved} of {_plural(e.n_organisms, 'organism name')} resolved"
            if e.verdict is not Verdict.PASS:
                levels.append(e.verdict)
        if t.incomplete:  # the saturation finding itself sets the level (tier marker)
            scope += f"; hit list incomplete for {', '.join(t.incomplete)}"
        reason = ""
        if amps:
            a = amps[0]
            reason = f"product {a.length} bp on {a.accession} ({a.organism or 'unknown'})"
            if len(amps) > 1:
                reason += f" and {len(amps) - 1} more"
        elif crit:
            reason = "critical primer sites, but no two facing each other (no product)"
        info = t.tier == "out_of_scope"
        rows.append(
            _row(
                f"Off-target: {t.title}",
                scope,
                res,
                Verdict.PASS if info else _worst(levels),
                reason,
                "specificity",
                label="Information only" if info else None,
            )
        )
        if info:
            rows[-1].css = "INFO"
    searched = {t.tier for t in overview}
    for tier in cfg.specificity.off_target_tiers:
        if tier not in searched:
            rows.append(
                _row(
                    f"Off-target: {TIER_TITLE.get(tier, tier)}",
                    "configured tier",
                    "not searched in this run",
                    None,
                    "",
                    "specificity",
                )
            )
    return rows


def _inclusivity_row(result: RunResult, cfg: Config) -> SummaryRow:
    inc = result.inclusivity
    section = next(s for s in result.sections if s.key == "inclusivity")
    if inc is None or not inc.tier_searched:
        return _row("Target detection", "–", section.note, None, "", "inclusivity")
    rules = cfg.inclusivity
    w = fragment_window(inc.fragment_years, rules.verdict_window_years)
    if not inc.exhaustive or w is None or w.percent is None:
        res = inc.rationale[0] if inc.rationale else section.note
        return _row(
            "Target detection (inclusivity)" if inc.exhaustive else "Target detection (sampled)",
            "whole fragment, no genome with the region yet"
            if inc.exhaustive
            else "per oligo and year",
            res,
            inc.verdict,
            "",
            "inclusivity",
        )
    what = "records" if inc.sample_scheme.startswith("Every NCBI Nucleotide record") else "genomes"
    pct = w.percent
    res = (
        f"{pct:.1f}% detectable, {100.0 * (w.detectable + w.at_risk) / w.n:.1f}% including at "
        f"risk, {100.0 * w.likely_failure / w.n:.1f}% likely failure"
    )
    scope = (
        f"whole fragment, {w.n:,} {what} released {w.first}–{w.last} "
        f"({w.undetermined:,} undetermined, not counted"
        + (f", of which {w.unassembled:,} copies possibly unassembled" if w.unassembled else "")
        + (f", {w.from_parts:,} detectable from parts" if w.from_parts else "")
        + ")"
    )
    if inc.verdict is Verdict.FAIL:
        reason = f"below your limit of {rules.fail_below_percent:g}% detectable"
    elif inc.verdict is Verdict.WARN:
        reason = (
            f"below your review limit of {rules.warn_below_percent:g}% detectable"
            if pct < rules.warn_below_percent
            else f"a single release year below {rules.fail_below_percent:g}%"
        )
    elif inc.verdict is Verdict.INCOMPLETE:
        reason = inc.rationale[0] if inc.rationale else ""
    else:
        reason = ""
    return _row("Target detection (inclusivity)", scope, res, inc.verdict, reason, "inclusivity")


def _channel_rows(result: RunResult, cfg: Config) -> list[SummaryRow]:
    """One row per detection channel (overhaul step 6), when channels differ in anything: its
    own target, detection over every assessed genome of it, and any signal elsewhere."""
    vs = result.variant_summary
    c = vs.coverage if vs else None
    if not channels_shown(c):
        return []
    rows = []
    for r in c.channel_results:  # type: ignore[union-attr]
        level, why = channel_verdict(r, cfg.inclusivity)
        judged = r.detected + r.not_detected
        scope = (f"{r.target_genomes:,} genomes of its target (taxon {r.target_taxid}), all "
                 f"years; {r.nontarget_genomes:,} other genomes of the scan")  # fmt: skip
        parts = [
            f"{r.detected_percent:.1f}% detected ({r.detected:,} of {judged:,})"
            if r.detected_percent is not None
            else "no target genome judged"
        ]
        if r.undetermined:
            parts.append(f"{r.undetermined:,} undetermined")
        if r.no_locus:
            parts.append(f"{r.no_locus:,} drafts without the region")
        if r.nontarget_genomes:
            parts.append(f"signal in {r.signal:,} of {r.nontarget_genomes:,} other genomes")
        dye = f" ({r.reporter})" if r.reporter else ""
        rows.append(_row(f"Detection per channel: {r.name}{dye}", scope, ", ".join(parts), level,
                         why, "channels"))  # fmt: skip
    return rows


def _coverage_row(result: RunResult) -> SummaryRow | None:
    vs = result.variant_summary
    c = vs.coverage if vs else None
    if c is None:
        return None
    what = "records" if c.source == "blast_partitioned" else "assemblies"
    scope = f"{c.listed_total:,} {what} listed by NCBI on {c.listed_at[:10]}"
    parts = [f"{c.assessed_total:,} assessed", f"region found in {c.found:,}"]
    if c.not_found:
        parts.append(f"not found in {c.not_found:,}")
    if c.masked:
        parts.append(f"hidden by N in {c.masked:,}")
    if c.contig_break:
        parts.append(
            f"cut by a {'record' if what == 'records' else 'contig'} end in {c.contig_break:,}"
        )
    if c.unavailable:
        parts.append(f"{c.unavailable:,} could not be downloaded")
    if c.related_only:
        parts.append(f"only related regions (not the target) in {c.related_only:,}")
    if c.complete:
        level, reason = Verdict.PASS, ""
    else:
        level = Verdict.INCOMPLETE
        reason = (
            f"{c.listed_total - c.assessed_total - c.unavailable:,} not assessed yet: run again"
        )
    return _row(
        "Coverage of the target",
        scope,
        ", ".join(parts),
        level,
        reason,
        "variants",
    )


def summary_rows(result: RunResult, cfg: Config, overview: list[Any]) -> list[SummaryRow]:
    """The rows of the "What was checked" table, in reading order."""
    rows = [_qc_row(result)]
    if result.mode != "qc-only":
        rows += _tier_rows(result, cfg, overview)
        rows.append(_inclusivity_row(result, cfg))
        rows += _channel_rows(result, cfg)
        cov = _coverage_row(result)
        if cov is not None:
            rows.append(cov)
    rows += _unshown_rows(result, rows)
    return rows


# which summary rows (by anchor) show each section's status
_SECTION_ROWS = {
    "oligo_qc": "oligo-qc",
    "specificity": "specificity",
    "amplicon_prediction": "specificity",
    "exclusivity": "specificity",
    "inclusivity": "inclusivity",
}


def _unshown_rows(result: RunResult, rows: list[SummaryRow]) -> list[SummaryRow]:
    """A row for every required section whose status no row shows yet, so the table can never
    read "No flags" while the status line does not (code review, 2026-09-27): e.g. a
    specificity finding that belongs to no search tier (a sequence window that could not be
    fetched, no perfect hit on the intended target) or an organism list that was not searched."""
    out: list[SummaryRow] = []
    required = set(result.overall.required_sections)
    for section in result.sections:
        if section.key not in required:
            continue
        level = section.verdict or Verdict.INCOMPLETE
        anchor = _SECTION_ROWS.get(section.key, "")
        shown = [
            Verdict(r.css)
            for r in rows  # not the rows added here: each section gets its own reason
            if r.anchor == anchor and r.css in Verdict.__members__
        ]
        if _RANK[level] <= _RANK[_worst(shown)]:
            continue
        reason = section.note
        spec = result.specificity
        if section.key in ("specificity", "amplicon_prediction") and spec is not None:
            untiered = [
                f.message
                for f in spec.findings
                if _SEVERITY.get(f.severity) is level and "Tier '" not in f.message
            ]
            reason = untiered[0] if untiered else reason
        title = "Off-target search" if anchor == "specificity" else section.title
        if section.key == "exclusivity":
            title = section.title
        if any(r.check == title and r.result == reason for r in out):
            continue  # sites and products share their untiered finding
        out.append(_row(title, "–", reason, section.verdict, "", anchor))
    return out
