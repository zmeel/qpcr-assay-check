"""The assessment's view of one stored genome: its copies of the locus as regions.

The genomes themselves are stored per locus in :mod:`.genomestore` (every candidate with its
evidence); :func:`.exhaustive.as_items` turns each record into a :class:`StoredAssembly` with
the copy rule applied, and the assessment reads only these two models.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StoredLocus(BaseModel):
    """One copy of the locus: the region around it (fragment sense) and where it lies."""

    contig: str
    strand: Literal["+", "-"]
    start: int  # 1-based, on the contig's forward strand, of the region
    end: int  # inclusive
    region: str
    offset: int  # index in ``region`` where the fragment starts (negative when cut before it)
    n_seeds: int  # fragment bases anchored by exact blocks
    truncated: bool  # a contig end falls inside the fragment
    on_plasmid: bool | None = None
    ref: int = Field(default=0, description="index of the reference fragment that found it")
    identity: float | None = Field(
        default=None, description="identity to its reference fragment over the part it covers"
    )
    anchors: list[tuple[int, int, int]] | None = Field(
        default=None,
        description="(fragment position, region index, length) of each exact block; oligo "
        "sites are placed through the nearest one",
    )
    fallback: bool = Field(default=False, description="found by the fallback search")

    def offset_at(self, pos: int) -> int:
        """Region index minus fragment position at fragment position ``pos``, through the
        nearest exact block (the single offset when there are none)."""
        if not self.anchors:
            return self.offset
        f, r, _n = min(self.anchors, key=lambda a: 0 if a[0] <= pos < a[0] + a[2]
                       else min(abs(pos - a[0]), abs(pos - a[0] - a[2])))  # fmt: skip
        return r - f


class StoredAssembly(BaseModel):
    """One genome (assembly or Nucleotide record) as the assessment reads it."""

    accession: str
    release_date: str
    organism: str = ""
    taxid: int | None = None
    assembly_level: str = ""
    status: Literal["found", "not_found", "masked"]
    n_loci: int = 0
    loci: list[StoredLocus] = Field(default_factory=list)
    n_contigs: int | None = None
    plasmid_contigs: int | None = None
    plasmid_examples: list[str] = Field(default_factory=list)
    found_by: Literal["scan", "blast", "direct_scan"] | None = None
    collection_date: str | None = Field(
        default=None,
        description="as the submitter recorded it; '' none given; None not read yet",
    )
    direct_checked: bool | None = Field(
        default=None,
        description="Nucleotide records: False when BLAST found nothing and the record was too "
        "long to fetch and scan whole",
    )

    @property
    def year(self) -> int:
        return int(self.release_date[:4])
