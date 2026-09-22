"""Lump the assay's own target-tier hits into unique sequence variants.

The same idea as a hand-built primer/probe conservation report (one row per distinct sequence
variant, with a count and a percentage of the assessed total), generalised beyond single oligos to
the whole fragment (forward + probe + reverse considered together, when all three bind the same
record).

Only sites with a real, fully observed alignment (``source`` ``blast_full`` or ``realigned``) are
counted. A ``blast_partial_worst_case`` site has assumed-matched flanks, not observed bases;
showing it as a measured variant would misrepresent an estimate as an observation. Excluded counts
are reported so this is never silently understated.

This is purely a different view of evidence the specificity assessment already scored (like
``taxonomy/rollup.py``'s species/genus/family aggregation): it carries no verdict of its own.
"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from ..models import Assay
from .models import Level, SiteResult, SpecificityResult

_MEASURED = {"blast_full", "realigned"}
_RANK = {"critical": 0, "warning": 1, "minor": 2}
_ROLES = ("forward", "probe", "reverse")


class VariantRow(BaseModel):
    """One unique alignment of an oligo against the target, and how often it was seen."""

    q_aln: str
    s_aln: str
    midline: str
    count: int
    percent: float
    level: Level
    n_mismatch: int
    n_gap: int
    example_accession: str
    example_organism: str | None = None
    example_site_id: str


class OligoVariants(BaseModel):
    """Every unique variant seen for one oligo, among the target tier's fully re-aligned hits."""

    role: str
    oligo: str
    total_measured: int
    n_excluded_unmeasured: int = Field(
        description="target-tier sites for this oligo that were not fully re-aligned "
        "(worst-case estimate only); never counted toward a percentage"
    )
    rows: list[VariantRow] = Field(default_factory=list)


class FragmentVariantRow(BaseModel):
    """One unique combination of forward + probe + reverse variants, seen together on a record."""

    forward: VariantRow
    probe: VariantRow
    reverse: VariantRow
    count: int
    percent: float
    level: Level
    example_accession: str
    example_organism: str | None = None


class VariantSummary(BaseModel):
    """The assay's own target-tier hits, lumped into unique variants.

    Informational: it visualises evidence the specificity assessment already scored and carries
    no verdict of its own (see ``docs/ARCHITECTURE.md``).
    """

    oligos: list[OligoVariants] = Field(default_factory=list)
    fragment_total: int = 0
    fragment_excluded_unmeasured: int = Field(
        default=0,
        description="target-tier predicted products excluded from the fragment table: no probe "
        "site inside the product, or one of the three sites was not fully re-aligned",
    )
    fragments: list[FragmentVariantRow] = Field(default_factory=list)


def _variant_row(s: SiteResult, count: int, total: int) -> VariantRow:
    return VariantRow(
        q_aln=s.q_aln,
        s_aln=s.s_aln,
        midline=s.midline,
        count=count,
        percent=100.0 * count / total if total else 0.0,
        level=s.level,
        n_mismatch=s.n_mismatch,
        n_gap=s.n_gap,
        example_accession=s.accession,
        example_organism=s.organism,
        example_site_id=s.id,
    )


def _oligo_variants(target_sites: list[SiteResult], role: str, oligo: str) -> OligoVariants:
    role_sites = [s for s in target_sites if s.role == role]
    measured = [s for s in role_sites if s.source in _MEASURED]
    groups: dict[tuple[str, str], list[SiteResult]] = defaultdict(list)
    for s in measured:
        groups[(s.q_aln, s.s_aln)].append(s)
    total = len(measured)
    rows = [_variant_row(members[0], len(members), total) for members in groups.values()]
    rows.sort(key=lambda r: (-r.count, r.q_aln))
    return OligoVariants(
        role=role,
        oligo=oligo,
        total_measured=total,
        n_excluded_unmeasured=len(role_sites) - len(measured),
        rows=rows,
    )


def build_variant_summary(spec: SpecificityResult, assay: Assay) -> VariantSummary:
    """Build the per-oligo and whole-fragment variant tables from the target tier's own hits."""
    target_sites = [s for s in spec.sites if s.tier == "target"]
    oligo_variants = [
        _oligo_variants(target_sites, role, assay.oligos[role]) for role in _ROLES
    ]  # fmt: skip

    by_id = {s.id: s for s in target_sites}
    target_amplicons = [a for a in spec.amplicons if a.tier == "target"]

    fragment_groups: dict[tuple, list[tuple[SiteResult, SiteResult, SiteResult]]] = defaultdict(
        list
    )
    excluded = 0
    for a in target_amplicons:
        left, right, probe = by_id.get(a.left_site), by_id.get(a.right_site), None
        if a.probe_site:
            probe = by_id.get(a.probe_site)
        if left is None or right is None or probe is None:
            excluded += 1
            continue
        fwd = left if left.role == "forward" else right
        rev = right if right.role == "reverse" else left
        if fwd.role != "forward" or rev.role != "reverse":
            excluded += 1  # defensive: pairing.py should never produce this
            continue
        unmeasured = {fwd.source, rev.source, probe.source} - _MEASURED
        if unmeasured:
            excluded += 1
            continue
        key = ((fwd.q_aln, fwd.s_aln), (probe.q_aln, probe.s_aln), (rev.q_aln, rev.s_aln))
        fragment_groups[key].append((fwd, probe, rev))

    total_fragments = sum(len(v) for v in fragment_groups.values())
    fragments = []
    for members in fragment_groups.values():
        fwd, probe, rev = members[0]
        count = len(members)
        level: Level = min((fwd.level, probe.level, rev.level), key=lambda lv: _RANK[lv])
        fragments.append(
            FragmentVariantRow(
                forward=_variant_row(fwd, count, total_fragments),
                probe=_variant_row(probe, count, total_fragments),
                reverse=_variant_row(rev, count, total_fragments),
                count=count,
                percent=100.0 * count / total_fragments if total_fragments else 0.0,
                level=level,
                example_accession=fwd.accession,
                example_organism=fwd.organism,
            )
        )
    fragments.sort(key=lambda f: (-f.count, f.forward.s_aln, f.probe.s_aln, f.reverse.s_aln))

    return VariantSummary(
        oligos=oligo_variants,
        fragment_total=total_fragments,
        fragment_excluded_unmeasured=excluded,
        fragments=fragments,
    )
