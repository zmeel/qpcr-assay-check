"""Result models for the run-to-run diff (serialised into results.json)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..verdict import Verdict

Level = Literal["critical", "warning", "minor"]


class SectionChange(BaseModel):
    """One report section's verdict, before and after."""

    key: str
    title: str
    verdict_before: Verdict | None = None
    verdict_after: Verdict | None = None
    changed: bool = False


class SiteChange(BaseModel):
    """An off-target site that appeared, disappeared, or changed level/mismatches.

    Matched across runs by a natural key (tier, role, accession, orientation, subject start/end)
    rather than by the run-local ``id`` field, which is only stable within one run.
    """

    kind: Literal["new", "resolved", "changed"]
    tier: str
    role: Literal["forward", "reverse", "probe"]
    accession: str
    orientation: Literal["+", "-"]
    subject_start: int
    subject_end: int
    organism: str | None = None
    level_before: Level | None = None
    level_after: Level | None = None
    n_mismatch_before: int | None = None
    n_mismatch_after: int | None = None


class AmpliconChange(BaseModel):
    """A predicted off-target product that appeared or disappeared.

    Matched across runs by a natural key (tier, accession, start, end, roles).
    """

    kind: Literal["new", "resolved"]
    tier: str
    accession: str
    start: int
    end: int
    roles: str
    organism: str | None = None
    classification: Literal["likely_detected", "amplified_not_detected"] | None = None


class InclusivityYearChange(BaseModel):
    """One oligo/year window's sampled match rate, before and after."""

    role: str
    year: int
    percent_before: float | None = None
    percent_after: float | None = None
    sample_size_before: int = 0
    sample_size_after: int = 0
    new_mismatch_positions: list[int] = Field(
        default_factory=list,
        description="1-based oligo positions with 0 mismatches before but >0 now (both sampled)",
    )


class HistoryResult(BaseModel):
    """The diff of this run against the most recent previous run for the same assay."""

    has_previous: bool
    previous_run_id: str | None = None
    previous_generated_at: str | None = None
    inputs_changed: bool = False
    verdict_before: Verdict | None = None
    verdict_changed: bool = False
    section_changes: list[SectionChange] = Field(default_factory=list)
    new_sites: list[SiteChange] = Field(default_factory=list)
    resolved_sites: list[SiteChange] = Field(default_factory=list)
    changed_sites: list[SiteChange] = Field(default_factory=list)
    new_amplicons: list[AmpliconChange] = Field(default_factory=list)
    resolved_amplicons: list[AmpliconChange] = Field(default_factory=list)
    inclusivity_changes: list[InclusivityYearChange] = Field(default_factory=list)
    verdict: Verdict
    rationale: list[str] = Field(default_factory=list)
