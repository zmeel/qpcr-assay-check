"""Run a search plan against NCBI (resumable) and keep what the assessment needs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ..config import Config
from ..errors import InputError
from ..models import Assay
from ..ncbi.blast import BlastApi
from ..ncbi.cache import Cache
from ..ncbi.eutils import Eutils
from ..ncbi.http import NcbiError, NcbiHttp
from ..ncbi.jobs import Job, JobStore
from ..ncbi.parser import ParsedSearch
from ..ncbi.runner import BlastRunner
from ..ncbi.settings import credentials_from_env
from ..pipeline import inputs_hash
from ..taxonomy.plan import OrganismListResolution, resolve_organism_list
from ..taxonomy.resolve import ancestors, outside_target
from .orchestrate import SearchOutcome, run_search
from .planner import NOTHING_TO_SEARCH, PlannedSearch, SearchPlan, plan_searches
from .tiers import TierTaxa, assay_tier_taxa, check_tier_taxa, dedupe


class Aborted(InputError):
    """The user declined to send the oligo sequences to NCBI."""


@dataclass
class RemoteSearch:
    """Everything produced by executing a search plan."""

    plan: SearchPlan
    outcome: SearchOutcome
    parsed: dict[str, ParsedSearch]
    search_dir: Path
    digest: str
    http: NcbiHttp
    cache: Cache
    organism_resolution: OrganismListResolution | None = None


def search_dir_for(assay: Assay, cfg: Config, outdir: Path) -> tuple[Path, str]:
    """Directory holding the resumable state of this assay's searches (keyed by inputs hash)."""
    digest = inputs_hash(assay, cfg)
    return outdir / assay.slug / f"search-{digest[:8]}", digest


def _resolve_and_plan(
    assay: Assay, cfg: Config, http: NcbiHttp, cache: Cache, *, only_tiers: set[str] | None
) -> tuple[SearchPlan, OrganismListResolution | None]:
    """Build the real (network-informed) search plan: resolve the organism list first.

    Skipped when ``only_tiers`` is given and excludes "exclusivity" (e.g. a validation run
    scoped to one other tier), so that run makes no unrelated Entrez Taxonomy calls.
    """
    resolution = None
    excl_taxids = None
    excl_unresolved = 0
    exclude = assay.target.excluded_taxids
    if exclude and assay.target.taxid is not None:
        wrong = outside_target(
            Eutils(http, cfg.ncbi.eutils_url), cache, assay.target.taxid, exclude,
            ttl_days=cfg.ncbi.taxonomy_cache_ttl_days,
        )  # fmt: skip
        if wrong:
            raise InputError(
                "Taxa left out of the target (target.taxa) must lie inside the target taxon "
                f"{assay.target.taxid}; not inside it (by NCBI Taxonomy): "
                + ", ".join(map(str, wrong))
                + ". An ancestor would empty the target search, and the near-neighbour search "
                "would then search the target itself."
            )
    if only_tiers is None or "exclusivity" in only_tiers:
        resolution = resolve_organism_list(cfg, Eutils(http, cfg.ncbi.eutils_url), cache, assay)
        excl_unresolved = len(resolution.unresolved)
        # The organism list may legitimately include the assay's own intended target (e.g. a
        # respiratory panel listing SARS-CoV-2 alongside the pathogens a SARS-CoV-2 assay is
        # checked against). Searching for it here would only ever find the assay's own perfect,
        # intended match -- not evidence of cross-reactivity -- so it is excluded from this tier's
        # own search; taxonomy/exclusivity.py still shows the organism-list row, flagged, rather
        # than silently dropping it.
        excl_taxids = [t for t in resolution.taxids if t != assay.target.taxid]
    # every tier's taxa against the target's lineage and against each other (tiers review
    # 2026-11-20, F2): refused when inside the target, NOT the target when an ancestor of it,
    # and a taxon in two tiers searched once
    taxa, moved = dedupe(assay_tier_taxa(assay, cfg.search.background_taxids, excl_taxids))
    names = (
        {r.taxid: r.name for r in resolution.resolutions if r.taxid is not None}
        if resolution is not None
        else {}
    )
    eutils = Eutils(http, cfg.ncbi.eutils_url)
    try:
        tier_taxa = check_tier_taxa(
            assay, taxa,
            lambda taxids: ancestors(
                eutils, cache, taxids, ttl_days=cfg.ncbi.taxonomy_cache_ttl_days
            ),
            names,
        )  # fmt: skip
        tier_taxa.notes[:0] = moved
        lineage_warning = ""
    except NcbiError as exc:
        # the exact duplicates are still removed; the lineage rules wait for the next run, and
        # the assessment's own lineage check still sets aside records of the target
        tier_taxa = TierTaxa(taxa=taxa, notes=list(moved))
        lineage_warning = (
            "The tier taxa could not be checked against the target's lineage (NCBI Taxonomy: "
            f"{exc}); an organism that contains the target is searched without NOT the target "
            "this time."
        )
    plan = plan_searches(
        assay, cfg, exclusivity_taxids=excl_taxids, exclusivity_unresolved=excl_unresolved,
        tier_taxa=tier_taxa,
    )  # fmt: skip
    if lineage_warning:
        plan.warnings.append(lineage_warning)
    if only_tiers is not None:  # validation runs restrict the plan; the cache keys stay the same
        plan.searches = [ps for ps in plan.searches if ps.tier in only_tiers]
    return plan, resolution


def run_remote_search(
    assay: Assay,
    cfg: Config,
    outdir: Path,
    *,
    confirm: Callable[[list[PlannedSearch], SearchPlan], bool],
    keep_tiers: set[str] | None = None,
    only_tiers: set[str] | None = None,
    on_plan: Callable[[SearchPlan], None] | None = None,
    allow_no_searches: bool = False,
) -> RemoteSearch:
    """Plan (resolving the exclusivity tier), ask for confirmation, execute, keep parsed results.

    ``on_plan`` is called once the real plan is known, before anything is sent, so a caller can
    show exactly what will be searched -- including the resolved exclusivity taxids -- rather than
    a plan built before resolution. ``confirm`` is called only when at least one search has to be
    submitted; searches that are cached or still resumable send nothing. Returning False from
    ``confirm`` aborts before anything is sent. ``allow_no_searches``: an empty plan is not an
    error (a full run still has its variant analysis; the specificity verdict then says that no
    off-target tier was searched).
    """
    creds = credentials_from_env()
    http = NcbiHttp(cfg.ncbi, creds)
    cache = Cache(cfg.ncbi.cache_dir)
    plan, resolution = _resolve_and_plan(assay, cfg, http, cache, only_tiers=only_tiers)
    if on_plan:
        on_plan(plan)
    if not plan.searches and not allow_no_searches:
        raise InputError(NOTHING_TO_SEARCH)
    search_dir, digest = search_dir_for(assay, cfg, outdir)
    store = JobStore(search_dir / "jobs.json")
    runner = BlastRunner(
        BlastApi(http, cfg.ncbi.blast_url), cache, store, cfg.ncbi, cfg.search.result_format
    )
    fresh = [
        ps
        for ps in plan.searches
        if runner.needs_submission(
            store.jobs.get(ps.key)
            or Job(
                key=ps.key, tier=ps.tier, label=ps.label, taxids=ps.taxids,
                entrez_query=ps.entrez_query, params={}, query_labels=ps.labels,
            )
        )
    ]  # fmt: skip
    if fresh and not confirm(fresh, plan):
        raise Aborted("Aborted. Nothing was sent to NCBI (use --yes to skip this question).")
    parsed: dict[str, ParsedSearch] = {}
    outcome = run_search(
        plan, cfg, runner, store, search_dir, inputs_hash=digest, keep=parsed, keep_tiers=keep_tiers
    )
    return RemoteSearch(plan, outcome, parsed, search_dir, digest, http, cache, resolution)
