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
from ..ncbi.http import NcbiHttp
from ..ncbi.jobs import Job, JobStore
from ..ncbi.parser import ParsedSearch
from ..ncbi.runner import BlastRunner
from ..ncbi.settings import credentials_from_env
from ..pipeline import inputs_hash
from .orchestrate import SearchOutcome, run_search
from .planner import PlannedSearch, SearchPlan, plan_searches


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


def search_dir_for(assay: Assay, cfg: Config, outdir: Path) -> tuple[Path, str]:
    """Directory holding the resumable state of this assay's searches (keyed by inputs hash)."""
    digest = inputs_hash(assay, cfg)
    return outdir / assay.slug / f"search-{digest[:8]}", digest


def run_remote_search(
    assay: Assay,
    cfg: Config,
    outdir: Path,
    *,
    confirm: Callable[[list[PlannedSearch], SearchPlan], bool],
    keep_tiers: set[str] | None = None,
    only_tiers: set[str] | None = None,
) -> RemoteSearch:
    """Plan, ask for confirmation if anything must be sent, execute, and keep parsed results.

    ``confirm`` is called only when at least one search has to be submitted; searches that are
    cached or still resumable send nothing. Returning False aborts before anything is sent.
    """
    plan = plan_searches(assay, cfg)
    if only_tiers is not None:  # validation runs restrict the plan; the cache keys stay the same
        plan.searches = [ps for ps in plan.searches if ps.tier in only_tiers]
    search_dir, digest = search_dir_for(assay, cfg, outdir)
    creds = credentials_from_env()
    store = JobStore(search_dir / "jobs.json")
    http = NcbiHttp(cfg.ncbi, creds)
    cache = Cache(cfg.ncbi.cache_dir)
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
    return RemoteSearch(plan, outcome, parsed, search_dir, digest, http, cache)
