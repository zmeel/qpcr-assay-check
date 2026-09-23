"""Result models of the exhaustive variant analysis (serialised into results.json)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class YearCoverage(BaseModel):
    year: int
    listed: int = Field(description="assemblies NCBI Datasets lists for this release year")
    assessed: int = Field(description="of those, assessed so far (this run and earlier runs)")


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
    plasmid_info_recorded: bool = Field(
        default=False,
        description="plasmid sequences were counted for at least one assembly (so the split of "
        "'region not found' can be shown)",
    )
    plasmid_header_examples: list[str] = Field(
        default_factory=list,
        description="FASTA descriptions recognised as plasmids, shown so the rule can be checked",
    )

    @property
    def complete(self) -> bool:
        return self.assessed_total >= self.listed_total
