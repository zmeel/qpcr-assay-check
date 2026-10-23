"""Assess BLAST hits: full-length re-alignment, site classification, products, verdict."""

from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from collections.abc import Callable

from ..align import realign
from ..config import Config
from ..models import Assay
from ..ncbi.http import NcbiError
from ..ncbi.parser import Hit, ParsedSearch
from ..oligo import thermo
from ..search.orchestrate import SearchOutcome
from ..search.planner import OUT_OF_SCOPE_TIER, SearchPlan
from .duplex import estimate_duplex
from .fetch import WindowFetcher
from .findings import build_findings, verdict_of
from .models import Finding, PartnerScan, SiteResult, SpecificityResult, TierCount
from .pairing import predict_amplicons, primer_can_prime
from .reach import floor_findings, floors
from .scan import PartnerScanner, progress_step
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
    "BLAST reports a site only when it contains an exact match as long as the BLAST word (7 bases, "
    "the smallest NCBI's remote BLAST allows for blastn) and its alignment scores high enough for "
    "the E-value cut-off. The smallest reportable score depends on the size of each search and "
    "is given per tier and oligo under 'search' (computed from NCBI's own search statistics); a "
    "site scoring less can be missing, so an absent hit is not proof of absent binding.",
    "Partial BLAST hits that were not re-aligned are assessed with the most risk-conservative "
    "assumption compatible with BLAST's scoring; they are marked as worst case.",
    "Duplex Tm and ΔG are nearest-neighbour estimates of stability. A mismatch at the 3'-terminal "
    "base is treated as an unpaired overhang and barely lowers Tm although it usually prevents "
    "extension; priming is judged from the mismatch and 3'-end columns.",
    "Products are predicted from the primary record of each BLAST hit group; identical sequences "
    "merged into one hit are not expanded, so a product on a merged record can be missed.",
    "Products are predicted from a forward and a reverse primer facing each other. A product from "
    "one primer binding both strands (forward-forward or reverse-reverse) is not predicted; for a "
    "primer that binds an off-target organism perfectly this is unlikely but not excluded.",
    "Only the tiers named in the scope statement were searched; a passing result says nothing "
    "about organisms outside them. Primer-BLAST remains a useful manual cross-check.",
]


SCAN_LIMITATION = (
    "The partner scan narrows that gap for the second primer and the probe of a product once "
    "BLAST has reported one primer site; a product of which BLAST reported neither primer site "
    "is not found."
)
NO_SCAN_LIMITATION = (
    "The partner scan was switched off (specificity.partner_scan_max_windows: 0): a product "
    "whose second primer site or probe site BLAST did not report is not found."
)


def _in_tier(hit: Hit, wanted: set[int], lineage: dict[int, set[int]]) -> Hit | None:
    """``hit`` if one of its records is of an organism under the tier's taxa, else None.

    NCBI's ``ENTREZ_QUERY`` restriction is not airtight (an influenza A record came back in an
    exclusivity search without influenza A, 2026-10-21), so each hit is checked against the
    lineage of its own organism. A hit without records, a record without a taxid, or one whose
    lineage could not be read counts as inside: nothing shows it is outside. When the first
    record of a merged hit is outside and another is inside, the inside one is moved first,
    since the site is reported under the first record.
    """

    def inside(taxid: int | None) -> bool:
        return taxid is None or taxid not in lineage or bool(wanted & lineage[taxid])

    if not hit.descriptions:
        return hit
    keep = [d for d in hit.descriptions if inside(d.taxid)]
    if not keep:
        return None
    if keep[0] is hit.descriptions[0]:
        return hit
    rest = [d for d in hit.descriptions if d is not keep[0]]
    return hit.model_copy(update={"descriptions": [keep[0], *rest]})


def _lineages(
    plan: SearchPlan,
    parsed: dict[str, ParsedSearch],
    assessed: list[str],
    ancestors_of: Callable[[list[int]], dict[int, set[int]]] | None,
    min_identical: int,
) -> tuple[dict[int, set[int]] | None, str]:
    """The NCBI ancestors of the organisms of the assessed tiers' relevant hits (those with an
    alignment of at least ``min_identical`` identical bases: the rest give no site anyway), and
    a problem if the lookup failed."""
    if ancestors_of is None:
        return None, ""
    taxids = {
        d.taxid
        for ps in plan.searches
        if ps.tier in assessed and ps.key in parsed
        for q in parsed[ps.key].queries.values()
        for hit in q.hits
        if hit.best_identity >= min_identical
        for d in hit.descriptions
        if d.taxid is not None
    }
    if not taxids:
        return {}, ""
    try:
        return ancestors_of(sorted(taxids)), ""
    except NcbiError as exc:
        log.warning("Could not read the lineages of the hit organisms: %s", exc)
        return None, str(exc)


def assess_specificity(
    assay: Assay,
    cfg: Config,
    plan: SearchPlan,
    parsed: dict[str, ParsedSearch],
    outcome: SearchOutcome,
    fetcher: WindowFetcher,
    ancestors_of: Callable[[list[int]], dict[int, set[int]]] | None = None,
) -> SpecificityResult:
    """Assess the off-target tiers of a completed search.

    ``ancestors_of``: NCBI lineages of taxa (``taxonomy.resolve.ancestors``). When given, a hit
    whose organism is outside the taxa its tier searched is set aside rather than assessed under
    that tier, and the findings say so; without it every hit counts, as before.
    """
    rules = cfg.specificity
    assessed = [*rules.off_target_tiers, OUT_OF_SCOPE_TIER]  # out of scope: reported, not judged
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

    lineage, lineage_problem = _lineages(plan, parsed, assessed, ancestors_of, min_identical)
    set_aside: dict[str, dict[str, str]] = defaultdict(dict)  # tier -> accession -> organism

    for ps in plan.searches:
        if ps.tier not in assessed or ps.key not in parsed:
            continue
        if ps.tier not in off_tiers_seen:
            off_tiers_seen.append(ps.tier)
        wanted = set(ps.taxids)
        for label in ps.labels:
            q = parsed[ps.key].queries[label]
            oligo = plan.queries[label]
            role = assay.role_of(label)
            site_rules = rules.probe_site if role == "probe" else rules.primer_site
            hits = q.hits
            if lineage is not None and wanted:
                hits = []
                for hit in q.hits:
                    if hit.best_identity < min_identical:
                        continue  # gives no candidate, so nothing to keep or set aside
                    kept = _in_tier(hit, wanted, lineage)
                    if kept is not None:
                        hits.append(kept)
                    elif hit.descriptions:
                        d = hit.descriptions[0]
                        set_aside[ps.tier][d.accession_version or d.accession or "?"] = (
                            d.sciname or "?"
                        )
            cands = [
                make_candidate(ps.tier, label, oligo, hit, hsp, role)
                for hit in hits
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
    failed_by_tier: dict[str, int] = defaultdict(int)
    step = progress_step(len(pending))
    for n, c in enumerate(pending, start=1):
        site_rules = rules.probe_site if c.role == "probe" else rules.primer_site
        window = None
        if c.accession != "unknown":
            lo, hi = window_for(c, rules.window_padding_nt, c.hit.length)
            before = fetcher.n_failed
            window = fetcher.get(c.accession, lo, hi)
            failed_by_tier[c.tier] += fetcher.n_failed - before
        if window is None:
            sites.append(site_from_bound(c, site_rules, f"S{next(ids)}"))
        else:
            oriented = oriented_window(window, c.orientation)
            aln = realign.align_semiglobal(c.oligo, oriented, scoring)
            sites.append(site_from_alignment(c, aln, window, lo, site_rules, f"S{next(ids)}"))
        if n % step == 0 or n == len(pending):  # read by the GUI's progress bar
            log.info("  %d / %d windows done", n, len(pending))

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

    # ---- products; then the partner scan: partner primers next to off-target primer sites
    # that form no product yet, and probes re-aligned inside products without a probe site
    def pair() -> tuple[list[SiteResult], list, set[str], set[str]]:
        priming = [s for s in keep if s.role == "probe" or primer_can_prime(s)]
        return priming, *predict_amplicons(priming, rules, assay)

    priming, amplicons, used, amp_truncated = pair()
    scanning = rules.partner_scan_max_windows > 0
    scanner = PartnerScanner(assay, plan.queries, rules, scoring, fetcher, ids)
    if scanning:
        # a tier whose product list was cut pairs no further sites: scanning there is wasted
        anchors = [
            s
            for s in keep
            if s.tier in rules.off_target_tiers
            and s.tier not in amp_truncated
            and primer_can_prime(s)
            and s.id not in used
        ]  # fmt: skip
        log.info("Partner scan next to %d unpaired off-target primer sites", len(anchors))
        added = scanner.partners(sites, anchors)
        if added:
            keep.extend(added)
            sites.extend(added)
            priming, amplicons, used, amp_truncated = pair()
        probes = scanner.probes([a for a in amplicons if a.tier in rules.off_target_tiers], sites)
        if probes:
            keep.extend(probes)
            sites.extend(probes)
            priming, amplicons, used, amp_truncated = pair()
    n_primer_only = sum(1 for s in priming if primer_can_prime(s) and s.id not in used)

    n_sites = {"critical": 0, "warning": 0, "minor": 0}
    for s in sites:
        n_sites[s.level] += 1

    for s in keep:
        if s.source == "blast_partial_worst_case":
            continue
        nM = cfg.reaction.probe_nM if s.role == "probe" else cfg.reaction.primer_nM
        s.tm_c, s.dg_kcal, s.delta_tm_c = estimate_duplex(s.oligo, s.s_aln, cond, nM, s.q_aln)

    saturated = [
        (r.tier, sat.label, sat.note)
        for r in outcome.searches
        if r.tier in assessed
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
        oligo_roles={o.name: o.role for o in assay.oligo_list},
        n_primer_only=n_primer_only,
        n_fetch_failed=sum(n for t, n in failed_by_tier.items() if t != OUT_OF_SCOPE_TIER),
        n_fetch_failed_out_of_scope=failed_by_tier.get(OUT_OF_SCOPE_TIER, 0),
        amplicons_truncated=amp_truncated,
        rules=rules,
    )
    findings.extend(_set_aside_findings(set_aside, lineage_problem))
    score_floors = floors(outcome.searches, plan.queries, assessed, cfg.search)
    findings.extend(floor_findings(score_floors, cfg.search.expect))
    scan = scanner.state.summary if scanning else None
    if scan is not None:
        findings.extend(scan_findings(scan, rules.partner_scan_max_windows))
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
            "partner_scan_max_windows": rules.partner_scan_max_windows,
            "max_amplicon_size": rules.max_amplicon_size,
            "min_identical_bases": min_identical,
            "blast": outcome.parameters,
            "databases": sorted({r.database for r in outcome.searches if r.database}),
            "blast_versions": sorted(
                {r.blast_version for r in outcome.searches if r.blast_version}
            ),
        },
        limitations=[
            LIMITATIONS[0],
            SCAN_LIMITATION if scanning else NO_SCAN_LIMITATION,
            *LIMITATIONS[1:],
        ],
        score_floors=score_floors,
        partner_scan=scan,
    )


def scan_findings(scan: PartnerScan, limit: int) -> list[Finding]:
    """What the partner scan covered and added; INCOMPLETE when it could not cover every
    off-target primer site that can prime, or every product without a probe site."""
    out = [
        Finding(
            severity="INFO",
            message=(
                f"Partner scan: {scan.windows} window(s) next to {scan.primer_sites} unpaired "
                "off-target primer site(s) searched for partner primers, and the probes "
                "re-aligned inside the products without a reported probe site "
                f"({scan.product_windows} product(s) fetched); {scan.primer_sites_added} primer "
                f"and {scan.probe_sites_added} probe site(s) of at least warning level that "
                "BLAST had not reported were added."
            ),
            topic="amplicons",
        )
    ]
    primer_gaps = []
    if scan.not_scanned:
        primer_gaps.append(
            f"{scan.not_scanned} primer site(s) beyond the limit of {limit} fetches "
            "(specificity.partner_scan_max_windows) were not scanned"
        )
    if scan.windows_failed:
        primer_gaps.append(f"{scan.windows_failed} window(s) could not be fetched")
    if scan.no_accession:
        primer_gaps.append(f"{scan.no_accession} primer site(s) lie on a record without accession")
    if primer_gaps:
        out.append(
            Finding(
                severity="INCOMPLETE",
                message=(
                    f"Partner scan incomplete: {'; '.join(primer_gaps)}. A product whose second "
                    "primer BLAST did not report can be missing there."
                ),
                topic="amplicons",
            )
        )
    probe_gaps = []
    if scan.products_not_scanned:
        probe_gaps.append(
            f"{scan.products_not_scanned} product(s) beyond the limit of {limit} fetches were "
            "not searched"
        )
    if scan.product_windows_failed:
        probe_gaps.append(f"{scan.product_windows_failed} product(s) could not be fetched")
    if probe_gaps:
        out.append(
            Finding(
                severity="INCOMPLETE",
                message=(
                    f"Probe re-alignment incomplete: {'; '.join(probe_gaps)}. A probe site BLAST "
                    "did not report can be missing there, so such a product may be detected "
                    "although it is listed as not detected."
                ),
                topic="amplicons",
            )
        )
    return out


_RANK = {"FAIL": 0, "INCOMPLETE": 1, "WARN": 2, "INFO": 3}


def _order(f: Finding) -> tuple[int, str]:
    return _RANK[f.severity], f.message


def _set_aside_findings(set_aside: dict[str, dict[str, str]], problem: str) -> list[Finding]:
    """Say which hits were left out of a tier for being outside its taxa, or that none could be
    checked."""
    out: list[Finding] = []
    if problem:
        out.append(
            Finding(
                severity="INFO",
                message=(
                    "The organisms of the hits could not be checked against the taxa each tier "
                    f"searched (lineage lookup failed: {problem}); a hit outside a tier's taxa, "
                    "which NCBI's taxon restriction lets through occasionally, may be counted in "
                    "that tier."
                ),
                topic="search",
            )
        )
    for tier, records in set_aside.items():
        shown = "; ".join(f"{acc} ({name})" for acc, name in sorted(records.items())[:5])
        more = f" and {len(records) - 5} more" if len(records) > 5 else ""
        out.append(
            Finding(
                severity="INFO",
                message=(
                    f"Tier '{tier}': {len(records)} hit record(s) set aside, their organism being "
                    "outside the taxa this tier searched (NCBI's taxon restriction is not "
                    f"airtight): {shown}{more}. They are not assessed as off-target sites here."
                ),
                topic="search",
            )
        )
    return out
