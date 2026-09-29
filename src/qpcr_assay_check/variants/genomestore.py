"""Store v2: every candidate copy of one locus per genome, with its evidence (overhaul step 4).

One JSON-lines file per locus definition. Its first line is a header with the schema version
and the key: the locus references (fragments and context), the scan settings, the taxon and
the source. A file whose header is missing or differs is set aside (renamed ``.old``) and every
genome is scanned again: no migration code, no rescans (user, 2026-09-29: "deleting the cache
and starting over should always be an option"). After the header, one line per genome; the
last line of an accession wins.

What is kept per genome lets every rule change without a new scan: all candidates found by the
chain locator (not only those counted as copies), each with its anchors, anchored fragment and
flank bases, identity, signed coordinates, the N inside and next to it, the sequence around it
and the molecule it sits on; per genome its sequences, length, N and gaps (N-runs of
``GAP_MIN_N`` or more). Only these regions are kept, never the genome (project rule).
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .. import __version__
from ..ncbi.cache import content_key
from .chain import Candidate, Reference, locate
from .datasets import AssemblyRecord, SequenceRole, is_plasmid

log = logging.getLogger(__name__)

SCHEMA = 2
GAP_MIN_N = 10  # an N-run of at least this length counts as an assembly gap
UNAVAILABLE_AFTER = 2  # failed download attempts before a genome counts as unavailable
_GAP_RE = re.compile(f"N{{{GAP_MIN_N},}}")


class ScanSettings(BaseModel):
    """What decides which candidates a scan finds: part of the store key."""

    k: int = 16
    step: int = 2
    max_indel: int = 150
    flank: int = 50


class StoredCopy(BaseModel):
    """One candidate copy (a :class:`chain.Candidate`) and the molecule it sits on."""

    contig: str
    strand: Literal["+", "-"]
    contig_length: int
    ref: int
    start: int
    end: int
    fragment_length: int
    anchors: list[tuple[int, int, int]]
    anchored: int
    context_left: int
    context_right: int
    identity: float | None
    n_inside: int
    n_left: int
    n_right: int
    region: str
    region_start: int
    molecule: str | None = Field(
        default=None,
        description="Chromosome, Plasmid, ... (Datasets sequence report, else 'Plasmid' when "
        "the FASTA description names one); None: not known",
    )

    @classmethod
    def of(cls, c: Candidate, molecule: str | None) -> StoredCopy:
        fields = {name: getattr(c, name) for name in cls.model_fields if name != "molecule"}
        return cls(**fields, molecule=molecule)

    def candidate(self) -> Candidate:
        """Back to a chain.Candidate (for is_copy, place and the other helpers)."""
        data = self.model_dump(exclude={"molecule"})
        data["anchors"] = tuple(tuple(a) for a in self.anchors)
        return Candidate(**data)


class GenomeRecord(BaseModel):
    """What one genome contributed to one locus."""

    accession: str
    release_date: str
    organism: str = ""
    taxid: int | None = None
    assembly_level: str = ""
    n_sequences: int
    total_length: int
    total_n: int
    gaps: int = Field(description=f"N-runs of {GAP_MIN_N} or more")
    copies: list[StoredCopy] = Field(default_factory=list, description="every candidate")

    @property
    def year(self) -> int:
        return int(self.release_date[:4])


def store_key(
    references: Sequence[Reference], settings: ScanSettings, *, taxon: int | str, source: str,
    excluded: Sequence[int] = (),
) -> dict[str, Any]:  # fmt: skip
    """The store key: a change in any of these means a new scan of every genome."""
    return {
        "schema": SCHEMA,
        "references": [[r.fragment.upper(), r.left.upper(), r.right.upper()] for r in references],
        "scan": settings.model_dump(),
        "taxon": str(taxon),
        "source": source,
        "excluded": sorted(excluded),
    }


def store_file(cache_dir: Path, key: dict[str, Any]) -> Path:
    """``<cache>/genomes/<taxon>-<key hash>.jsonl``."""
    return Path(cache_dir) / "genomes" / f"{key['taxon']}-{content_key(key)[:16]}.jsonl"


class GenomeStore:
    """The records of one locus key; opening a file with another key sets it aside."""

    def __init__(self, path: Path, key: dict[str, Any]) -> None:
        self.path = Path(path)
        self.key = key
        self.items: dict[str, GenomeRecord] = {}
        self.failures_path = self.path.with_name(self.path.name + ".failures.json")
        self.failures: dict[str, dict[str, Any]] = {}
        if self.path.exists() and not self._load():
            old = self.path.with_suffix(".old")
            self.path.replace(old)
            if self.failures_path.exists():
                self.failures_path.unlink()
            log.warning(
                "The stored regions in %s were made with another locus definition or method; "
                "they are set aside as %s and every genome is scanned again.", self.path, old,
            )  # fmt: skip
        if not self.path.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)
            header = {"schema": SCHEMA, "tool_version": __version__, "key": key}
            self.path.write_text(json.dumps(header) + "\n", encoding="utf-8")
        if self.failures_path.exists():
            try:
                self.failures = json.loads(self.failures_path.read_text("utf-8"))
            except ValueError:
                log.warning("Ignoring unreadable %s", self.failures_path)

    def _load(self) -> bool:
        """Read the records; False when the header is missing or its key differs."""
        lines = self.path.read_text(encoding="utf-8").splitlines()
        try:
            header = json.loads(lines[0]) if lines else {}
        except ValueError:
            return False
        if header.get("schema") != SCHEMA or header.get("key") != self.key:
            return False
        for n, line in enumerate(lines[1:], 2):
            if not line.strip():
                continue
            try:
                rec = GenomeRecord.model_validate_json(line)
            except ValueError:
                log.warning("Skipping unreadable line %d of %s", n, self.path)
                continue
            self.items[rec.accession] = rec
        return True

    def __contains__(self, accession: str) -> bool:
        return accession in self.items

    def add(self, rec: GenomeRecord) -> GenomeRecord:
        """Append one genome's line (the last line of an accession wins on load)."""
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(rec.model_dump_json() + "\n")
        self.items[rec.accession] = rec
        self.failures.pop(rec.accession, None)
        return rec

    def record_failure(self, accession: str, reason: str) -> None:
        """Count a failed download, with its reason (tried again on the next run)."""
        entry = self.failures.setdefault(accession, {"count": 0, "reason": ""})
        entry["count"] += 1
        entry["reason"] = reason[:200]
        self.failures_path.write_text(json.dumps(self.failures, indent=0), encoding="utf-8")

    def unavailable(self, accession: str) -> bool:
        """Not stored, and its download failed on at least ``UNAVAILABLE_AFTER`` runs."""
        entry = self.failures.get(accession)
        return accession not in self.items and bool(entry) and entry["count"] >= UNAVAILABLE_AFTER


def sequence_stats(seqs: dict[str, str]) -> tuple[int, int, int, int]:
    """``(sequences, total length, N, gaps)`` of a genome's FASTA records."""
    upper = [s.upper() for s in seqs.values()]
    return (
        len(upper),
        sum(map(len, upper)),
        sum(s.count("N") for s in upper),
        sum(len(_GAP_RE.findall(s)) for s in upper),
    )


def scan_genome(
    rec: AssemblyRecord,
    records: dict[str, tuple[str, str]],
    references: Sequence[Reference],
    settings: ScanSettings,
    roles: dict[str, SequenceRole] | None = None,
) -> GenomeRecord:
    """Locate every candidate in one genome (``records``: id -> (FASTA description, sequence))
    and keep it with the genome's statistics. ``roles``: the assembly's sequence report, when
    fetched; otherwise a FASTA description naming a plasmid marks the molecule."""
    seqs = {name: seq for name, (_d, seq) in records.items()}
    found = locate(seqs, references, k=settings.k, step=settings.step,
                   max_indel=settings.max_indel, flank=settings.flank)  # fmt: skip
    n, total, total_n, gaps = sequence_stats(seqs)
    return GenomeRecord(
        accession=rec.accession, release_date=rec.release_date, organism=rec.organism,
        taxid=rec.taxid, assembly_level=rec.assembly_level, n_sequences=n, total_length=total,
        total_n=total_n, gaps=gaps,
        copies=[StoredCopy.of(c, _molecule(c.contig, records, roles)) for c in found],
    )  # fmt: skip


def _molecule(
    contig: str, records: dict[str, tuple[str, str]], roles: dict[str, SequenceRole] | None
) -> str | None:
    if roles and contig in roles:
        return roles[contig].molecule or None
    return "Plasmid" if is_plasmid(records.get(contig, ("", ""))[0]) else None
