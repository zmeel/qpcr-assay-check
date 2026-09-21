"""Run a search plan, assess the results, and write ``hits.tsv`` and ``search.json``."""

from __future__ import annotations

import csv
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .. import __version__
from ..config import Config
from ..ncbi.jobs import Job, JobStore
from ..ncbi.parser import ParsedSearch, QueryResult, parse_blast_json
from ..ncbi.runner import BlastRunner
from .assess import QuerySaturation, RestrictionSummary, assess_saturation, summarise_restriction
from .planner import PlannedSearch, SearchPlan

log = logging.getLogger(__name__)

HITS_COLUMNS = [
    "tier", "query", "accession", "taxid", "organism", "title", "n_merged", "hsp",
    "identical_bases", "align_len", "gaps", "bit_score", "evalue", "query_from", "query_to",
    "hit_from", "hit_to", "query_strand", "hit_strand", "merged_taxids",
]  # fmt: skip


class SearchRecord(BaseModel):
    """Outcome of one submitted search."""

    tier: str
    label: str
    taxids: list[int]
    entrez_query: str | None
    key: str
    rid: str | None
    state: str
    blast_version: str | None
    database: str | None
    n_hits: dict[str, int]
    perfect_full_length: dict[str, int] = Field(default_factory=dict)
    saturation: list[QuerySaturation]
    restriction: RestrictionSummary | None


class SearchOutcome(BaseModel):
    """Everything ``search.json`` records."""

    schema_version: int = 1
    tool: dict[str, str]
    generated_at: str
    inputs_hash: str
    oligos: dict[str, str]
    parameters: dict[str, Any]
    searches: list[SearchRecord]
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def saturated(self) -> bool:
        """True if a hit list is saturated in any tier except the intended target.

        A well-sequenced target (SARS-CoV-2 has more than 9 million records) always fills the hit
        list with perfect matches; that is expected and says nothing about specificity. Inclusivity
        is assessed with time windows instead.
        """
        return any(s.saturated for r in self.searches if r.tier != "target" for s in r.saturation)


def _perfect(results: list[QueryResult], queries: dict[str, str]) -> dict[str, int]:
    """Hits with an alignment covering the whole oligo without a single mismatch or gap."""
    out: dict[str, int] = {}
    for q in results:
        n = len(queries[q.label])
        out[q.label] = sum(
            any(h.identity == n and h.align_len == n and h.gaps == 0 for h in hit.hsps)
            for hit in q.hits
        )
    return out


def _rows(tier: str, parsed: ParsedSearch) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for label, q in parsed.queries.items():
        for hit in q.hits:
            d = hit.descriptions[0] if hit.descriptions else None
            merged = sorted({x.taxid for x in hit.descriptions if x.taxid is not None})
            for hsp in hit.hsps:
                rows.append(
                    [
                        tier, label,
                        (d.accession_version if d else "") or "",
                        (d.taxid if d and d.taxid is not None else ""),
                        (d.sciname if d else "") or "",
                        (d.title if d else "")[:120],
                        len(hit.descriptions), hsp.num, hsp.identity, hsp.align_len, hsp.gaps,
                        hsp.bit_score, hsp.evalue, hsp.query_from, hsp.query_to, hsp.hit_from,
                        hsp.hit_to, hsp.query_strand, hsp.hit_strand,
                        ";".join(str(t) for t in merged[:20]),
                    ]
                )  # fmt: skip
    return rows


def run_search(
    plan: SearchPlan,
    cfg: Config,
    runner: BlastRunner,
    store: JobStore,
    out_dir: Path,
    *,
    inputs_hash: str,
    now: datetime | None = None,
    keep: dict[str, ParsedSearch] | None = None,
    keep_tiers: set[str] | None = None,
) -> SearchOutcome:
    """Execute every planned search (resuming where possible) and write the outputs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[SearchRecord] = []
    all_rows: list[list[Any]] = []
    versions: set[str] = set()

    for ps in plan.searches:
        job = store.jobs.get(ps.key) or _new_job(ps)
        store.upsert(job)
        raw = runner.run(job, ps.fasta, ps.params)
        parsed = parse_blast_json(raw, ps.labels)
        if parsed.version:
            versions.add(parsed.version)
        if keep is not None and (keep_tiers is None or ps.tier in keep_tiers):
            keep[ps.key] = parsed
        results: list[QueryResult] = list(parsed.queries.values())
        records.append(
            SearchRecord(
                tier=ps.tier,
                label=ps.label,
                taxids=ps.taxids,
                entrez_query=ps.entrez_query,
                key=ps.key,
                rid=job.rid,
                state=job.state,
                blast_version=parsed.version,
                database=parsed.database,
                n_hits={q.label: len(q.hits) for q in results},
                perfect_full_length=_perfect(results, plan.queries),
                saturation=[
                    assess_saturation(
                        q, cfg.search.hitlist_size, cfg.search.relevance.min_identical_bases
                    )
                    for q in results
                ],
                restriction=summarise_restriction(results, ps.taxids) if ps.taxids else None,
            )
        )
        all_rows.extend(_rows(ps.tier, parsed))

    with (out_dir / "hits.tsv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow(HITS_COLUMNS)
        writer.writerows(all_rows)

    warnings = list(plan.warnings)
    notes = list(plan.notes)
    for r in records:
        for s in r.saturation:
            if s.saturated and r.tier == "target":
                notes.append(
                    f"[{r.label}] {s.label}: hit list full of relevant hits. Expected for a "
                    "well-sequenced target; inclusivity uses time windows instead."
                )
            elif s.saturated:
                warnings.append(f"[{r.label}] {s.label}: {s.note}")
        if r.restriction and not r.restriction.verifiable and r.n_hits and sum(r.n_hits.values()):
            warnings.append(
                f"[{r.label}] hits carry no taxonomy information, so the taxon restriction could "
                "not be checked."
            )

    stamp = (now or datetime.now(UTC)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    outcome = SearchOutcome(
        tool={"name": "qpcr-assay-check", "version": __version__},
        generated_at=stamp,
        inputs_hash=inputs_hash,
        oligos=plan.queries,
        parameters={
            "search": cfg.search.model_dump(mode="json"),
            "blast_versions": sorted(versions),
        },
        searches=records,
        notes=notes,
        warnings=warnings,
    )
    (out_dir / "search.json").write_text(outcome.model_dump_json(indent=2), encoding="utf-8")
    return outcome


def _new_job(ps: PlannedSearch) -> Job:
    return Job(
        key=ps.key,
        tier=ps.tier,
        label=ps.label,
        taxids=ps.taxids,
        entrez_query=ps.entrez_query,
        params={k: v for k, v in ps.params.items() if k != "QUERY"},
        query_labels=ps.labels,
    )


def load_outcome(path: Path) -> SearchOutcome:
    """Read a previously written ``search.json``."""
    return SearchOutcome.model_validate(json.loads(path.read_text(encoding="utf-8")))
