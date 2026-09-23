"""Orchestration: turn an assay + configuration into a complete, versioned evaluation record."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
from datetime import UTC, datetime
from pathlib import Path

import primer3

from . import __version__
from .config import Config
from .history.diff import compute_history
from .inclusivity.models import InclusivityResult
from .models import Assay, Status
from .oligo.qc import run_oligo_qc
from .results import OverallResult, RunResult, SectionResult
from .search.orchestrate import SearchOutcome
from .search.planner import HUMAN_TAXID
from .specificity.models import SiteResult, SpecificityResult
from .specificity.variants import VariantSummary, build_variant_summary
from .taxonomy.exclusivity import ExclusivityResult, build_exclusivity
from .taxonomy.plan import OrganismListResolution
from .taxonomy.rollup import TaxonCount
from .variants.models import ExhaustiveCoverage
from .verdict import Verdict, combine, exit_code, verdict_from_status

log = logging.getLogger(__name__)


def inputs_hash(assay: Assay, cfg: Config) -> str:
    """SHA-256 over the canonical JSON of the assay definition and the effective config."""
    # Operational settings (timeouts, cache location, report options) do not change the science,
    # so they must not change the hash that identifies "the same evaluation".
    payload = {
        "assay": assay.model_dump(mode="json"),
        "config": cfg.model_dump(
            mode="json",
            exclude={"ncbi": True, "report": True, "variants": {"max_assemblies_per_run"}},
        ),  # fmt: skip
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _inclusivity_title(inclusivity: InclusivityResult | None) -> str:
    if inclusivity is not None and inclusivity.exhaustive:
        return "Inclusivity across the intended target (all genome assemblies)"
    return "Inclusivity across the intended target (sampled)"


def _rationale(qc_findings: list[str], not_evaluated: list[str]) -> list[str]:
    lines = list(qc_findings)
    if not_evaluated:
        lines.append("Not evaluated: " + "; ".join(not_evaluated) + ".")
    return lines


def evaluate(
    assay: Assay,
    cfg: Config,
    *,
    qc_only: bool = False,
    now: datetime | None = None,
    specificity: SpecificityResult | None = None,
    search_outcome: SearchOutcome | None = None,
    organism_resolution: OrganismListResolution | None = None,
    taxonomy_breakdown: list[TaxonCount] | None = None,
    taxon_species: dict[int, str] | None = None,
    inclusivity: InclusivityResult | None = None,
    target_sites: list[SiteResult] | None = None,
    variant_coverage: ExhaustiveCoverage | None = None,
    release_dates: dict[str, str] | None = None,
    variant_note: str | None = None,
    previous_run: RunResult | None = None,
) -> RunResult:
    """Run every analysis that exists in this version and assemble the evaluation record."""
    now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    digest = inputs_hash(assay, cfg)
    qc = run_oligo_qc(assay, cfg)

    findings = [
        f"{c.name}: {c.message}"
        for c in qc.checks
        if c.status in (Status.FAIL, Status.WARN) and c.message
    ]
    findings += [
        f"{s.label}: structure with Tm {s.tm_c:.1f} °C at {s.temp_c:g} °C ({s.status.value})."
        for s in qc.structures
        if s.status in (Status.FAIL, Status.WARN) and s.tm_c is not None
    ]

    sections = [
        SectionResult(
            key="oligo_qc",
            title="Oligo quality control",
            state="evaluated",
            verdict=verdict_from_status(qc.status),
            note=(
                f"{sum(c.status is Status.FAIL for c in qc.checks)} FAIL, "
                f"{sum(c.status is Status.WARN for c in qc.checks)} WARN among "
                f"{len(qc.checks)} checks; "
                f"{sum(s.status in (Status.WARN, Status.FAIL) for s in qc.structures)} of "
                f"{len(qc.structures)} structure calculations flagged."
            ),
        )
    ]
    exclusivity: ExclusivityResult | None = None
    variant_summary: VariantSummary | None = None
    human_not_searched = search_outcome is not None and not any(
        HUMAN_TAXID in r.taxids for r in search_outcome.searches if r.tier != "target"
    )
    if specificity is not None:
        if target_sites is not None:
            variant_summary = build_variant_summary(
                target_sites, assay, release_dates=release_dates, coverage=variant_coverage
            )
            variant_summary.target_list_full = (
                variant_coverage is None
                and bool(search_outcome)
                and any(
                    sat.list_full
                    for r in search_outcome.searches
                    if r.tier == "target"
                    for sat in r.saturation
                )
            )
        n = specificity.n_sites
        sections.append(
            SectionResult(
                key="specificity",
                title="Specificity: off-target primer and probe sites",
                state="evaluated",
                verdict=specificity.verdict_sites,
                note=(
                    f"{n.get('critical', 0)} critical and {n.get('warning', 0)} warning sites; "
                    f"{specificity.n_fetched} sequence windows used, "
                    f"{specificity.n_fetch_failed} could not be fetched."
                    + (" Human background was not searched." if human_not_searched else "")
                ),
            )
        )
        sections.append(
            SectionResult(
                key="amplicon_prediction",
                title="Predicted off-target products",
                state="evaluated",
                verdict=specificity.verdict_amplicons,
                note=f"{len(specificity.amplicons)} predicted product(s).",
            )
        )
        tier_searched = bool(search_outcome) and any(
            r.tier == "exclusivity" for r in search_outcome.searches
        )
        exclusivity = build_exclusivity(
            organism_resolution,
            specificity.sites,
            specificity.amplicons,
            cfg.specificity.severity,
            tier_searched=tier_searched,
            target_taxid=assay.target.taxid,
            taxon_species=taxon_species,
        )
        n_hit = sum(1 for r in exclusivity.rows if r.n_sites)
        note = f"{exclusivity.n_resolved}/{exclusivity.n_organisms} organism name(s) resolved"
        note += f"; {n_hit} had at least one relevant hit." if exclusivity.n_resolved else "."
        if exclusivity.unresolved:
            note += f" {len(exclusivity.unresolved)} name(s) not resolved (see rationale)."
        n_target = sum(1 for r in exclusivity.rows if r.is_target)
        if n_target:
            note += (
                f" {n_target} name(s) are the assay's own intended target and were excluded "
                "from this search."
            )
        if not tier_searched:
            note = "The exclusivity tier was not searched in this run."
        sections.append(
            SectionResult(
                key="exclusivity",
                title="Exclusivity against the clinical organism list",
                state="evaluated",
                verdict=exclusivity.verdict,
                note=note,
            )
        )
    else:
        for key, title in (
            ("specificity", "Specificity: off-target primer and probe sites"),
            ("amplicon_prediction", "Predicted off-target products"),
            ("exclusivity", "Exclusivity against the clinical organism list"),
        ):
            sections.append(
                SectionResult(
                    key=key,
                    title=title,
                    state="skipped",
                    verdict=None,
                    note="Skipped (--qc-only)." if qc_only else "No search results were supplied.",
                )
            )
    if inclusivity is not None:
        note = (
            inclusivity.sample_scheme
            if inclusivity.tier_searched
            else "The target tier was not searched in this run."
        )
        sections.append(
            SectionResult(
                key="inclusivity",
                title=_inclusivity_title(inclusivity),
                state="evaluated",
                verdict=inclusivity.verdict,
                note=note,
            )
        )
    else:
        sections.append(
            SectionResult(
                key="inclusivity",
                title=_inclusivity_title(inclusivity),
                state="skipped",
                verdict=None,
                note="Skipped (--qc-only)." if qc_only else "No search results were supplied.",
            )
        )
    history = None
    if qc_only:
        sections.append(
            SectionResult(
                key="history",
                title="Comparison with the previous run",
                state="skipped",
                verdict=None,
                note="Skipped (--qc-only).",
            )
        )
    else:
        history = compute_history(
            previous_run,
            inputs_hash=digest,
            section_verdicts={s.key: s.verdict for s in sections},
            section_titles={s.key: s.title for s in sections},
            sites=specificity.sites if specificity else [],
            amplicons=specificity.amplicons if specificity else [],
            inclusivity=inclusivity,
            variant_summary=variant_summary,
        )
        if history.has_previous:
            note = f"Compared to the run on {history.previous_generated_at}: {history.rationale[0]}"
            if len(history.rationale) > 1:
                note += f" (+{len(history.rationale) - 1} more change(s), see rationale)."
        else:
            note = history.rationale[0]
        sections.append(
            SectionResult(
                key="history",
                title="Comparison with the previous run",
                state="evaluated",
                verdict=history.verdict,
                note=note,
            )
        )

    required = ["oligo_qc"] if qc_only else [s.key for s in sections]
    by_key: dict[str, Verdict | None] = {s.key: s.verdict for s in sections}
    verdict = combine(by_key, required)
    not_evaluated = [s.title for s in sections if s.key in required and s.verdict is None]

    if specificity is not None:
        findings += [
            f"Specificity: {f.message}"
            for f in specificity.findings
            if f.severity in ("FAIL", "INCOMPLETE", "WARN")
        ]
    if variant_coverage is not None and not variant_coverage.complete:
        c = variant_coverage
        findings.append(
            f"Variant analysis: {c.assessed_total} of {c.listed_total} genome assemblies of the "
            f"target assessed so far (at most {c.budget_per_run} new ones per run, newest first). "
            "Run again to continue; the variant tables and inclusivity cover only the assessed "
            "assemblies until then."
        )
    if (
        variant_coverage is not None
        and variant_coverage.target_on_plasmid
        and variant_coverage.not_found_with_plasmid
    ):
        c = variant_coverage
        findings.append(
            f"Variant analysis: {c.not_found_with_plasmid} genome assembl"
            f"{'y contains' if c.not_found_with_plasmid == 1 else 'ies contain'} plasmid "
            "sequence but not the target region (e.g. "
            f"{', '.join(c.not_found_with_plasmid_examples[:5])}). The target lies on a plasmid, "
            "so this may be a deletion that the assay would miss (as with the Swedish nvCT "
            "variant), or an incomplete plasmid assembly: review these records."
        )
    if variant_note:
        findings.append(f"Variant analysis: {variant_note}")
    if human_not_searched:
        findings.append(
            f"Human background: no search in this run covered human (taxid {HUMAN_TAXID}), so "
            "off-target binding to human DNA was not evaluated. Add 9606 to "
            "'search.background_taxids' to include it."
        )
    if exclusivity is not None and exclusivity.unresolved:
        names = ", ".join(r.name for r in exclusivity.unresolved[:10])
        n_more = len(exclusivity.unresolved) - 10
        more = f" (+{n_more} more)" if n_more > 0 else ""
        findings.append(
            f"Exclusivity: {len(exclusivity.unresolved)} organism-list name(s) did not resolve to "
            f"exactly one taxonomy ID and were not searched: {names}{more}. Review the organism "
            "list; never guessed."
        )
    if inclusivity is not None and inclusivity.verdict is not Verdict.PASS:
        findings += [f"Inclusivity: {line}" for line in inclusivity.rationale]
    if history is not None and history.verdict is not Verdict.PASS:
        findings += [f"History: {line}" for line in history.rationale]
    if not findings and verdict is Verdict.PASS:
        findings = ["No oligo QC check raised a WARN or FAIL."]
    overall = OverallResult(
        verdict=verdict,
        exit_code=exit_code(verdict),
        rationale=_rationale(findings, not_evaluated),
        required_sections=required,
    )

    return RunResult(
        tool={"name": "qpcr-assay-check", "version": __version__},
        run_id=f"{assay.slug}-{now:%Y%m%dT%H%M%SZ}-{digest[:8]}",
        generated_at=now.isoformat().replace("+00:00", "Z"),
        inputs_hash=digest,
        mode="qc-only" if qc_only else "full",
        network_used=search_outcome is not None,
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "primer3-py": getattr(primer3, "__version__", "unknown"),
        },
        assay=assay,
        config=cfg.model_dump(mode="json"),
        oligo_qc=qc,
        specificity=specificity,
        exclusivity=exclusivity,
        taxonomy_breakdown=taxonomy_breakdown or [],
        variant_summary=variant_summary,
        inclusivity=inclusivity,
        history=history,
        search=search_outcome.model_dump(mode="json") if search_outcome else None,
        sections=sections,
        overall=overall,
    )


def write_outputs(result: RunResult, base_dir: Path, cfg: Config) -> Path:
    """Write results.json, report.html and results.xlsx; return the run directory."""
    from .report.html import render_report
    from .report.tsv import write_hits_tsv
    from .report.xlsx import write_workbook

    parent = base_dir / result.assay.slug
    parent.mkdir(parents=True, exist_ok=True)
    run_dir = parent / result.run_id
    for attempt in range(2, 100):  # never overwrite an existing evaluation record
        try:
            run_dir.mkdir()
            break
        except FileExistsError:
            run_dir = parent / f"{result.run_id}-{attempt}"
    else:  # pragma: no cover - would need ~100 runs in one second
        raise RuntimeError(f"could not create a unique run directory under {parent}")
    (run_dir / "results.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "report.html").write_text(render_report(result, cfg), encoding="utf-8")
    write_workbook(result, run_dir / "results.xlsx")
    if result.specificity is not None:
        write_hits_tsv(result, run_dir / "hits.tsv")
    log.info("Wrote evaluation record to %s", run_dir)
    return run_dir
