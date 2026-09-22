"""Result models. Everything here is serialised to ``results.json`` (schema_version 1)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from .history.models import HistoryResult
from .inclusivity.models import InclusivityResult
from .models import Assay, Status
from .specificity.models import SpecificityResult
from .taxonomy.exclusivity import ExclusivityResult
from .taxonomy.rollup import TaxonCount
from .verdict import Verdict

RESULTS_SCHEMA_VERSION = 1


class CheckResult(BaseModel):
    """One scored (or informational) QC check."""

    id: str
    subject: str = Field(description="forward | reverse | probe | pair | amplicon")
    name: str
    status: Status
    display: str = Field(description="Formatted value(s) for tables")
    value: float | None = None
    value_min: float | None = None
    value_max: float | None = None
    unit: str = ""
    message: str = ""
    rule: str = ""


class StructureResult(BaseModel):
    """Worst hairpin/dimer found for one oligo or oligo pair."""

    kind: Literal["hairpin", "homodimer", "heterodimer", "end_dimer"]
    label: str
    subjects: list[str]
    found: bool
    tm_c: float | None = None
    dg_kcal: float | None = None
    temp_c: float
    status: Status
    variant: str | None = Field(
        default=None, description="Degenerate variant(s) giving the worst case"
    )
    n_evaluated: int = 1
    n_total: int = 1
    ascii_lines: list[str] = Field(default_factory=list)


class OligoInfo(BaseModel):
    """An oligo as evaluated, including its degenerate expansion."""

    role: str
    sequence: str
    length_nt: int
    degenerate: bool
    n_variants: int
    variants: list[str]
    gc_percent_min: float
    gc_percent_max: float
    tm_c_min: float
    tm_c_max: float


class SiteInfo(BaseModel):
    """Position of an oligo in the reference amplicon (1-based, sense-strand coordinates)."""

    oligo: str
    strand: Literal["+", "-"]
    start: int
    end: int
    mismatches: int


class AmpliconSummary(BaseModel):
    """Geometry of the amplicon defined by the primers within the reference amplicon."""

    input_length_nt: int
    product_length_nt: int | None = None
    product_gc_percent: float | None = None
    forward_site: SiteInfo | None = None
    reverse_site: SiteInfo | None = None
    probe_site: SiteInfo | None = None
    overlap_forward_nt: int | None = None
    overlap_reverse_nt: int | None = None
    gap_forward_probe_nt: int | None = None
    gap_probe_reverse_nt: int | None = None
    flank_5_nt: int | None = None
    flank_3_nt: int | None = None


class QCReport(BaseModel):
    """Everything the oligo QC produced."""

    oligos: list[OligoInfo]
    checks: list[CheckResult]
    structures: list[StructureResult]
    amplicon: AmpliconSummary | None = None
    amplicon_note: str = ""
    tm_unreliable_reasons: list[str] = Field(default_factory=list)
    status: Status


class SectionResult(BaseModel):
    """State of one analysis section of the evaluation."""

    key: str
    title: str
    state: Literal["evaluated", "not_implemented", "skipped"]
    verdict: Verdict | None = None
    note: str = ""
    available_from: str | None = None


class OverallResult(BaseModel):
    """The overall verdict, with the evidence behind it."""

    verdict: Verdict
    exit_code: int
    rationale: list[str]
    required_sections: list[str]


class RunResult(BaseModel):
    """A complete evaluation record."""

    schema_version: int = RESULTS_SCHEMA_VERSION
    tool: dict[str, str]
    run_id: str
    generated_at: str = Field(description="UTC, ISO 8601")
    inputs_hash: str = Field(description="SHA-256 over the assay definition and effective config")
    mode: Literal["full", "qc-only"]
    network_used: bool
    environment: dict[str, str]
    assay: Assay
    config: dict[str, Any]
    oligo_qc: QCReport
    specificity: SpecificityResult | None = None
    exclusivity: ExclusivityResult | None = None
    taxonomy_breakdown: list[TaxonCount] = Field(
        default_factory=list, description="Off-target sites aggregated by species/genus/family"
    )
    inclusivity: InclusivityResult | None = None
    history: HistoryResult | None = None
    search: dict[str, Any] | None = Field(
        default=None, description="Parameters, versions, RIDs and hit counts of the remote searches"
    )
    sections: list[SectionResult]
    overall: OverallResult
