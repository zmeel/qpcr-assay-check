"""Predict PCR products from primer sites that face each other on the same subject record."""

from __future__ import annotations

import logging
import re
from collections import defaultdict

from ..config import SpecificitySettings
from ..models import Assay, TemplateType
from .models import AmpliconResult, SiteResult
from .sites import record_type

log = logging.getLogger(__name__)


def oligo_of(label: str) -> str:
    """The oligo a query label stands for: a degenerate variant (``forward_v3``) counts as its
    oligo (``forward``)."""
    return re.sub(r"_v\d+$", "", label)


def site_quality(site: SiteResult) -> tuple[int, int, int, str]:
    """Sort key, best site first: fewest mismatches and gaps, longest clean 3' end, first id."""
    num = site.id[1:]
    return (
        site.n_mismatch + site.n_gap, -site.clean_3prime_nt,
        int(num) if num.isdigit() else 0, site.id,
    )  # fmt: skip


def same_site_groups(sites: list[SiteResult]) -> list[list[SiteResult]]:
    """Sites of one oligo on one record, tier and strand whose spans overlap, best first.

    Each degenerate variant is a query of its own, so one binding site is reported once per
    variant that reaches it; a group is that one site (code review, 2026-11-17: the HSV-1
    primers, 8 variants each, counted one HSV-2 product up to 64 times).
    """
    by: dict[tuple[str, str, str, str, str], list[SiteResult]] = defaultdict(list)
    for s in sites:
        by[(s.tier, s.accession, s.role, oligo_of(s.query), s.orientation)].append(s)
    groups: list[list[SiteResult]] = []
    for key in sorted(by):
        members = sorted(by[key], key=lambda s: (s.subject_start, s.subject_end, s.id))
        current: list[SiteResult] = []
        end = 0
        for s in members:
            if current and s.subject_start <= end:
                current.append(s)
                end = max(end, s.subject_end)
            else:
                if current:
                    groups.append(current)
                current, end = [s], s.subject_end
        if current:
            groups.append(current)
    return [sorted(g, key=site_quality) for g in groups]


def best_of_each_site(sites: list[SiteResult]) -> list[SiteResult]:
    """One site per binding site: the best variant of each :func:`same_site_groups` group."""
    return [g[0] for g in same_site_groups(sites)]


def _channels(assay: Assay, binding: list[SiteResult]) -> list[str]:
    """The channels whose probes bind inside a product (a degenerate variant counts as its
    oligo), in the assay's channel order."""
    names = {oligo_of(p.query) for p in binding}
    return [ch.name for ch in assay.channels if names & set(ch.probes)]


def _who(site: SiteResult) -> str:
    """The oligo's name for a named oligo, else its role (unchanged for single-oligo assays)."""
    name = oligo_of(site.query)
    return site.role if name == site.role else name


#: Classes under which an off-target site acts whatever its level: the grading expects little
#: or no effect (e.g. a terminal G3 mismatch, R1 tolerated, which the count-based levels called
#: minor because no 3' base is clean).
GOOD = frozenset({"perfect", "tolerated"})


def _acts_by_grade(site: SiteResult, strong: bool) -> bool:
    """Both rule sets together (whole-project review, 2026-11-17, P3): a site graded likely
    failure never acts (e.g. 3 primer mismatches in the 3'-most 16 nt, R3; one mismatch under an
    MGB, R9); a site graded perfect or tolerated always does; at risk and indeterminate act at a
    level that acted before (``strong``). The R1-R9 classes rest on near-identical target
    sequences and count primer mismatches only in the 3'-most 16 nt, so for a distant off-target
    sequence the level still bounds the rest."""
    if site.grade == "likely_failure":
        return False
    if site.cautious and site.grade in ("at_risk", "indeterminate") and site.level != "minor":
        # near neighbours, read in the cautious direction (tiers review 2026-11-20, F8): at
        # warning level, gaps included, whatever probe_binds_if says; a minor site stays bounded
        # by the level (the classes count primer mismatches only in the 3'-most 16 nt, so random
        # sequence can grade at risk: a run of N did, 2026-11-20)
        return True
    return site.grade in GOOD or strong


def grade_site(site: SiteResult, assay: Assay, cautious: bool = False) -> None:
    """Give an off-target site the class the assay's own target sites get (R1-R9; MGB rules for
    an MGB probe), so one rule set decides priming and binding everywhere (whole-project review,
    2026-11-17, P3: the count-based levels called a single mismatch at -1 to -3 unable to prime,
    though R1 grades some of those tolerated, and let a probe with 3 mismatches bind, MGB probes
    included). A site that already has a class keeps it. ``cautious``: the site lies in a tier
    of ``specificity.cautious_tiers``."""
    site.cautious = site.cautious or cautious
    if site.grade is not None or not site.q_aln or not site.s_aln:
        return
    if site.source == "blast_partial_worst_case":
        # its unaligned bases are assumed to fit as well as possible (risk-conservative);
        # grading them as unknown mismatches would hide a possible cross-reaction, so the
        # levels decide, as before
        return
    if len(site.q_aln) != len(site.s_aln):
        log.warning("Site %s: alignment strings of different length; graded by level only",
                    site.id)  # fmt: skip
        return
    from ..oligo.grade import grade_fields

    name = oligo_of(site.query)
    o = next((x for x in assay.oligo_list if x.name == name), None)
    # an unread base (N) is no evidence of binding off target: a mismatch, as in the partner
    # scan, not an ambiguity code to grade both ways (a run of N would otherwise "prime")
    s_aln = site.s_aln.upper().replace("N", ".")
    fields = grade_fields(site.q_aln, s_aln, site.role, mgb=o is not None and o.has_mgb())
    for key, value in fields.items():
        setattr(site, key, value)


def primer_can_prime(site: SiteResult) -> bool:
    """Can an off-target primer site prime? With a graded class: never when likely failure,
    always when perfect or tolerated, else at critical or warning level (:func:`_acts_by_grade`);
    without one (``specificity.graded_off_target: false``), by level alone."""
    if site.role not in ("forward", "reverse"):
        return False
    if site.grade is not None:
        return _acts_by_grade(site, site.level != "minor")
    return site.level != "minor"


def probe_binds(site: SiteResult, rules: SpecificitySettings) -> bool:
    """Does a probe site give signal inside a product? With a graded class (R9, MGB rules
    included): never when likely failure, always when perfect or tolerated, else at the level set
    in ``probe_binds_if``; without one, by that level alone."""
    if site.role != "probe":
        return False
    strong = (
        site.level == "critical"
        if rules.probe_binds_if == "critical"
        else site.level in ("critical", "warning")
    )
    if site.grade is not None:
        return _acts_by_grade(site, strong)
    return strong


def _note(
    assay: Assay,
    rules: SpecificitySettings,
    site: SiteResult,
    rtype: str,
    lineage: set[int] | None = None,
) -> str:
    """Genomic-DNA versus cDNA remark for RNA assays and eukaryotic subjects: the organism, or
    one of its NCBI ancestors (``lineage``, when known), is in ``eukaryote_taxids`` (tiers
    review 2026-11-20, F9: an exact match left Candida or Trichomonas without the note)."""
    eukaryote = set(rules.eukaryote_taxids)
    found = site.taxid in eukaryote or bool(lineage and eukaryote & lineage)
    if assay.template_type is not TemplateType.RNA or not found:
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
    sites: list[SiteResult],
    rules: SpecificitySettings,
    assay: Assay,
    lineage: dict[int, set[int]] | None = None,
) -> tuple[list[AmpliconResult], set[str], set[str]]:
    """Pair forward and reverse primer sites; returns ``(amplicons, ids of sites used, tiers
    whose product list was cut)``. ``max_amplicons`` applies per tier, so one tier with many
    products (e.g. out-of-scope relatives) cannot crowd out another tier's products.

    A pair forms a product when one site lies on each strand, they face each other (the '+' site
    starts first and the '-' site ends last), and the product is at most ``max_amplicon_size``.
    The probe counts as binding if a probe site of sufficient level lies inside the product.
    Pairing uses the *primary* record of each BLAST hit group: identical sequences merged into one
    hit are not expanded, so a product on a merged record can be missed.

    The degenerate variants of a primer that reach the same site are one site: the best variant
    pairs, and every variant of a site that pairs counts as used, so one product is one product.
    """
    same: dict[str, list[str]] = {}
    primers: list[SiteResult] = []
    for g in same_site_groups([s for s in sites if primer_can_prime(s)]):
        same[g[0].id] = [s.id for s in g]
        primers.append(g[0])
    groups: dict[tuple[str, str], list[SiteResult]] = defaultdict(list)
    for s in [*primers, *(s for s in sites if s.role == "probe")]:
        groups[(s.tier, s.accession)].append(s)

    out: list[AmpliconResult] = []
    used: set[str] = set()
    truncated: set[str] = set()
    per_tier: dict[str, int] = defaultdict(int)
    for key in sorted(groups):
        tier = key[0]
        if tier in truncated:
            continue
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
                if per_tier[tier] >= rules.max_amplicons:
                    truncated.add(tier)
                    break
                per_tier[tier] += 1
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
                        roles=f"{_who(left)}/{_who(right)}",
                        left_site=left.id,
                        right_site=right.id,
                        start=left.subject_start,
                        end=right.subject_end,
                        length=length,
                        probe_site=best.id if best else None,
                        channels=_channels(assay, binding),
                        classification="likely_detected" if binding else "amplified_not_detected",
                        record_type=rtype,  # type: ignore[arg-type]
                        note=_note(
                            assay,
                            rules,
                            left,
                            rtype,
                            (lineage or {}).get(left.taxid) if left.taxid is not None else None,
                        ),  # fmt: skip
                    )
                )
                used.update([*same[left.id], *same[right.id]])
    return out, used, truncated
