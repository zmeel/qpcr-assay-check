"""Lump the assay's own target-tier hits into unique sequence variants.

The same idea as a hand-built primer/probe conservation report (one row per distinct sequence
variant, with a count and a percentage of the assessed total), generalised beyond single oligos to
the whole fragment (forward + probe + reverse considered together, when all three bind the same
record).

The sites come from :func:`assess_target_sites`: every target-tier BLAST hit, with partial hits
fetched and re-aligned (the off-target assessment never builds target-tier sites). The counts cover
the hits BLAST returned (at most ``hitlist_size`` per oligo), not the whole target population.

Only sites with a real, fully observed alignment (``source`` ``blast_full`` or ``realigned``) are
counted. A ``blast_partial_worst_case`` site has assumed-matched flanks, not observed bases;
showing it as a measured variant would misrepresent an estimate as an observation. Excluded counts
are reported so this is never silently understated.

It carries no verdict of its own.
"""

from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel, Field

from ..align import realign
from ..config import Config
from ..inclusivity.sites import assess_candidates
from ..models import Assay
from ..ncbi.parser import ParsedSearch
from ..search.planner import SearchPlan
from ..variants.models import ExhaustiveCoverage
from .fetch import WindowFetcher
from .models import Level, SiteResult
from .sites import Candidate, make_candidate, role_of

log = logging.getLogger(__name__)

LIST_FULL_NOTE = (
    "The target search's hit list was full: the target has more records than BLAST returns. "
    "BLAST lists the best-scoring matches first, so these hits are biased toward perfect matches; "
    "variants with mismatches can be under-represented or missing entirely, and the percentages "
    "are not the prevalence of each variant in the target population."
)

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
    clean_3prime_nt: int = Field(default=0, description="perfectly matching bases at the 3' end")
    example_accession: str
    example_organism: str | None = None
    example_site_id: str
    first_seen: str | None = Field(
        default=None, description="earliest release date of an assembly with this variant"
    )
    last_seen: str | None = Field(
        default=None, description="latest release date of an assembly with this variant"
    )


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
        description="target-tier records excluded from the fragment table: forward, probe or "
        "reverse missing among the record's hits, or one of the three not fully re-aligned",
    )
    fragments: list[FragmentVariantRow] = Field(default_factory=list)
    target_list_full: bool = Field(
        default=False,
        description="the target search returned a full hit list for at least one oligo, so the "
        "tables are biased toward perfect matches (see LIST_FULL_NOTE)",
    )
    source: Literal["blast_hits", "datasets", "blast_partitioned"] = Field(
        default="blast_hits",
        description="blast_hits: the target tier's BLAST hits; datasets: every genome assembly "
        "of the target in NCBI Datasets (exhaustive, see coverage)",
    )
    coverage: ExhaustiveCoverage | None = None


def _variant_row(
    s: SiteResult, count: int, total: int, dates: list[str] | None = None
) -> VariantRow:
    return VariantRow(
        first_seen=min(dates) if dates else None,
        last_seen=max(dates) if dates else None,
        q_aln=s.q_aln,
        s_aln=s.s_aln,
        midline=s.midline,
        count=count,
        percent=100.0 * count / total if total else 0.0,
        level=s.level,
        n_mismatch=s.n_mismatch,
        n_gap=s.n_gap,
        clean_3prime_nt=s.clean_3prime_nt,
        example_accession=s.accession,
        example_organism=s.organism,
        example_site_id=s.id,
    )


def _dates(members: list[SiteResult], release_dates: dict[str, str]) -> list[str]:
    return [release_dates[m.accession] for m in members if m.accession in release_dates]


def _oligo_variants(
    target_sites: list[SiteResult], role: str, oligo: str, release_dates: dict[str, str]
) -> OligoVariants:
    role_sites = [s for s in target_sites if s.role == role]
    measured = [s for s in role_sites if s.source in _MEASURED]
    groups: dict[tuple[str, str], list[SiteResult]] = defaultdict(list)
    for s in measured:
        groups[(s.q_aln, s.s_aln)].append(s)
    total = len(measured)
    rows = [
        _variant_row(members[0], len(members), total, _dates(members, release_dates))
        for members in groups.values()
    ]
    rows.sort(key=lambda r: (-r.count, r.q_aln))
    return OligoVariants(
        role=role,
        oligo=oligo,
        total_measured=total,
        n_excluded_unmeasured=len(role_sites) - len(measured),
        rows=rows,
    )


def assess_target_sites(
    assay: Assay,
    cfg: Config,
    plan: SearchPlan,
    parsed: dict[str, ParsedSearch],
    fetcher: WindowFetcher,
) -> list[SiteResult]:
    """Full-length sites for every target-tier hit, the best one per record and oligo.

    Partial hits are always fetched and re-aligned (windows are cached), as for inclusivity: a
    variant table needs the observed bases, not a worst-case bound. A record can carry more than
    one HSP per oligo (or one per degenerate variant); the closest match is the one that binds.
    """
    rules = cfg.specificity
    scoring = realign.Scoring(
        rules.alignment.match, rules.alignment.mismatch,
        rules.alignment.gap_open, rules.alignment.gap_extend,
    )  # fmt: skip
    min_identical = cfg.search.relevance.min_identical_bases
    ids = itertools.count(1)
    sites: list[SiteResult] = []
    for ps in plan.searches:
        if ps.tier != "target" or ps.key not in parsed:
            continue
        for label in ps.labels:
            role = role_of(label)
            site_rules = rules.probe_site if role == "probe" else rules.primer_site
            cands: list[Candidate] = [
                make_candidate("target", label, plan.queries[label], hit, hsp)
                for hit in parsed[ps.key].queries[label].hits
                for hsp in hit.hsps
                if hsp.identity >= min_identical
            ]
            n_partial = sum(1 for c in cands if c.partial)
            log.info(
                "Variant summary: %d target-tier site(s) for %s, %d partial (fetched and "
                "re-aligned; windows are cached)", len(cands), label, n_partial,
            )  # fmt: skip
            found = assess_candidates(
                cands, site_rules, fetcher, scoring, rules.window_padding_nt, ids
            )
            sites += [s.model_copy(update={"id": f"T{s.id[1:]}"}) for s in found]

    best: dict[tuple[str, str], SiteResult] = {}
    for s in sites:
        key = (s.accession, s.role)
        if key not in best or _closeness(s) < _closeness(best[key]):
            best[key] = s
    return sorted(best.values(), key=lambda s: int(s.id[1:]))


def _closeness(s: SiteResult) -> tuple[int, int, int, int]:
    measured = 0 if s.source in _MEASURED else 1
    return measured, s.n_mismatch + s.n_gap, -s.clean_3prime_nt, int(s.id[1:])


def build_variant_summary(
    target_sites: list[SiteResult],
    assay: Assay,
    *,
    release_dates: dict[str, str] | None = None,
    coverage: ExhaustiveCoverage | None = None,
) -> VariantSummary:
    """Build the per-oligo and whole-fragment variant tables from the target tier's own sites.

    A fragment is the forward, probe and reverse site found on the same record (one per oligo,
    as :func:`assess_target_sites` returns them), whether or not the primers could prime: a
    variant with a 3'-end mismatch is exactly what the table must show.
    """
    dates = release_dates or {}
    target_sites = [s for s in target_sites if s.tier == "target"]
    oligo_variants = [
        _oligo_variants(target_sites, role, assay.oligos[role], dates) for role in _ROLES
    ]  # fmt: skip

    by_record: dict[str, dict[str, SiteResult]] = defaultdict(dict)
    for s in target_sites:
        if s.accession != "unknown":
            current = by_record[s.accession].get(s.role)
            if current is None or _closeness(s) < _closeness(current):
                by_record[s.accession][s.role] = s

    fragment_groups: dict[tuple, list[tuple[SiteResult, SiteResult, SiteResult]]] = defaultdict(
        list
    )
    excluded = 0
    for roles in by_record.values():
        fwd, probe, rev = roles.get("forward"), roles.get("probe"), roles.get("reverse")
        if fwd is None or probe is None or rev is None:
            excluded += 1
            continue
        if {fwd.source, rev.source, probe.source} - _MEASURED:
            excluded += 1
            continue
        key = ((fwd.q_aln, fwd.s_aln), (probe.q_aln, probe.s_aln), (rev.q_aln, rev.s_aln))
        fragment_groups[key].append((fwd, probe, rev))

    total_fragments = sum(len(v) for v in fragment_groups.values())
    fragments = []
    for members in fragment_groups.values():
        fwd, probe, rev = members[0]
        count = len(members)
        seen = _dates([m[0] for m in members], dates)
        level: Level = min((fwd.level, probe.level, rev.level), key=lambda lv: _RANK[lv])
        fragments.append(
            FragmentVariantRow(
                forward=_variant_row(fwd, count, total_fragments, seen),
                probe=_variant_row(probe, count, total_fragments, seen),
                reverse=_variant_row(rev, count, total_fragments, seen),
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
        source=coverage.source if coverage is not None else "blast_hits",  # type: ignore[arg-type]
        coverage=coverage,
    )
