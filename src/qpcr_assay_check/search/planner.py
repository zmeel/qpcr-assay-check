"""Plan the remote searches: tiers, taxon restriction, batching, and the search budget."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import Config
from ..models import Assay
from ..ncbi import blast
from ..oligo import iupac

MAX_BATCH_BASES = 1000  # NCBI: merge short queries into one search of up to 1,000 bases


@dataclass
class PlannedSearch:
    """One BLAST submission: a batch of query oligos restricted to one group of taxa."""

    tier: str
    title: str
    taxids: list[int]
    entrez_query: str | None
    chunk: int
    n_chunks: int
    batch: int
    n_batches: int
    labels: list[str]
    fasta: str
    params: dict[str, str]
    key: str

    @property
    def label(self) -> str:
        """Short human-readable identifier."""
        extra = f" chunk {self.chunk}/{self.n_chunks}" if self.n_chunks > 1 else ""
        extra += f" batch {self.batch}/{self.n_batches}" if self.n_batches > 1 else ""
        return f"{self.tier}{extra}"


@dataclass
class SearchPlan:
    """Everything that would be sent to NCBI, before anything is sent."""

    queries: dict[str, str]
    searches: list[PlannedSearch]
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def is_offpeak(now: datetime) -> bool:
    """NCBI's off-peak window: weekends, or 21:00-05:00 US Eastern time on weekdays."""
    eastern = now.astimezone(ZoneInfo("America/New_York"))
    return eastern.weekday() >= 5 or eastern.hour >= 21 or eastern.hour < 5


def build_queries(assay: Assay, cfg: Config) -> dict[str, str]:
    """Query oligos keyed by FASTA identifier; degenerate oligos become one query per variant."""
    queries: dict[str, str] = {}
    for role, seq in assay.oligos.items():
        variants = iupac.expand(seq, cfg.oligo.max_degenerate_expansions)
        if len(variants) == 1:
            queries[role] = variants[0]
        else:
            for i, v in enumerate(variants, start=1):
                queries[f"{role}_v{i}"] = v
    return queries


def split_batches(
    queries: dict[str, str], max_bases: int = MAX_BATCH_BASES
) -> list[dict[str, str]]:
    """Greedy split so each submission stays within the recommended query size."""
    batches: list[dict[str, str]] = [{}]
    used = 0
    for label, seq in queries.items():
        if batches[-1] and used + len(seq) > max_bases:
            batches.append({})
            used = 0
        batches[-1][label] = seq
        used += len(seq)
    return batches


def _chunks(items: list[int], size: int) -> list[list[int]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def plan_searches(assay: Assay, cfg: Config) -> SearchPlan:
    """Tiered, taxon-restricted searches: target, near neighbours, background."""
    queries = build_queries(assay, cfg)
    batches = split_batches(queries)
    tiers: list[tuple[str, str, list[int]]] = []
    plan = SearchPlan(queries=queries, searches=[])

    if assay.target.taxid is not None:
        tiers.append(("target", "Intended target", [assay.target.taxid]))
    else:
        plan.notes.append(
            "The target tier was skipped: the assay has no taxonomy ID. "
            "From v0.4.0 it is derived from the reference accession."
        )
    near = sorted(set(assay.near_neighbour_taxids) | set(assay.exclusion_taxids))
    if near:
        tiers.append(("near_neighbours", "Near neighbours and exclusion taxa", near))
    if cfg.search.background_taxids:
        tiers.append(("background", "Background taxa", sorted(set(cfg.search.background_taxids))))
    plan.notes.append(
        "The organism-list tier (clinical organisms) arrives in v0.4.0 with taxonomy resolution."
    )

    size = cfg.search.max_taxids_per_search
    for tier, title, taxids in tiers:
        groups = _chunks(taxids, size)
        for ci, group in enumerate(groups, start=1):
            entrez = blast.build_entrez_query(group)
            for bi, batch in enumerate(batches, start=1):
                fasta = blast.build_query_fasta(batch)
                params = blast.build_put_params(cfg, fasta, entrez)
                plan.searches.append(
                    PlannedSearch(
                        tier=tier,
                        title=title,
                        taxids=group,
                        entrez_query=entrez,
                        chunk=ci,
                        n_chunks=len(groups),
                        batch=bi,
                        n_batches=len(batches),
                        labels=list(batch),
                        fasta=fasta,
                        params=params,
                        key=blast.request_key(params),
                    )
                )

    if len(plan.searches) > cfg.search.max_searches_warn:
        plan.warnings.append(
            f"{len(plan.searches)} searches are planned; NCBI asks for more than "
            f"{cfg.search.max_searches_warn} searches to be run at weekends or between 21:00 and "
            "05:00 US Eastern time (roughly 03:00-11:00 in the Netherlands)."
        )
    return plan
