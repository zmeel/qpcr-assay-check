"""Result models of the exhaustive variant analysis (serialised into results.json)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class YearCoverage(BaseModel):
    year: int
    listed: int = Field(description="assemblies NCBI Datasets lists for this release year")
    assessed: int = Field(description="of those, assessed so far (this run and earlier runs)")


class OligoCoverageRow(BaseModel):
    """How many genomes one oligo covers, on each genome's best-binding copy."""

    role: str
    name: str
    reporter: str | None = None
    covered: int = Field(description="genomes where this oligo binds well (detectable)")
    only: int = Field(description="of those, genomes no other oligo of the role covers")


class ChannelCoverageRow(BaseModel):
    """Probes sharing a reporter dye form one detection channel."""

    reporter: str
    probes: list[str]
    covered: int


class CopyCoverage(BaseModel):
    """Every stored copy of the region, every alternative oligo: what the assay can detect.

    A site is detectable when it has at most 1 mismatch, no gap and no mismatch in the last 5
    nucleotides (the inclusivity criterion); a copy is detectable when all its roles are. Each
    genome is judged by its best-binding copy.
    """

    genomes: int = Field(description="genomes with at least one complete copy assessed")
    multi_copy: int = Field(description="genomes with more than one complete copy assessed")
    max_copies: int = 0
    copies_capped: int = Field(
        default=0,
        description="genomes with more copies than were stored (older stores kept at most 5)",
    )
    best_copy_not_first: int = Field(
        default=0,
        description="genomes whose best-binding copy is not the one found most confidently "
        "(before v1.3.0 the tables used that first copy)",
    )
    with_detectable_copy: int = 0
    escapes: int = Field(default=0, description="genomes without any detectable copy")
    escape_examples: list[str] = Field(default_factory=list)
    oligos: list[OligoCoverageRow] = Field(default_factory=list)
    role_none: dict[str, int] = Field(
        default_factory=dict, description="per role: genomes that none of its oligos covers"
    )
    role_none_examples: dict[str, list[str]] = Field(default_factory=dict)
    channels: list[ChannelCoverageRow] = Field(default_factory=list)
    any_channel: int = 0
    all_channels: int = 0
    probe_channels: str = Field(
        default="any", description="setting: which channels a genome needs to count as detected"
    )
    homopolymer_bulges_detectable: bool = Field(
        default=False,
        description="setting: whether a site that differs only by a single-base run length "
        "counts as detectable (the counts above use this rule)",
    )
    with_detectable_copy_strict: int = Field(
        default=0, description="genomes with a detectable copy when bulges do not count"
    )
    with_detectable_copy_bulges: int = Field(
        default=0, description="genomes with a detectable copy when bulges count"
    )


class ExhaustiveCoverage(BaseModel):
    """How much of the target's assembly collection the variant analysis covers."""

    source: str = "datasets"
    taxon: int
    amplicon_length: int
    amplicon_source: str
    filters: dict[str, bool | str]
    listed_total: int
    assessed_total: int
    processed_this_run: int
    download_failed_this_run: int
    budget_per_run: int
    found: int
    not_found: int
    contig_break: int = Field(description="region cut by a contig end (draft assemblies)")
    multi_copy: int = Field(description="assemblies with more than one copy of the region")
    years: list[YearCoverage] = Field(default_factory=list)
    listed_at: str
    not_found_examples: list[str] = Field(default_factory=list)
    target_on_plasmid: bool | None = Field(
        default=None,
        description="most copies of the region that were found lie on sequences described as a "
        "plasmid (None: nothing found, or not recorded)",
    )
    not_found_without_plasmid: int = Field(
        default=0, description="region not found, and the assembly contains no plasmid sequence"
    )
    not_found_with_plasmid: int = Field(
        default=0,
        description="region not found although the assembly contains plasmid sequence(s): for a "
        "plasmid-borne target, a possible deletion (as in the Swedish nvCT variant)",
    )
    not_found_with_plasmid_examples: list[str] = Field(default_factory=list)
    masked: int = Field(
        default=0,
        description="region present but hidden by N (low-coverage sequencing): the whole region, "
        "or an oligo site inside it; not assessed, since an N is neither a match nor a variant",
    )
    masked_examples: list[str] = Field(default_factory=list)
    found_by_direct_scan: int = Field(
        default=0,
        description="Nucleotide records: no BLAST hit, region found by fetching the record (for "
        "example, too new for the BLAST database)",
    )
    not_checked_directly: int = Field(
        default=0,
        description="Nucleotide records without a BLAST hit that were not fetched and scanned "
        "(longer than direct_scan_max_length, or the fetch failed)",
    )
    plasmid_info_recorded: bool = Field(
        default=False,
        description="plasmid sequences were counted for at least one assembly (so the split of "
        "'region not found' can be shown)",
    )
    plasmid_header_examples: list[str] = Field(
        default_factory=list,
        description="FASTA descriptions recognised as plasmids, shown so the rule can be checked",
    )

    copies: CopyCoverage | None = Field(
        default=None, description="copies, coverage per oligo and channel, escape list (v1.3.0)"
    )

    @property
    def complete(self) -> bool:
        return self.assessed_total >= self.listed_total
