"""Predict PCR products from primer sites that face each other on the same subject record."""

from __future__ import annotations

from collections import defaultdict

from ..config import SpecificitySettings
from ..models import Assay, TemplateType
from .models import AmpliconResult, SiteResult
from .sites import record_type


def primer_can_prime(site: SiteResult) -> bool:
    """A primer site at critical or warning level is assumed able to prime."""
    return site.role in ("forward", "reverse") and site.level != "minor"


def probe_binds(site: SiteResult, rules: SpecificitySettings) -> bool:
    """Does a probe site reach the level configured as 'binds well enough to give signal'?"""
    if site.role != "probe":
        return False
    if rules.probe_binds_if == "critical":
        return site.level == "critical"
    return site.level in ("critical", "warning")


def _note(assay: Assay, rules: SpecificitySettings, site: SiteResult, rtype: str) -> str:
    """Genomic-DNA versus cDNA remark for RNA assays and eukaryotic subjects."""
    if assay.template_type is not TemplateType.RNA or site.taxid not in rules.eukaryote_taxids:
        return ""
    if rtype == "genomic":
        return (
            "Genomic record of a eukaryote: this product matters to an RNA assay only if the "
            "specimen contains genomic DNA and no intron separates the primer sites."
        )
    if rtype == "transcript":
        return "Transcript record: this product would also arise from RNA."
    return ""


def predict_amplicons(
    sites: list[SiteResult], rules: SpecificitySettings, assay: Assay
) -> tuple[list[AmpliconResult], set[str], bool]:
    """Pair forward and reverse primer sites; returns ``(amplicons, ids of sites used, truncated)``.

    A pair forms a product when one site lies on each strand, they face each other (the '+' site
    starts first and the '-' site ends last), and the product is at most ``max_amplicon_size``.
    The probe counts as binding if a probe site of sufficient level lies inside the product.
    Pairing uses the *primary* record of each BLAST hit group: identical sequences merged into one
    hit are not expanded, so a product on a merged record can be missed.
    """
    groups: dict[tuple[str, str], list[SiteResult]] = defaultdict(list)
    for s in sites:
        groups[(s.tier, s.accession)].append(s)

    out: list[AmpliconResult] = []
    used: set[str] = set()
    truncated = False
    for key in sorted(groups):
        members = sorted(groups[key], key=lambda x: (x.subject_start, x.subject_end, x.id))
        plus = [s for s in members if primer_can_prime(s) and s.orientation == "+"]
        minus = [s for s in members if primer_can_prime(s) and s.orientation == "-"]
        probes = [s for s in members if s.role == "probe"]
        for left in plus:
            for right in minus:
                if {left.role, right.role} != {"forward", "reverse"}:
                    continue
                if not (
                    left.subject_start < right.subject_start
                    and left.subject_end < right.subject_end
                ):
                    continue
                length = right.subject_end - left.subject_start + 1
                if length > rules.max_amplicon_size:
                    continue
                if len(out) >= rules.max_amplicons:
                    truncated = True
                    return out, used, truncated
                inside = [
                    p
                    for p in probes
                    if p.subject_start >= left.subject_start and p.subject_end <= right.subject_end
                ]
                binding = [p for p in inside if probe_binds(p, rules)]
                pool = binding or inside
                best = min(pool, key=lambda p: (p.n_mismatch + p.n_gap, p.id)) if pool else None
                rtype = record_type(left.accession, left.title)
                out.append(
                    AmpliconResult(
                        id=f"A{len(out) + 1}",
                        tier=left.tier,
                        accession=left.accession,
                        taxid=left.taxid,
                        organism=left.organism,
                        roles=f"{left.role}/{right.role}",
                        left_site=left.id,
                        right_site=right.id,
                        start=left.subject_start,
                        end=right.subject_end,
                        length=length,
                        probe_site=best.id if best else None,
                        classification="likely_detected" if binding else "amplified_not_detected",
                        record_type=rtype,  # type: ignore[arg-type]
                        note=_note(assay, rules, left, rtype),
                    )
                )
                used.update({left.id, right.id})
    return out, used, truncated
