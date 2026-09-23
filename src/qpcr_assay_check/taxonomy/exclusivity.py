"""Build the exclusivity report: the clinical organism list against already-assessed hits.

The 'exclusivity' tier's BLAST hits are assessed exactly like any other off-target tier (full-length
re-alignment, site classification, amplicon pairing: see ``specificity/``) because it is one of
``specificity.off_target_tiers``. What this module adds is SPEC.md step 8's own view of that same
evidence: one row per organism in the list -- including organisms with zero hits, and organism
names that did not resolve to a taxonomy ID at all (never silently dropped) -- rather than one row
per BLAST hit.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from ..config import SeverityMap
from ..specificity.models import AmpliconResult, SiteResult
from ..verdict import Verdict
from .plan import OrganismListResolution
from .resolve import Resolution

_LEVEL_RANK = {"critical": 2, "warning": 1, "minor": 0}


class ExclusivityRow(BaseModel):
    """One organism-list entry and the strongest evidence found against it."""

    organism: str
    taxid: int | None = None
    resolution: Literal["resolved", "ambiguous", "unresolved"]
    is_target: bool = Field(
        default=False,
        description=(
            "this taxid is the assay's own intended target: excluded from the exclusivity "
            "search, since a perfect match there is expected and is not evidence of "
            "cross-reactivity, not a genuine off-target finding"
        ),
    )
    n_sites: int = 0
    best_site_id: str | None = None
    best_site_level: Literal["critical", "warning", "minor"] | None = None
    amplicon_predicted: bool = False
    amplicon_classification: Literal["likely_detected", "amplified_not_detected"] | None = None


class ExclusivityResult(BaseModel):
    """The exclusivity tier's report: per-organism table, its own verdict, and open resolutions."""

    tier_searched: bool
    verdict: Verdict
    rows: list[ExclusivityRow]
    unresolved: list[Resolution]
    n_organisms: int
    n_resolved: int
    source: Literal["assay", "global"] | None = Field(
        default=None,
        description="Which exclusivity list this run used: this assay's own "
        "'exclusivity_organisms', or the global/packaged list. None when the tier was never "
        "searched, so no list was ever loaded.",
    )


def _best(sites: list[SiteResult]) -> SiteResult:
    return max(sites, key=lambda s: (_LEVEL_RANK[s.level], -(s.n_mismatch + s.n_gap)))


def _row_verdict_severities(
    sites: list[SiteResult], amplicons: list[AmpliconResult], sev: SeverityMap
) -> set[str]:
    """Severities contributed by exclusivity-tier evidence, same mapping as specificity findings."""
    out: set[str] = set()
    for s in sites:
        if s.level == "minor":
            continue
        if s.role == "probe":
            if s.level == "critical":
                out.add(sev.probe_site_critical)
        else:
            out.add(sev.primer_site_critical if s.level == "critical" else sev.primer_site_warning)
    for a in amplicons:
        out.add(
            sev.amplicon_likely_detected
            if a.classification == "likely_detected"
            else sev.amplicon_not_detected
        )
    return out


def build_exclusivity(
    resolution: OrganismListResolution | None,
    sites: list[SiteResult],
    amplicons: list[AmpliconResult],
    sev: SeverityMap,
    *,
    tier_searched: bool,
    target_taxid: int | None = None,
    taxon_species: dict[int, str] | None = None,
) -> ExclusivityResult:
    """Group the exclusivity tier's already-assessed sites/amplicons by organism-list entry.

    A BLAST hit's own ``taxid`` is whatever NCBI Taxonomy record the matched sequence is filed
    under, which for some organisms is a strain-level taxon more specific than the species-level
    (or higher) taxid an organism-list name like "Influenza A virus" resolves to (confirmed live:
    ~10% of a real Influenza A-restricted search's hits carried a distinct, more specific taxid --
    see docs/ARCHITECTURE.md). Grouping by exact taxid equality alone would silently drop those
    hits from their organism's row. ``taxon_species`` (taxid -> species name, from
    ``taxonomy.resolve.fetch_lineages``, covering both the hit taxids and the organism-list's own
    resolved taxids) lets a hit be matched to a row by species instead when both are known;
    grouping falls back to the bare taxid for anything missing from that map, exactly as before,
    never guessing a species that was not actually looked up.

    Missing evidence (saturation, fetch failures, hit-list truncation) is reported at the overall
    specificity level, not recomputed per organism here. ``target_taxid``, if given, marks the
    organism-list row that is the assay's own intended target (see ``ExclusivityRow.is_target``):
    that taxid is never searched as part of this tier (see ``search/execute.py``), so its row is
    never populated from ``sites``/``amplicons`` here either, even defensively.
    """
    taxon_species = taxon_species or {}

    def group_key(taxid: int) -> str:
        species = taxon_species.get(taxid)
        return f"species:{species}" if species else f"taxid:{taxid}"

    excl_sites = [s for s in sites if s.tier == "exclusivity"]
    excl_amplicons = [a for a in amplicons if a.tier == "exclusivity"]
    sites_by_key: dict[str, list[SiteResult]] = {}
    for s in excl_sites:
        if s.taxid is not None:
            sites_by_key.setdefault(group_key(s.taxid), []).append(s)
    amplicons_by_key: dict[str, list[AmpliconResult]] = {}
    for a in excl_amplicons:
        if a.taxid is not None:
            amplicons_by_key.setdefault(group_key(a.taxid), []).append(a)

    resolutions = resolution.resolutions if resolution else []
    rows: list[ExclusivityRow] = []
    for r in resolutions:
        is_target = r.taxid is not None and r.taxid == target_taxid
        row = ExclusivityRow(
            organism=r.name, taxid=r.taxid, resolution=r.status, is_target=is_target
        )
        if r.taxid is not None and not is_target:
            key = group_key(r.taxid)
            hits = sites_by_key.get(key, [])
            row.n_sites = len(hits)
            if hits:
                best = _best(hits)
                row.best_site_id, row.best_site_level = best.id, best.level
            amps = amplicons_by_key.get(key, [])
            if amps:
                row.amplicon_predicted = True
                row.amplicon_classification = (
                    "likely_detected"
                    if any(a.classification == "likely_detected" for a in amps)
                    else "amplified_not_detected"
                )
        rows.append(row)

    if not tier_searched:
        verdict = Verdict.INCOMPLETE  # missing evidence is never a PASS
    else:
        severities = _row_verdict_severities(excl_sites, excl_amplicons, sev)
        verdict = (
            Verdict.FAIL
            if "FAIL" in severities
            else Verdict.WARN
            if "WARN" in severities
            else Verdict.PASS
        )

    return ExclusivityResult(
        tier_searched=tier_searched,
        verdict=verdict,
        rows=rows,
        unresolved=resolution.unresolved if resolution else [],
        n_organisms=len(resolutions),
        n_resolved=sum(1 for r in resolutions if r.status == "resolved"),
        source=resolution.source if resolution else None,
    )
