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
from .datasets import AssemblyRecord
from .locate import Locus

log = logging.getLogger(__name__)

MAX_LOCI_KEPT = 5


class StoredLocus(BaseModel):
    contig: str
    strand: Literal["+", "-"]
    start: int
    end: int
    region: str
    offset: int
    n_seeds: int
    truncated: bool


class StoredAssembly(BaseModel):
    """What one assembly contributed: its metadata and every copy of the amplicon region."""

    accession: str
    release_date: str
    organism: str = ""
    taxid: int | None = None
    assembly_level: str = ""
    status: Literal["found", "not_found"]
    n_loci: int = 0
    loci: list[StoredLocus] = Field(default_factory=list)

    @property
    def year(self) -> int:
        return int(self.release_date[:4])


def store_path(cache_dir: Path, taxon: int | str, amplicon: str, flank: int) -> Path:
    key = content_key({"amplicon": amplicon.upper(), "flank": flank})[:16]
    return Path(cache_dir) / "variants" / f"{taxon}-{key}.jsonl"


class RegionStore:
    """Loads existing lines on open; :meth:`add` appends and flushes one line per assembly."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.items: dict[str, StoredAssembly] = {}
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

    def add(self, rec: AssemblyRecord, loci: list[Locus]) -> StoredAssembly:
        item = StoredAssembly(
            accession=rec.accession,
            release_date=rec.release_date,
            organism=rec.organism,
            taxid=rec.taxid,
            assembly_level=rec.assembly_level,
            status="found" if loci else "not_found",
            n_loci=len(loci),
            loci=[StoredLocus(**_locus(lc)) for lc in loci[:MAX_LOCI_KEPT]],
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(item.model_dump_json() + "\n")
        self.items[item.accession] = item
        return item


def _locus(lc: Locus) -> dict[str, Any]:
    return json.loads(json.dumps(asdict(lc)))
