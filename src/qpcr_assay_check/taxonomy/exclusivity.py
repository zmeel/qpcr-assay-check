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

from pydantic import BaseModel

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
) -> ExclusivityResult:
    """Group the exclusivity tier's already-assessed sites/amplicons by organism-list entry.

    Missing evidence (saturation, fetch failures, hit-list truncation) is reported at the overall
    specificity level, not recomputed per organism here.
    """
    excl_sites = [s for s in sites if s.tier == "exclusivity"]
    excl_amplicons = [a for a in amplicons if a.tier == "exclusivity"]
    sites_by_taxid: dict[int, list[SiteResult]] = {}
    for s in excl_sites:
        if s.taxid is not None:
            sites_by_taxid.setdefault(s.taxid, []).append(s)
    amplicons_by_taxid: dict[int, list[AmpliconResult]] = {}
    for a in excl_amplicons:
        if a.taxid is not None:
            amplicons_by_taxid.setdefault(a.taxid, []).append(a)

    resolutions = resolution.resolutions if resolution else []
    rows: list[ExclusivityRow] = []
    for r in resolutions:
        row = ExclusivityRow(organism=r.name, taxid=r.taxid, resolution=r.status)
        if r.taxid is not None:
            hits = sites_by_taxid.get(r.taxid, [])
            row.n_sites = len(hits)
            if hits:
                best = _best(hits)
                row.best_site_id, row.best_site_level = best.id, best.level
            amps = amplicons_by_taxid.get(r.taxid, [])
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
    )
