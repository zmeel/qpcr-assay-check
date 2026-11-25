"""Result models of the specificity assessment (serialised into results.json)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..verdict import Verdict

Level = Literal["critical", "warning", "minor"]
SiteSource = Literal["blast_full", "realigned", "blast_partial_worst_case", "scanned"]


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
    subject_length: int | None = Field(default=None, description="length of the subject record")
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
    grade: str | None = Field(
        default=None,
        description="graded mismatch class (docs/MISMATCH_CLASSES.md), on the target and, with "
        "specificity.graded_off_target, on off-target sites: "
        "perfect | tolerated | at_risk | likely_failure | indeterminate",
    )
    grade_rule: str = ""
    grade_note: str = ""
    cautious: bool = Field(
        default=False,
        description="in a cautious tier (specificity.cautious_tiers): graded at risk or "
        "indeterminate, the site primes or binds at warning level",
    )
    channel_sites: list[SiteResult] = Field(
        default_factory=list,
        exclude=True,
        description="probes in several reporter channels, exhaustive analysis: the best site of "
        "each channel on the same copy (detectable from parts: on the cut copies, possibly "
        "different ones), reporter order (not serialised)",
    )


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
    channels: list[str] = Field(
        default_factory=list,
        description="detection channels with a probe binding inside the product (overhaul step 6)",
    )
    classification: Literal["likely_detected", "amplified_not_detected"]
    record_type: Literal["genomic", "transcript", "other"]
    note: str = ""


class Finding(BaseModel):
    """One line of the specificity rationale."""

    severity: Literal["FAIL", "WARN", "INFO", "INCOMPLETE"]
    message: str
    topic: Literal["sites", "amplicons", "search"] = "sites"
    # the sign-off's wording (report, Part A): short, without the explanation; lines with the
    # same tier and short are merged there, their ``about`` listed (user, 2026-11-20). Empty:
    # the sign-off prints ``message``.
    short: str = ""
    tier: str = ""
    about: str = ""
    # what a site or product finding counts, for the report's tier table (user, 2026-11-25):
    # primer_critical_product, primer_critical_no_product, primer_warning, probe_critical,
    # probe_warning, products_detected, products_not_detected (partner_scan_summary and
    # primer_only_summary: said in the products paragraph); with the number of sites or
    # products and the closest site's id. Empty for every other finding.
    kind: str = ""
    count: int = 0
    site: str = ""


class TierCount(BaseModel):
    """Numbers of hits examined for one tier and query oligo."""

    tier: str
    query: str
    blast_hits: int
    hsps_relevant: int
    sites_assessed: int
    truncated: bool = False


class ScoreFloor(BaseModel):
    """The smallest alignment score the searches of one tier could report for one oligo."""

    tier: str
    query: str
    length: int
    min_score: int | None = Field(
        description="highest score floor of the tier's searches; None without search statistics"
    )
    max_mismatches_reported: int | None = Field(
        description="mismatches (no gap) a full-length site may have and still always be reported"
    )
    searches_without_statistics: int = 0
    list_full: bool = Field(
        default=False, description="a search of this tier filled its hit list for this oligo"
    )
    space_source: str = Field(
        default="reported",
        description="how the search space was known: reported, from_hits or upper_bound "
        "(the least direct one among the tier's searches)",
    )
    per_search: list[tuple[list[int], int | None]] = Field(
        default_factory=list,
        description="(taxa searched, score floor) per search of the tier, in plan order: the "
        "tier's floor is the highest of them (tiers review 2026-11-20, F6)",
    )


class PartnerScan(BaseModel):
    """The partner scan: windows next to off-target primer sites searched for partners and
    probes that BLAST did not report."""

    primer_sites: int = Field(
        description="off-target primer sites that can prime and formed no product from BLAST's "
        "sites alone"
    )
    windows: int = Field(description="windows next to primer sites scanned for partners")
    product_windows: int = Field(
        default=0, description="products fetched to re-align the probes in"
    )
    windows_failed: int = 0
    not_scanned: int = Field(default=0, description="primer sites beyond the window limit")
    no_accession: int = Field(
        default=0, description="primer sites on a record without accession: not scannable"
    )
    product_windows_failed: int = 0
    products_not_scanned: int = Field(
        default=0, description="products without a probe site beyond the product limit"
    )
    products_not_scanned_by_tier: dict[str, int] = Field(default_factory=dict)
    product_windows_failed_by_tier: dict[str, int] = Field(default_factory=dict)
    primer_sites_added: int = 0
    probe_sites_added: int = 0


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
    score_floors: list[ScoreFloor] = Field(default_factory=list)
    partner_scan: PartnerScan | None = None
    restriction_by_lineage: dict[str, dict[str, int]] = Field(
        default_factory=dict,
        description="per tier, the relevant hits by the NCBI lineage of their organism: inside "
        "the tier's taxa, set aside (outside them, or the target itself) and not checkable (no "
        "taxid or lineage); empty without lineages (tiers review 2026-11-20, F5)",
    )
