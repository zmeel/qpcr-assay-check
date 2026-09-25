"""Command-line interface."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
import yaml
from pydantic import ValidationError

from . import __version__
from .config import Config, default_config_text, format_validation_error, load_config
from .errors import InputError, QpcrAssayCheckError
from .models import Assay
from .pipeline import evaluate, write_outputs
from .verdict import EXIT_CODES, EXIT_INPUT_ERROR, EXIT_NCBI_ERROR, Verdict

app = typer.Typer(
    name="qpcr-assay-check",
    help=(
        "Evaluate one real-time PCR (TaqMan) assay in silico and write a versioned evaluation "
        "record. In silico analysis does not replace experimental validation."
    ),
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)
log = logging.getLogger("qpcr_assay_check")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"qpcr-assay-check {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = False,
) -> None:
    """qpcr-assay-check."""


def _setup_logging(verbose: int) -> None:
    level = logging.WARNING if verbose == 0 else logging.INFO if verbose == 1 else logging.DEBUG
    logging.basicConfig(
        level=level, format="%(levelname)s %(name)s: %(message)s", stream=sys.stderr
    )


def _fail(message: str, code: int = EXIT_INPUT_ERROR) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code)


def _read_assay_file(path: Path) -> dict[str, Any]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise InputError(f"Cannot read assay file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise InputError(f"Assay file {path} must contain a YAML mapping")
    return data


def build_assay(path: Path | None, overrides: dict[str, Any]) -> Assay:
    """Assemble an assay from an optional YAML file plus command-line overrides."""
    data = _read_assay_file(path) if path else {}
    target = dict(data.get("target") or {})
    for key in ("taxid", "accession", "gene"):
        if overrides.get(f"target_{key}") is not None:
            target[key] = overrides[f"target_{key}"]
    for key, value in overrides.items():
        if value is not None and not key.startswith("target_") and value != []:
            data[key] = value
    data["target"] = {k: v for k, v in target.items() if v not in (None, "")}
    try:
        return Assay.model_validate(data)
    except ValidationError as exc:
        raise InputError(f"Invalid assay definition:\n{format_validation_error(exc)}") from exc


@app.command()
def validate(
    assay_file: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="Assay YAML file.")
    ],
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Configuration YAML.")
    ] = None,
) -> None:
    """Check an assay file and configuration without running any analysis."""
    try:
        assay = build_assay(assay_file, {})
        cfg = load_config(config, assay.settings)
    except QpcrAssayCheckError as exc:
        _fail(str(exc))
        return
    typer.echo(f"OK: '{assay.assay_name}' ({assay.template_type.value}) is valid.")
    for o in assay.oligo_list:
        name = o.role if o.name == o.role else f"{o.role} {o.name}"
        typer.echo(f"  {name:8} {o.sequence} ({len(o.sequence)} nt)")
    typer.echo(f"  configuration: annealing {cfg.reaction.annealing_temp_C:g} °C")
    if assay.settings:
        typer.echo(f"  settings from the assay file: {', '.join(sorted(assay.settings))}")


@app.command()
def run(
    assay_file: Annotated[
        Path | None, typer.Argument(exists=True, dir_okay=False, help="Assay YAML file.")
    ] = None,
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Configuration YAML.")
    ] = None,
    outdir: Annotated[Path, typer.Option("--outdir", "-o", help="Base output directory.")] = Path(
        "results"
    ),
    qc_only: Annotated[
        bool, typer.Option("--qc-only", help="Only oligo QC; the verdict then covers QC alone.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be sent to NCBI; send nothing.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Do not ask before sending oligos to NCBI.")
    ] = False,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, help="More logging.")] = 0,
    name: Annotated[str | None, typer.Option(help="Assay name.")] = None,
    forward: Annotated[str | None, typer.Option(help="Forward primer, 5'->3'.")] = None,
    reverse: Annotated[str | None, typer.Option(help="Reverse primer, 5'->3'.")] = None,
    probe: Annotated[str | None, typer.Option(help="Probe, 5'->3'.")] = None,
    probe_reporter: Annotated[str | None, typer.Option(help="Reporter dye, e.g. FAM.")] = None,
    probe_quencher: Annotated[str | None, typer.Option(help="Quencher, e.g. BHQ1.")] = None,
    probe_modification: Annotated[
        list[str] | None, typer.Option(help="Probe modification (repeatable), e.g. MGB.")
    ] = None,
    template_type: Annotated[str | None, typer.Option(help="DNA or RNA.")] = None,
    target_taxid: Annotated[
        int | None, typer.Option(help="NCBI taxonomy ID of the target.")
    ] = None,
    target_accession: Annotated[str | None, typer.Option(help="Reference accession.")] = None,
    target_gene: Annotated[str | None, typer.Option(help="Target gene name.")] = None,
    reference_amplicon: Annotated[
        str | None, typer.Option(help="Sense-strand reference amplicon (optional).")
    ] = None,
) -> None:
    """Evaluate one assay and write results.json, report.html, hits.tsv and results.xlsx.

    Without --qc-only this runs the tiered remote BLAST searches (the oligo sequences are sent to
    NCBI; you are asked first), re-aligns the hits over the full oligo length, predicts products
    and judges specificity. Interrupted runs resume when you run the same command again.
    Command-line options override values in the assay file. The exit code reflects the
    verdict: 0 PASS, 10 WARN, 20 FAIL, 30 INCOMPLETE, 64 invalid input, 70 NCBI problem.
    """
    _setup_logging(verbose)
    overrides: dict[str, Any] = {
        "assay_name": name,
        "forward": forward,
        "reverse": reverse,
        "probe": probe,
        "probe_reporter": probe_reporter,
        "probe_quencher": probe_quencher,
        "probe_modifications": probe_modification or [],
        "template_type": template_type.upper() if template_type else None,
        "target_taxid": target_taxid,
        "target_accession": target_accession,
        "target_gene": target_gene,
        "reference_amplicon": reference_amplicon,
    }
    if assay_file is None and not any(v for v in overrides.values()):
        _fail("give an assay file or at least --name, --forward, --reverse, --probe and a target.")
    from .ncbi.http import NcbiError

    try:
        assay = build_assay(assay_file, overrides)
        cfg = load_config(config, assay.settings)
        if qc_only:
            result = evaluate(assay, cfg, qc_only=True)
        else:
            result = _evaluate_with_search(assay, cfg, outdir, dry_run=dry_run, yes=yes)
            if result is None:  # dry run
                return
        run_dir = write_outputs(result, outdir, cfg)
    except NcbiError as exc:
        typer.echo(f"NCBI problem: {exc}", err=True)
        raise typer.Exit(EXIT_NCBI_ERROR) from exc
    except QpcrAssayCheckError as exc:
        _fail(str(exc))
        return

    typer.echo(f"Verdict: {result.overall.verdict.value}")
    for line in result.overall.rationale:
        typer.echo(f"  - {line}")
    typer.echo(f"Record written to {run_dir}")
    raise typer.Exit(result.overall.exit_code)


@app.command()
def init(
    directory: Annotated[Path, typer.Argument(help="Directory to write into.")] = Path("."),
    example: Annotated[
        bool,
        typer.Option(
            "--example", help="Write the verified CDC N1 example instead of a blank template."
        ),
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Overwrite existing files.")] = False,
) -> None:
    """Write a starter assay.yaml (every option explained) and a fully commented config.yaml."""
    from importlib import resources

    directory.mkdir(parents=True, exist_ok=True)
    if example:
        assay_text = (
            resources.files("qpcr_assay_check") / "data" / "examples" / "cdc_2019-nCoV_N1.yaml"
        ).read_text(encoding="utf-8")
    else:  # every option, explained (the same file as examples/assay_template.yaml)
        template = resources.files("qpcr_assay_check") / "data" / "assay_template.yaml"
        assay_text = template.read_text(encoding="utf-8")
    for filename, text in (("assay.yaml", assay_text), ("config.yaml", default_config_text())):
        target = directory / filename
        if target.exists() and not force:
            _fail(f"{target} already exists (use --force to overwrite).", 1)
        target.write_text(text, encoding="utf-8")
        typer.echo(f"Wrote {target}")


def _evaluate_with_search(assay: Assay, cfg: Config, outdir: Path, *, dry_run: bool, yes: bool):
    """Full evaluation: remote searches, full-length assessment, verdicts.

    The exclusivity tier's taxonomy IDs are resolved from the organism list when the search
    actually runs (needs the network and NCBI_EMAIL), so a --dry-run plan cannot show them; it
    shows the organism-list name count instead (see planner.plan_searches).
    """
    from .ncbi.blast import BlastApi
    from .ncbi.eutils import Eutils
    from .ncbi.jobs import JobStore
    from .ncbi.runner import BlastRunner
    from .search.execute import run_remote_search
    from .search.planner import plan_searches
    from .specificity.assess import assess_specificity
    from .specificity.fetch import WindowFetcher
    from .specificity.variants import assess_target_sites
    from .variants.datasets import DatasetsClient
    from .variants.exhaustive import run_exhaustive
    from .variants.partitioned import collect_partitioned

    if dry_run:
        plan = plan_searches(assay, cfg)
        for line in _describe_plan(plan):
            typer.echo(line)
        if not plan.searches:
            raise InputError(
                "Nothing to search: give the assay a target taxid or configure background taxa."
            )
        typer.echo("Dry run: nothing was sent to NCBI.")
        return None

    def show(plan: Any) -> None:
        for line in _describe_plan(plan):
            typer.echo(line)

    remote = run_remote_search(
        assay,
        cfg,
        outdir,
        confirm=_make_confirm(yes),
        keep_tiers=set(cfg.specificity.off_target_tiers) | {"target"},
        on_plan=show,
    )
    from .history.store import find_previous_run
    from .inclusivity.aggregate import compute_inclusivity
    from .ncbi.http import NcbiError
    from .taxonomy.resolve import fetch_lineages
    from .taxonomy.rollup import taxonomy_breakdown

    previous_run = find_previous_run(outdir, assay.slug)
    eutils = Eutils(remote.http, cfg.ncbi.eutils_url)
    fetcher = WindowFetcher(eutils, remote.cache)
    specificity = assess_specificity(
        assay, cfg, remote.plan, remote.parsed, remote.outcome, fetcher
    )
    try:
        breakdown = taxonomy_breakdown(
            specificity.sites, eutils, remote.cache, ttl_days=cfg.ncbi.taxonomy_cache_ttl_days
        )
    except NcbiError as exc:
        # Informational only (not a required section): a lineage-lookup failure should not
        # discard an otherwise-complete specificity verdict.
        log.warning("Could not fetch taxonomy lineages for the breakdown: %s", exc)
        breakdown = []
    try:
        # Same lineage lookup the breakdown above needs (cache-backed, so this adds no extra
        # NCBI calls for taxids already fetched there), plus the exclusivity list's own resolved
        # taxids: lets a hit filed under a more specific descendant taxid (e.g. a named influenza
        # strain) than an organism-list entry's own taxid still be grouped onto that entry's row
        # by species, instead of only ever matching on exact taxid equality (see
        # taxonomy/exclusivity.py and docs/ARCHITECTURE.md).
        excl_taxids = remote.organism_resolution.taxids if remote.organism_resolution else []
        site_taxids = {s.taxid for s in specificity.sites if s.taxid is not None}
        lineages = fetch_lineages(
            eutils, remote.cache, sorted(site_taxids | set(excl_taxids)),
            ttl_days=cfg.ncbi.taxonomy_cache_ttl_days,
        )  # fmt: skip
        taxon_species = {t: lin.species for t, lin in lineages.items() if lin.species}
    except NcbiError as exc:
        log.warning("Could not fetch taxonomy lineages for exclusivity grouping: %s", exc)
        taxon_species = {}
    tier_searched = any(r.tier == "target" for r in remote.outcome.searches)
    exhaustive, variant_note = None, None
    if cfg.variants.source in ("datasets", "blast_partitioned"):
        # Every genome assembly (datasets) or every Nucleotide record (blast_partitioned) of the
        # target (v1.1.0), not the target tier's BLAST hits, which are BLAST's best matches and
        # so biased toward perfect ones when the hit list is full.
        collector = None
        if cfg.variants.source == "blast_partitioned":
            runner = BlastRunner(
                BlastApi(remote.http, cfg.ncbi.blast_url), remote.cache,
                JobStore(remote.cache.root / "variants" / "jobs-partitioned.json"), cfg.ncbi,
                cfg.search.result_format,
            )  # fmt: skip

            def collector(store: Any, taxon: int, amplicon: str, context: Any) -> Any:
                return collect_partitioned(
                    eutils, runner, runner.store, fetcher, store, taxon, amplicon, cfg,
                    context=context,
                )  # fmt: skip

        try:
            exhaustive = run_exhaustive(
                assay, cfg, DatasetsClient(remote.http, cfg.ncbi.datasets_url),
                remote.cache.root, eutils.fetch_fasta,
                collector=collector, source=cfg.variants.source,
            )  # fmt: skip
        except (InputError, NcbiError) as exc:
            variant_note = (
                f"the exhaustive analysis was not run ({exc}); the variant tables and "
                "inclusivity use the target tier's BLAST hits instead."
            )
            log.warning("%s", variant_note)
    try:
        target_sites = (
            exhaustive.sites
            if exhaustive is not None
            else assess_target_sites(assay, cfg, remote.plan, remote.parsed, fetcher)
            if tier_searched
            else None
        )
    except NcbiError as exc:
        # Informational only (the variant summary has no verdict): a fetch failure here should
        # not discard an otherwise-complete specificity/exclusivity verdict.
        log.warning("Could not build the variant summary: %s", exc)
        target_sites = None
    try:
        inclusivity = (
            exhaustive.inclusivity
            if exhaustive is not None
            else compute_inclusivity(
                assay,
                cfg,
                remote.plan,
                remote.parsed,
                fetcher,
                eutils,
                remote.cache,
                tier_searched=tier_searched,
            )
        )
    except NcbiError as exc:
        # Informational only (not a required section): a date-lookup failure should not
        # discard an otherwise-complete specificity/exclusivity verdict.
        log.warning("Could not compute inclusivity: %s", exc)
        inclusivity = None
    return evaluate(
        assay,
        cfg,
        specificity=specificity,
        search_outcome=remote.outcome,
        organism_resolution=remote.organism_resolution,
        taxonomy_breakdown=breakdown,
        taxon_species=taxon_species,
        inclusivity=inclusivity,
        target_sites=target_sites,
        variant_coverage=exhaustive.coverage if exhaustive is not None else None,
        release_dates=exhaustive.release_dates if exhaustive is not None else None,
        variant_note=variant_note,
        previous_run=previous_run,
    )


def _make_confirm(yes: bool) -> Any:
    """Confirmation callback: sequences are only sent to NCBI after the user agrees."""

    def confirm(fresh: list[Any], plan: Any) -> bool:
        if yes:
            return True
        typer.echo(
            f"{len(fresh)} search(es) will send the sequences above to NCBI's public servers."
        )
        try:
            typer.confirm("Continue?", abort=True)
        except typer.Abort:
            return False
        return True

    return confirm


def _describe_plan(plan: Any) -> list[str]:
    lines = ["Oligo sequences that would be sent to NCBI (BLAST, database core_nt):"]
    lines += [f"  {label:12} {seq}" for label, seq in plan.queries.items()]
    lines.append(f"Planned searches: {len(plan.searches)}")
    for ps in plan.searches:
        where = ps.entrez_query or "(no taxon restriction)"
        lines.append(f"  - {ps.label}: {where}")
    lines += [f"Note: {n}" for n in plan.notes]
    lines += [f"WARNING: {w}" for w in plan.warnings]
    return lines


@app.command()
def search(
    assay_file: Annotated[
        Path, typer.Argument(exists=True, dir_okay=False, help="Assay YAML file.")
    ],
    config: Annotated[
        Path | None, typer.Option("--config", "-c", help="Configuration YAML.")
    ] = None,
    outdir: Annotated[Path, typer.Option("--outdir", "-o", help="Base output directory.")] = Path(
        "results"
    ),
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be sent to NCBI; send nothing.")
    ] = False,
    yes: Annotated[
        bool, typer.Option("--yes", "-y", help="Do not ask before sending oligos to NCBI.")
    ] = False,
    verbose: Annotated[int, typer.Option("--verbose", "-v", count=True, help="More logging.")] = 0,
) -> None:
    """Run the tiered remote BLAST searches and write hits.tsv and search.json.

    Needs NCBI_EMAIL (and optionally NCBI_API_KEY) in the environment. The oligo sequences are
    sent to NCBI. Interrupted runs resume when you run the same command again. Exit codes:
    0 complete, 10 complete but a hit list is saturated, 64 invalid input, 70 NCBI problem
    (resumable).
    """
    from .ncbi.http import NcbiError
    from .search.execute import run_remote_search
    from .search.planner import plan_searches

    _setup_logging(verbose)
    try:
        assay = build_assay(assay_file, {})
        cfg = load_config(config, assay.settings)
    except QpcrAssayCheckError as exc:
        _fail(str(exc))
        return

    if dry_run:
        try:
            plan = plan_searches(assay, cfg)
        except QpcrAssayCheckError as exc:
            _fail(str(exc))
            return
        for line in _describe_plan(plan):
            typer.echo(line)
        if not plan.searches:
            _fail("Nothing to search: give the assay a target taxid or configure background taxa.")
            return
        typer.echo("Dry run: nothing was sent to NCBI.")
        return

    def show(plan: Any) -> None:
        for line in _describe_plan(plan):
            typer.echo(line)

    try:
        remote = run_remote_search(assay, cfg, outdir, confirm=_make_confirm(yes), on_plan=show)
    except NcbiError as exc:
        typer.echo(f"NCBI problem: {exc}", err=True)
        raise typer.Exit(EXIT_NCBI_ERROR) from exc
    except QpcrAssayCheckError as exc:
        _fail(str(exc))
        return
    outcome, search_dir = remote.outcome, remote.search_dir

    total = sum(sum(r.n_hits.values()) for r in outcome.searches)
    typer.echo(f"Done: {len(outcome.searches)} search(es), {total} hits in total.")
    for w in outcome.warnings:
        typer.echo(f"WARNING: {w}")
    typer.echo(f"Results written to {search_dir}")
    raise typer.Exit(EXIT_CODES[Verdict.WARN] if outcome.saturated else 0)
