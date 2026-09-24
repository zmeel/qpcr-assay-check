"""Append-only store of the region extracted from each assembly (resumable across runs).

One JSON line per processed assembly, in a file keyed by the target taxon and the reference
amplicon (plus the flank setting), so a different assay on the same target never reuses another
amplicon's regions. Only the amplicon region and its flanks are kept, never the genome (see the
project rules). An interrupted run loses at most the batch it was working on.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..ncbi.cache import content_key
from .datasets import AssemblyRecord, is_plasmid
from .locate import Locus

log = logging.getLogger(__name__)

MAX_LOCI_KEPT = 20  # multi-copy targets (v1.3.0; stores written before kept 5)


class StoredLocus(BaseModel):
    contig: str
    strand: Literal["+", "-"]
    start: int
    end: int
    region: str
    offset: int
    n_seeds: int
    truncated: bool
    on_plasmid: bool | None = None
    ref: int = Field(default=0, description="index of the reference amplicon that found it")


class StoredAssembly(BaseModel):
    """What one assembly contributed: its metadata and every copy of the amplicon region."""

    accession: str
    release_date: str
    organism: str = ""
    taxid: int | None = None
    assembly_level: str = ""
    status: Literal["found", "not_found", "masked"]
    n_loci: int = 0
    loci: list[StoredLocus] = Field(default_factory=list)
    n_contigs: int | None = None
    plasmid_contigs: int | None = Field(
        default=None,
        description="sequences whose FASTA description names a plasmid (None: not recorded, "
        "stored before v1.1.0's plasmid check)",
    )
    plasmid_examples: list[str] = Field(default_factory=list)
    found_by: Literal["scan", "blast", "direct_scan"] | None = Field(
        default=None,
        description="scan: genome scanned (assembly source); blast: a BLAST hit; direct_scan: "
        "no BLAST hit, found by fetching the record itself (e.g. not yet in the BLAST database)",
    )
    direct_checked: bool | None = Field(
        default=None,
        description="Nucleotide records only: a record without a BLAST hit was fetched and "
        "scanned directly before being called 'not found'",
    )
    refs_checked: int | None = Field(
        default=None,
        description="'not found' only: how many reference amplicons were tried (None: only the "
        "first, stored before v1.3.0)",
    )
    context_checked: bool | None = Field(
        default=None,
        description="'not found' only: whether the reference sequence around the amplicon was "
        "searched for a region wholly hidden by N (None: stored before v1.1.1)",
    )

    @property
    def copies_capped(self) -> bool:
        """Found, with fewer copies stored than kept now (stores before v1.3.0 kept 5)."""
        return self.status == "found" and len(self.loci) < min(self.n_loci, MAX_LOCI_KEPT)

    @property
    def needs_rescan(self) -> bool:
        """Stored before a check this version makes: scan it again (once)."""
        if self.plasmid_contigs is None or self.copies_capped:
            return True
        if self.status != "not_found" or self.direct_checked is False:
            return False  # a record too long to fetch (False) is not retried every run
        # 'not found' Nucleotide records stored before the direct scan existed, and any 'not
        # found' stored before the check for a region wholly hidden by N (v1.1.1)
        return (
            self.assembly_level == "Nucleotide record" and self.direct_checked is None
        ) or self.context_checked is None

    @property
    def year(self) -> int:
        return int(self.release_date[:4])


def store_path(
    cache_dir: Path, taxon: int | str, amplicon: str, flank: int, source: str = "datasets"
) -> Path:
    payload: dict[str, object] = {"amplicon": amplicon.upper(), "flank": flank}
    if source != "datasets":  # the datasets key predates other sources: keep existing stores
        payload["source"] = source
    key = content_key(payload)[:16]
    suffix = "" if source == "datasets" else f"-{source}"
    return Path(cache_dir) / "variants" / f"{taxon}-{key}{suffix}.jsonl"


class RegionStore:
    """Loads existing lines on open; :meth:`add` appends and flushes one line per assembly."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.items: dict[str, StoredAssembly] = {}
        self.aliases: set[str] = set()  # ESearch UIDs already looked up in this run
        self.n_refs = 1  # reference amplicons of the assay; set by the caller
        if self.path.exists():
            for n, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    item = StoredAssembly.model_validate_json(line)
                except ValueError:
                    log.warning("Skipping unreadable line %d of %s", n, self.path)
                    continue
                self.items[item.accession] = item

    def __contains__(self, accession: str) -> bool:
        return accession in self.items

    def done(self, accession: str) -> bool:
        """Stored and complete: nothing left to download for this assembly."""
        item = self.items.get(accession)
        if item is None or item.needs_rescan:
            return False
        # 'not found' with fewer reference amplicons than the assay now has: try the others once
        return not (item.status == "not_found" and self.n_refs > (item.refs_checked or 1))

    def add(
        self,
        rec: AssemblyRecord,
        loci: list[Locus],
        descriptions: dict[str, str] | None = None,
        *,
        found_by: str | None = None,
        direct_checked: bool | None = None,
        masked: list[Locus] | None = None,
        context_checked: bool | None = None,
        ref: int = 0,
        refs_checked: int | None = None,
    ) -> StoredAssembly:
        """Store one assembly/record. ``masked``: no clean copy, but the region is there under N."""
        item = StoredAssembly(
            accession=rec.accession,
            release_date=rec.release_date,
            organism=rec.organism,
            taxid=rec.taxid,
            assembly_level=rec.assembly_level,
            status="found" if loci else ("masked" if masked else "not_found"),
            n_loci=len(loci) if loci else len(masked or []),
            loci=[
                StoredLocus(**_locus(lc), on_plasmid=_plasmid(descriptions, lc.contig), ref=ref)
                for lc in (loci or masked or [])[:MAX_LOCI_KEPT]
            ],
            n_contigs=len(descriptions) if descriptions is not None else None,
            plasmid_contigs=(
                sum(1 for d in descriptions.values() if is_plasmid(d))
                if descriptions is not None
                else None
            ),
            plasmid_examples=[
                f"{name} {d}"[:160] for name, d in (descriptions or {}).items() if is_plasmid(d)
            ][:3],
            found_by=(found_by or "scan") if loci else None,  # type: ignore[arg-type]
            direct_checked=direct_checked,
            context_checked=context_checked if not loci and not masked else None,
            refs_checked=refs_checked if not loci and not masked else None,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(item.model_dump_json() + "\n")
        self.items[item.accession] = item
        return item


def _plasmid(descriptions: dict[str, str] | None, contig: str) -> bool | None:
    if descriptions is None or contig not in descriptions:
        return None
    return is_plasmid(descriptions[contig])


def _locus(lc: Locus) -> dict[str, Any]:
    return json.loads(json.dumps(asdict(lc)))
