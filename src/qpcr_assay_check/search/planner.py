"""Plan the remote searches: tiers, taxon restriction, batching, and the search budget."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import Config
from ..models import Assay
from ..ncbi import blast
from ..oligo import iupac
from ..taxonomy.organisms import load_organism_list, organism_list_source
from .tiers import TIER_PRIORITY, TierTaxa, assay_tier_taxa, dedupe

MAX_BATCH_BASES = 1000  # NCBI: merge short queries into one search of up to 1,000 bases


OUT_OF_SCOPE_TIER = "out_of_scope"  # target.taxa with role out_of_scope: information only


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
    """Everything that would be sent to NCBI, before anything is sent.

    ``exclusivity_pending``: an organism list is configured but not resolved to taxonomy IDs yet
    (``--dry-run`` plans without the network), so its tier is missing from ``searches`` although
    the real run will search it.
    """

    queries: dict[str, str]
    searches: list[PlannedSearch]
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exclusivity_pending: bool = False

    @property
    def searches_something(self) -> bool:
        """Whether the run will send at least one search."""
        return bool(self.searches) or self.exclusivity_pending


NOTHING_TO_SEARCH = (
    "Nothing to search: configure off-target taxa (search.background_taxids, an exclusivity "
    "list or near neighbours), or set search.target_tier: true."
)
NOTHING_TO_EVALUATE = (
    "Nothing to search and no target taxon for the variant analysis: give the assay a target "
    "taxid or configure off-target taxa."
)


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


HUMAN_TAXID = 9606


def _chunks(items: list[int], size: int) -> list[list[int]]:
    """``items`` in as few searches of at most ``size`` as possible, of balanced sizes (23 taxa
    in 12 + 11, not 20 + 3: a small tail search with few alignments set the whole tier's
    reporting floor, tiers review 2026-11-20, F6)."""
    if not items:
        return []
    n = -(-len(items) // size)
    base, extra = divmod(len(items), n)
    out, i = [], 0
    for k in range(n):
        step = base + (1 if k < extra else 0)
        out.append(items[i : i + step])
        i += step
    return out


def plan_searches(
    assay: Assay,
    cfg: Config,
    *,
    exclusivity_taxids: list[int] | None = None,
    exclusivity_unresolved: int = 0,
    tier_taxa: TierTaxa | None = None,
) -> SearchPlan:
    """Tiered, taxon-restricted searches: near neighbours, background, exclusivity, and the
    target itself only when ``search.target_tier`` is set.

    ``exclusivity_taxids`` are the clinical organism list's names already resolved to taxonomy
    IDs (see ``taxonomy.resolve``); resolution needs the network, so callers that must plan
    without it (``--dry-run``) pass ``None`` and this only notes how many names are configured.
    ``exclusivity_unresolved`` is the count of names that could not be resolved or were ambiguous,
    for the same note: never guessed, but the search plan (and the reader of it) should know they
    were skipped.

    ``tier_taxa``: the taxa per tier after the lineage checks against the target and between the
    tiers (``search.tiers.check_tier_taxa``, which needs NCBI Taxonomy). Without it (a dry run),
    a taxon listed in two tiers is still searched only once, in the more specific tier.
    """
    queries = build_queries(assay, cfg)
    batches = split_batches(queries)
    tiers: list[tuple[str, str, list[int]]] = []
    exclude = assay.target.excluded_taxids
    plan = SearchPlan(queries=queries, searches=[])

    if assay.target.taxid is None:
        plan.notes.append(
            "The target tier was skipped: the assay has no taxonomy ID. "
            "From v0.4.0 it is derived from the reference accession."
        )
    elif cfg.search.target_tier:
        tiers.append(("target", "Intended target", [assay.target.taxid]))
    else:
        # its hits fed the variant tables until the exhaustive analysis replaced them
        # (2026-09-29); since then only a positive-control line, at the cost of what was the
        # slowest search of a run for a large target (user decision 2026-10-23)
        plan.notes.append(
            "The intended target is not searched as a tier (search.target_tier: false): the "
            "variant analysis assesses every record of the target itself, which also shows "
            "whether each oligo matches it."
        )
    # taxa inside the target that the assay must not detect are near neighbours; taxa that are
    # only out of scope get their own tier, reported as information ("also detects"); a taxon in
    # two tiers is searched once, in the more specific one (tiers review 2026-11-20, F2)
    if tier_taxa is None:
        taxa, moved = dedupe(
            assay_tier_taxa(assay, cfg.search.background_taxids, exclusivity_taxids)
        )
        plan.notes.extend(moved)
        not_target: dict[int, list[int]] = {}
    else:
        taxa = {t: tier_taxa.taxa.get(t, []) for t in TIER_PRIORITY}
        not_target = tier_taxa.exclude
        plan.notes.extend(tier_taxa.notes)
    if taxa["near_neighbours"]:
        tiers.append(("near_neighbours", "Near neighbours and exclusion taxa",
                      taxa["near_neighbours"]))  # fmt: skip
    if taxa["out_of_scope"]:
        tiers.append(
            (OUT_OF_SCOPE_TIER, "Out of scope (reported, not judged)", taxa["out_of_scope"])
        )
    if taxa["background"]:
        tiers.append(("background", "Background taxa", taxa["background"]))
    if HUMAN_TAXID not in cfg.search.background_taxids:
        plan.warnings.append(
            f"Human (taxid {HUMAN_TAXID}) is not in 'search.background_taxids', so no human "
            "background search is planned; the report will state that off-target binding to "
            "human DNA was not evaluated."
        )
    if exclusivity_taxids:
        if taxa["exclusivity"]:
            tiers.append(("exclusivity", "Clinical organism list", taxa["exclusivity"]))
    elif exclusivity_taxids is None:
        source = organism_list_source(cfg, assay)
        n_names = len(load_organism_list(cfg, assay).names)
        plan.exclusivity_pending = n_names > 0
        if plan.exclusivity_pending and not tiers:
            plan.notes.append(
                "The exclusivity tier is the only search planned: if none of its names resolves "
                "to a taxonomy ID other than the target's, there is nothing to search and the run "
                "says so after resolving them."
            )
        which = (
            f"this assay's own 'exclusivity_organisms' list ({n_names} name(s))"
            if source == "assay"
            else f"the global organism list ({n_names} name(s), 'organisms.list_file' or the "
            "packaged starter list)"
        )
        plan.notes.append(
            f"The exclusivity tier will search {which}, resolved to taxonomy IDs when the search "
            "actually runs; not shown in --dry-run."
        )
    if cfg.variants.source == "blast_partitioned":
        plan.notes.append(
            "Variant analysis (variants.source: blast_partitioned): up to "
            f"{cfg.variants.blast_max_records_per_run} Nucleotide records of the target per run; "
            f"records up to {cfg.variants.direct_scan_max_length} bases are fetched and scanned "
            "directly, longer ones are found by sending the reference amplicon to NCBI BLAST, "
            f"once per list of up to {cfg.variants.blast_records_per_search} records."
        )
    if exclusivity_unresolved:
        plan.warnings.append(
            f"{exclusivity_unresolved} organism-list name(s) could not be resolved to exactly one "
            "taxonomy ID and were left out of the exclusivity tier (see the taxonomy resolution "
            "report); review and fix them in the organism list rather than relying on this search "
            "to cover them."
        )

    size = cfg.search.max_taxids_per_search
    for tier, title, taxids in tiers:
        groups = _chunks(taxids, size)
        for ci, group in enumerate(groups, start=1):
            if tier == "target":
                left_out = exclude
            else:
                left_out = sorted({x for t in group for x in not_target.get(t, [])})
            entrez = blast.build_entrez_query(group, left_out or None)
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
