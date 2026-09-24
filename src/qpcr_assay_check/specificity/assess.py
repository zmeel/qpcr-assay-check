"""Assess BLAST hits: full-length re-alignment, site classification, products, verdict."""

from __future__ import annotations

import itertools
import logging
from collections import defaultdict

from ..align import realign
from ..config import Config
from ..models import Assay
from ..ncbi.parser import ParsedSearch
from ..oligo import thermo
from ..search.orchestrate import SearchOutcome
from ..search.planner import SearchPlan
from .duplex import estimate_duplex
from .fetch import WindowFetcher
from .findings import build_findings, verdict_of
from .models import Finding, SiteResult, SpecificityResult, TierCount
from .pairing import predict_amplicons, primer_can_prime
from .sites import (
    Candidate,
    can_reach_warning,
    make_candidate,
    oriented_window,
    site_from_alignment,
    site_from_bound,
    site_from_full,
    window_for,
)

log = logging.getLogger(__name__)

LIMITATIONS = [
    "BLAST is a heuristic seeded by exact 7-base matches: a site with widely spaced mismatches "
    "can be missed, so an absent hit is not proof of absent binding.",
    "Partial BLAST hits that were not re-aligned are assessed with the most risk-conservative "
    "assumption compatible with BLAST's scoring; they are marked as worst case.",
    "Duplex Tm and ΔG are nearest-neighbour estimates of stability. A mismatch at the 3'-terminal "
    "base is treated as an unpaired overhang and barely lowers Tm although it usually prevents "
    "extension; priming is judged from the mismatch and 3'-end columns.",
    "Products are predicted from the primary record of each BLAST hit group; identical sequences "
    "merged into one hit are not expanded, so a product on a merged record can be missed.",
    "Only the tiers named in the scope statement were searched; a passing result says nothing "
    "about organisms outside them. Primer-BLAST remains a useful manual cross-check.",
]


def assess_specificity(
    assay: Assay,
    cfg: Config,
    plan: SearchPlan,
    parsed: dict[str, ParsedSearch],
    outcome: SearchOutcome,
    fetcher: WindowFetcher,
) -> SpecificityResult:
    """Assess the off-target tiers of a completed search."""
    rules = cfg.specificity
    scoring = realign.Scoring(
        rules.alignment.match,
        rules.alignment.mismatch,
        rules.alignment.gap_open,
        rules.alignment.gap_extend,
    )
    cond = thermo.Conditions.from_reaction(cfg.reaction)
    min_identical = cfg.search.relevance.min_identical_bases
    ids = itertools.count(1)

    sites: list[SiteResult] = []
    pending: list[Candidate] = []
    tally: dict[tuple[str, str], TierCount] = {}
    off_tiers_seen: list[str] = []

    for ps in plan.searches:
        if ps.tier not in rules.off_target_tiers or ps.key not in parsed:
            continue
        if ps.tier not in off_tiers_seen:
            off_tiers_seen.append(ps.tier)
        for label in ps.labels:
            q = parsed[ps.key].queries[label]
            oligo = plan.queries[label]
            role = assay.role_of(label)
            site_rules = rules.probe_site if role == "probe" else rules.primer_site
            cands = [
                make_candidate(ps.tier, label, oligo, hit, hsp, role)
                for hit in q.hits
                for hsp in hit.hsps
                if hsp.identity >= min_identical
            ]
            cands.sort(key=lambda c: (c.lower_bound, -c.hsp.identity, c.hsp.evalue))
            chosen = cands[: rules.max_sites_per_query]
            t = tally.setdefault(
                (ps.tier, label),
                TierCount(
                    tier=ps.tier, query=label, blast_hits=0, hsps_relevant=0, sites_assessed=0
                ),
            )
            t.blast_hits += len(q.hits)
            t.hsps_relevant += len(cands)
            t.sites_assessed += len(chosen)
            t.truncated = t.truncated or len(cands) > len(chosen)
            for c in chosen:
                if not c.partial:
                    sites.append(site_from_full(c, site_rules, f"S{next(ids)}"))
                elif not can_reach_warning(c, site_rules):
                    sites.append(site_from_bound(c, site_rules, f"S{next(ids)}"))
                else:
                    pending.append(c)

    # ---- fetch windows for the candidates that could still matter, then re-align
    log.info("Re-aligning %d partial hits (windows are cached)", len(pending))
    for n, c in enumerate(pending, start=1):
        site_rules = rules.probe_site if c.role == "probe" else rules.primer_site
        window = None
        if c.accession != "unknown":
            lo, hi = window_for(c, rules.window_padding_nt, c.hit.length)
            window = fetcher.get(c.accession, lo, hi)
        if window is None:
            sites.append(site_from_bound(c, site_rules, f"S{next(ids)}"))
        else:
            oriented = oriented_window(window, c.orientation)
            aln = realign.align_semiglobal(c.oligo, oriented, scoring)
            sites.append(site_from_alignment(c, aln, window, lo, site_rules, f"S{next(ids)}"))
        if n % 200 == 0:
            log.info("  %d / %d windows done", n, len(pending))

    n_sites = {"critical": 0, "warning": 0, "minor": 0}
    for s in sites:
        n_sites[s.level] += 1

    # ---- keep every critical/warning site plus the closest minor ones for display
    keep = [s for s in sites if s.level != "minor"]
    minor: dict[tuple[str, str], list[SiteResult]] = defaultdict(list)
    for s in sites:
        if s.level == "minor":
            minor[(s.tier, s.query)].append(s)
    for group in minor.values():
        group.sort(key=lambda s: (s.n_mismatch + s.n_gap, -s.clean_3prime_nt, s.id))
        keep.extend(group[: rules.report_top_sites])
    keep.sort(key=lambda s: int(s.id[1:]))

    for s in keep:
        if s.source == "blast_partial_worst_case":
            continue
        nM = cfg.reaction.probe_nM if s.role == "probe" else cfg.reaction.primer_nM
        s.tm_c, s.dg_kcal, s.delta_tm_c = estimate_duplex(s.oligo, s.s_aln, cond, nM)

    # ---- products
    priming = [s for s in keep if s.role == "probe" or primer_can_prime(s)]
    amplicons, used, amp_truncated = predict_amplicons(priming, rules, assay)
    n_primer_only = sum(1 for s in priming if primer_can_prime(s) and s.id not in used)

    saturated = [
        (r.tier, sat.label, sat.note)
        for r in outcome.searches
        if r.tier in rules.off_target_tiers
        for sat in r.saturation
        if sat.saturated
    ]
    intended: dict[str, int] = defaultdict(int)
    for r in outcome.searches:
        if r.tier == "target":
            for label, n in r.perfect_full_length.items():
                intended[label] += n

    findings = build_findings(
        sites=keep,
        amplicons=amplicons,
        site_by_id={s.id: s for s in keep},
        counts=list(tally.values()),
        saturated=saturated,
        off_tiers_seen=off_tiers_seen,
        intended_target=dict(intended),
        target_searched=any(r.tier == "target" for r in outcome.searches),
        n_primer_only=n_primer_only,
        n_fetch_failed=fetcher.n_failed,
        amplicons_truncated=amp_truncated,
        rules=rules,
    )
    verdict = verdict_of(findings)
    rationale = [f.message for f in findings if f.severity in ("FAIL", "INCOMPLETE", "WARN")]
    if not rationale:
        rationale = [
            "No off-target site or product reached warning level in the searched tiers "
            f"({', '.join(off_tiers_seen)})."
        ]
    scope = next((f.message for f in findings if f.topic == "search" and f.severity == "INFO"), "")
    return SpecificityResult(
        verdict=verdict,
        verdict_sites=verdict_of(findings, {"sites", "search"}),
        verdict_amplicons=verdict_of(findings, {"amplicons"}),
        scope=scope,
        intended_target=dict(intended),
        n_fetched=fetcher.n_network + fetcher.n_cached,
        n_fetch_failed=fetcher.n_failed,
        rationale=rationale,
        findings=sorted(findings, key=_order),
        counts=list(tally.values()),
        n_sites=n_sites,
        n_primer_only=n_primer_only,
        sites=keep,
        amplicons=amplicons,
        searches=[r.model_dump(mode="json") for r in outcome.searches],
        parameters={
            "alignment": rules.alignment.model_dump(),
            "primer_site": rules.primer_site.model_dump(),
            "probe_site": rules.probe_site.model_dump(),
            "severity": rules.severity.model_dump(),
            "window_padding_nt": rules.window_padding_nt,
            "max_amplicon_size": rules.max_amplicon_size,
            "min_identical_bases": min_identical,
            "blast": outcome.parameters,
            "databases": sorted({r.database for r in outcome.searches if r.database}),
            "blast_versions": sorted(
                {r.blast_version for r in outcome.searches if r.blast_version}
            ),
        },
        limitations=list(LIMITATIONS),
    )


_RANK = {"FAIL": 0, "INCOMPLETE": 1, "WARN": 2, "INFO": 3}


def _order(f: Finding) -> tuple[int, str]:
    return _RANK[f.severity], f.message
