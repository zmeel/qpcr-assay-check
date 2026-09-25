"""Result models for the inclusivity assessment (serialised into results.json)."""

from __future__ import annotations

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
    sample_scheme: str = ""
    verdict: Verdict
    rationale: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
