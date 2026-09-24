"""Result models of the specificity assessment (serialised into results.json)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..verdict import Verdict

Level = Literal["critical", "warning", "minor"]
SiteSource = Literal["blast_full", "realigned", "blast_partial_worst_case"]


class SiteResult(BaseModel):
    """One full-length alignment of an oligo to a subject sequence."""

    id: str
    tier: str
    query: str = Field(description="FASTA label, e.g. forward or forward_v2")
    role: Literal["forward", "reverse", "probe"]
    oligo: str
    accession: str
    taxid: int | None = None
    organism: str | None = None
    title: str = ""
    n_merged: int = 1
    orientation: Literal["+", "-"] = Field(
        description=(
            "'+': the oligo equals the subject's forward strand; '-': its reverse complement does"
        )
    )
    subject_start: int
    subject_end: int
    source: SiteSource
    q_aln: str
    s_aln: str
    midline: str
    n_match: int
    n_mismatch: int
    n_gap: int
    n_ambiguous: int
    n_unaligned: int = 0
    defect_positions: list[int]
    mismatches_last5: int
    mismatches_last3: int
    terminal_defect: bool
    clean_3prime_nt: int
    tm_c: float | None = None
    dg_kcal: float | None = None
    delta_tm_c: float | None = Field(default=None, description="duplex Tm minus perfect-match Tm")
    note: str = Field(
        default="", description="e.g. a homopolymer run-length variant aligned as a bulge"
    )
    level: Level


class AmpliconResult(BaseModel):
    """A predicted PCR product: two primer sites facing each other on one subject."""

    id: str
    tier: str
    accession: str
    taxid: int | None = None
    organism: str | None = None
    roles: str = Field(description="e.g. forward/reverse")
    left_site: str
    right_site: str
    start: int
    end: int
    length: int
    probe_site: str | None = None
    classification: Literal["likely_detected", "amplified_not_detected"]
    record_type: Literal["genomic", "transcript", "other"]
    note: str = ""


class Finding(BaseModel):
    """One line of the specificity rationale."""

    severity: Literal["FAIL", "WARN", "INFO", "INCOMPLETE"]
    message: str
    topic: Literal["sites", "amplicons", "search"] = "sites"


class TierCount(BaseModel):
    """Numbers of hits examined for one tier and query oligo."""

    tier: str
    query: str
    blast_hits: int
    hsps_relevant: int
    sites_assessed: int
    truncated: bool = False


class SpecificityResult(BaseModel):
    """Everything the specificity assessment found."""

    verdict: Verdict
    verdict_sites: Verdict = Field(description="verdict of the site findings alone")
    verdict_amplicons: Verdict = Field(description="verdict of the amplicon findings alone")
    scope: str = ""
    intended_target: dict[str, int] = Field(
        default_factory=dict, description="perfect full-length hits per oligo in the target tier"
    )
    n_fetched: int = 0
    n_fetch_failed: int = 0
    rationale: list[str]
    findings: list[Finding]
    counts: list[TierCount]
    n_sites: dict[str, int] = Field(description="sites per level")
    n_primer_only: int = 0
    sites: list[SiteResult]
    amplicons: list[AmpliconResult]
    searches: list[dict] = Field(default_factory=list, description="search records incl. RIDs")
    parameters: dict = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
