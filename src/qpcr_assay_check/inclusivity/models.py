"""Result models for the inclusivity assessment (serialised into results.json)."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field

from ..verdict import Verdict


class WindowStats(BaseModel):
    """One year's inclusivity statistics for one oligo, from a sampled subset of that year."""

    year: int
    population_size: int | None = Field(
        description="ESearch count of target-taxon records published in this year, or None if "
        "it could not be counted; the honest denominator this sample is drawn from."
    )
    sample_size: int
    n_perfect: int = Field(description="0 mismatches, 0 gaps")
    n_one_mismatch: int = Field(description="exactly 1 mismatch, 0 gaps")
    n_two_plus_mismatch: int = Field(description="2+ mismatches, or any gap")
    n_three_prime_mismatch: int = Field(description="a mismatch in the last 5 nt of the oligo")
    n_detectable: int | None = Field(
        default=None,
        description="graded mismatch class perfect or tolerated (docs/MISMATCH_CLASSES.md); "
        "None in records made before the classes",
    )
    n_by_grade: dict[str, int] = Field(default_factory=dict, description="records per class")
    n_undetermined: int = Field(
        default=0,
        description="a mismatch in an MGB probe or an ambiguity code in the genome (rules R9, R6): "
        "no published basis, left out of the detectable percentage",
    )
    per_position_mismatches: list[int] = Field(
        description="mismatch count at each 1-based oligo position, across this window's sample"
    )
    n_fetch_failed: int = 0


class InclusivityOligoResult(BaseModel):
    """Inclusivity trend for one oligo, across every assessed year."""

    role: str
    oligo: str
    windows: list[WindowStats] = Field(default_factory=list)
    n_no_date: int = Field(
        default=0, description="sampled hits whose submission year could not be determined"
    )


class FragmentYear(BaseModel):
    """Per year: the genome outcome from the three best-copy sites together (forward, probe,
    reverse), as in the whole-fragment table; exhaustive analysis only."""

    year: int
    population_size: int | None = None
    with_region: int = Field(description="records with all three sites assessed")
    detectable: int = 0
    at_risk: int = 0
    likely_failure: int = 0
    undetermined: int = 0
    by_pair_rule: int = Field(default=0, description="likely failure decided by R8 alone")
    unassembled: int = Field(
        default=0,
        description="of the undetermined: draft genomes whose copies are possibly unassembled",
    )
    from_parts: int = Field(
        default=0, description="of the undetermined: genomes detectable from parts (cut copies)"
    )
    unjudged: int = Field(
        default=0,
        description="of the undetermined: region there, but cut by a contig end or hidden by N, "
        "so no site could be judged",
    )
    label: str = Field(default="", description="row name when not a year (collection axis)")


class CollectionAxis(BaseModel):
    """The genomes of the release-year window again, by the year their sample was collected
    (as the submitter recorded it). Information only: the verdict stays per release year."""

    first_year: int = Field(description="first release year of the window")
    last_year: int
    years: list[FragmentYear] = Field(
        default_factory=list, description="collection years inside the window, oldest first"
    )
    earlier: FragmentYear = Field(description="collected before the window's first year")
    undated: FragmentYear = Field(
        description="no usable collection date: none given, no year in it, or a year after the "
        "window"
    )
    not_read: FragmentYear = Field(
        description="collection date not read yet (stored before it was read, and not listed "
        "again since)"
    )


class DistinctPatterns(BaseModel):
    """The status window again, with genomes of identical sites counted once (theory reviews
    2026-10-01, user 2026-10-02): a clonal outbreak sequenced a thousand times is one pattern.
    Information only, next to the genome count; the status uses the genome count."""

    first: int
    last: int
    axis: str = Field(default="release", description="release or collection year")
    genomes: int = Field(description="judged genomes in the window (undetermined left out)")
    patterns: int = Field(description="distinct best-copy site patterns among them")
    detectable: int = 0
    at_risk: int = 0
    likely_failure: int = 0
    largest: int = Field(default=0, description="genomes carrying the most common pattern")
    likely_failure_genomes: int = 0

    @property
    def percent(self) -> float | None:
        return 100.0 * self.detectable / self.patterns if self.patterns else None


@dataclass(frozen=True)
class FragmentWindow:
    """The whole-fragment outcome pooled over the verdict window: the last ``window_years``
    complete release years plus the most recent year with data."""

    first: int
    last: int
    years: list[FragmentYear]
    with_region: int
    undetermined: int
    detectable: int
    at_risk: int
    likely_failure: int
    unassembled: int = 0  # of the undetermined: copies possibly unassembled
    from_parts: int = 0  # of the undetermined: detectable from parts
    unjudged: int = 0  # of the undetermined: region cut by a contig end or hidden by N

    @property
    def n(self) -> int:
        """The base of the percentages: records with the region, undetermined left out."""
        return self.with_region - self.undetermined

    @property
    def percent(self) -> float | None:
        return 100.0 * self.detectable / self.n if self.n > 0 else None


def fragment_window(years: list[FragmentYear], window_years: int) -> FragmentWindow | None:
    """Pool the per-year whole-fragment outcome over the verdict window (None without data)."""
    with_data = [y for y in years if y.with_region]
    if not with_data:
        return None
    last = max(y.year for y in with_data)
    window = [y for y in years if last - window_years <= y.year <= last]
    return FragmentWindow(
        first=min(y.year for y in window),
        last=last,
        years=window,
        with_region=sum(y.with_region for y in window),
        undetermined=sum(y.undetermined for y in window),
        detectable=sum(y.detectable for y in window),
        at_risk=sum(y.at_risk for y in window),
        likely_failure=sum(y.likely_failure for y in window),
        unassembled=sum(y.unassembled for y in window),
        from_parts=sum(y.from_parts for y in window),
        unjudged=sum(y.unjudged for y in window),
    )


class InclusivityResult(BaseModel):
    """Everything the inclusivity assessment found."""

    tier_searched: bool
    exhaustive: bool = Field(
        default=False,
        description="built from every genome assembly of the target (v1.1.0), not a sample",
    )
    target_taxid: int | None = None
    oligos: list[InclusivityOligoResult] = Field(default_factory=list)
    fragment_years: list[FragmentYear] = Field(
        default_factory=list, description="whole-fragment outcome per year (exhaustive only)"
    )
    collection: CollectionAxis | None = Field(
        default=None, description="the same genomes by collection year (exhaustive analysis)"
    )
    status_axis: str = Field(
        default="release",
        description="release: the status window counts release years; collection: collection "
        "years (genomes without a usable date left out)",
    )
    distinct: DistinctPatterns | None = Field(
        default=None, description="the status window with identical site patterns counted once"
    )
    sample_scheme: str = ""
    verdict: Verdict
    rationale: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def status_years(inc: InclusivityResult) -> list[FragmentYear]:
    """The rows the status window is pooled from: release years, or collection years."""
    if inc.status_axis == "collection":
        return inc.collection.years if inc.collection is not None else []
    return inc.fragment_years
