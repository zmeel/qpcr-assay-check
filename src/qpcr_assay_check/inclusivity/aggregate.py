"""Build the inclusivity trend: bucket the target tier's own hits into years, sample, re-align.

Reuses the "target" tier search every run already makes (taxon-restricted only; no separate,
date-restricted BLAST search -- see docs/ARCHITECTURE.md for why combining ENTREZ_QUERY taxon
restriction with a [PDAT] date filter in one BLAST call cannot be relied on). Each hit's
submission year comes from ESummary, looked up afterwards; the sample for each year is drawn from
whatever the target-tier search actually returned for that year, not from a dedicated per-year
search, so a target with far more records than the hit-list cap allows may under-represent recent
(or old) years depending on where in BLAST's own ranking those records fall -- reported honestly
via ``population_size`` (an independent ESearch count) next to ``sample_size``, never presented as
the full population.
"""

from __future__ import annotations

import itertools
import logging
from collections import defaultdict
from datetime import UTC, datetime

from ..align import realign
from ..config import Config, InclusivitySettings
from ..models import Assay
from ..ncbi.blast import build_entrez_query
from ..ncbi.cache import Cache
from ..ncbi.eutils import Eutils
from ..ncbi.http import NcbiError
from ..ncbi.parser import ParsedSearch
from ..search.planner import SearchPlan
from ..specificity.fetch import WindowFetcher
from ..specificity.models import SiteResult
from ..specificity.sites import Candidate, make_candidate
from ..verdict import Verdict
from .dates import fetch_years
from .models import InclusivityOligoResult, InclusivityResult, WindowStats
from .sites import assess_candidates

log = logging.getLogger(__name__)

ROLES = ("forward", "reverse", "probe")


def _sample(candidates: list[Candidate], n: int) -> list[Candidate]:
    """Deterministic, evenly spread sample, one per accession, ordered by accession.

    Of a record's candidates (alternative oligos of the role, degenerate variants, several HSPs)
    the one closest to binding represents it: alternatives in one mix, the best one binds.
    """
    by_accession: dict[str, Candidate] = {}
    for c in candidates:
        cur = by_accession.get(c.accession)
        if cur is None or (c.lower_bound, -c.hsp.identity) < (cur.lower_bound, -cur.hsp.identity):
            by_accession[c.accession] = c
    ordered = [by_accession[a] for a in sorted(by_accession)]
    if len(ordered) <= n:
        return ordered
    step = len(ordered) / n
    return [ordered[int(i * step)] for i in range(n)]


def _stats(
    sites: list[SiteResult], year: int, population: int | None, oligo_len: int
) -> WindowStats:
    per_position = [0] * oligo_len
    n_perfect = n_one = n_two_plus = n_three_prime = n_failed = 0
    for s in sites:
        # in inclusivity's own assess_candidates, worst-case only happens when a fetch failed
        # (there is no can_reach_warning-style pruning here, unlike the off-target assessment)
        if s.source == "blast_partial_worst_case":
            n_failed += 1
        for p in s.defect_positions:
            if 1 <= p <= oligo_len:
                per_position[p - 1] += 1
        if s.n_gap or s.n_mismatch >= 2:
            n_two_plus += 1
        elif s.n_mismatch == 1:
            n_one += 1
        else:
            n_perfect += 1
        if s.mismatches_last5:
            n_three_prime += 1
    return WindowStats(
        year=year,
        population_size=population,
        sample_size=len(sites),
        n_perfect=n_perfect,
        n_one_mismatch=n_one,
        n_two_plus_mismatch=n_two_plus,
        n_three_prime_mismatch=n_three_prime,
        per_position_mismatches=per_position,
        n_fetch_failed=n_failed,
    )


def _population(
    eutils: Eutils, taxid: int, year: int, exclude: list[int] | None = None
) -> int | None:
    try:
        term = f"{build_entrez_query([taxid], exclude)} AND {year}/01/01:{year}/12/31[PDAT]"
        return eutils.esearch_count("nuccore", term)
    except NcbiError as exc:
        log.warning("Could not count year %d population: %s", year, exc)
        return None


def compute_inclusivity(
    assay: Assay,
    cfg: Config,
    plan: SearchPlan,
    parsed: dict[str, ParsedSearch],
    fetcher: WindowFetcher,
    eutils: Eutils,
    cache: Cache,
    *,
    tier_searched: bool,
    now: datetime | None = None,
) -> InclusivityResult:
    """Bucket the target tier's hits into years, sample, re-align, and aggregate."""
    rules = cfg.inclusivity
    if not tier_searched or assay.target.taxid is None:
        return InclusivityResult(
            tier_searched=False,
            target_taxid=assay.target.taxid,
            verdict=Verdict.INCOMPLETE,
            rationale=["The target tier was not searched: inclusivity has no evidence."],
        )

    taxid = assay.target.taxid
    current_year = (now or datetime.now(UTC)).year
    years = list(range(current_year - rules.lookback_years + 1, current_year + 1))
    exclude = assay.target.exclude_taxids
    populations = {year: _population(eutils, taxid, year, exclude) for year in years}

    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    ids = itertools.count(1)
    target_searches = [ps for ps in plan.searches if ps.tier == "target"]
    min_identical = cfg.search.relevance.min_identical_bases

    oligo_results: list[InclusivityOligoResult] = []
    for role in ROLES:
        members = assay.by_role(role)
        oligo = " / ".join(o.sequence for o in members)  # alternatives in the same mix
        oligo_len = max(len(o.sequence) for o in members)
        site_rules = cfg.specificity.probe_site if role == "probe" else cfg.specificity.primer_site
        candidates: list[Candidate] = []
        for ps in target_searches:
            if ps.key not in parsed:
                continue
            for label in ps.labels:
                if assay.role_of(label) != role:
                    continue
                q = parsed[ps.key].queries[label]
                oligo_variant = plan.queries[label]
                candidates += [
                    make_candidate("target", label, oligo_variant, hit, hsp, role)
                    for hit in q.hits
                    for hsp in hit.hsps
                    if hsp.identity >= min_identical
                ]

        accessions = sorted({c.accession for c in candidates if c.accession != "unknown"})
        years_by_accession = (
            fetch_years(eutils, cache, accessions, ttl_days=cfg.ncbi.taxonomy_cache_ttl_days)
            if accessions
            else {}
        )

        by_year: dict[int, list[Candidate]] = defaultdict(list)
        n_no_date = 0
        for c in candidates:
            year = years_by_accession.get(c.accession)
            if year is None:
                n_no_date += 1
            else:
                by_year[year].append(c)

        windows: list[WindowStats] = []
        for year in years:
            sample = _sample(by_year.get(year, []), rules.sample_per_window)
            sites = assess_candidates(
                sample, site_rules, fetcher, scoring, cfg.specificity.window_padding_nt, ids
            )
            windows.append(_stats(sites, year, populations[year], oligo_len))
        oligo_results.append(
            InclusivityOligoResult(role=role, oligo=oligo, windows=windows, n_no_date=n_no_date)
        )

    verdict, rationale = _verdict(oligo_results, rules)
    rationale += _unassessed_years(oligo_results)
    if any(
        len(parsed[ps.key].queries[label].hits) >= cfg.search.hitlist_size
        for ps in target_searches
        if ps.key in parsed
        for label in ps.labels
    ):
        rationale.append(
            "The target search's hit list was full, and BLAST lists the best-scoring matches "
            "first: each year's sample is drawn from those hits, so it is biased toward perfect "
            "matches and can understate how many records carry mismatches."
        )
    return InclusivityResult(
        tier_searched=True,
        target_taxid=taxid,
        oligos=oligo_results,
        sample_scheme=(
            f"Up to {rules.sample_per_window} record(s) per year sampled from the target tier's "
            f"own BLAST hits (evenly spread by accession), over the last {rules.lookback_years} "
            "year(s); population size per year from an independent ESearch count."
        ),
        verdict=verdict,
        rationale=rationale,
        limitations=[
            "The sample for each year comes from whatever the target-tier BLAST search actually "
            "returned for that year, not a dedicated per-year search: a target with far more "
            "records than the hit-list cap allows may under- or over-represent some years "
            "depending on BLAST's own ranking, not a controlled random sample of the population.",
            "A record's submission year comes from ESummary and has not been checked against "
            "live NCBI output as thoroughly as the rest of this tool; see docs/ARCHITECTURE.md.",
        ],
    )


def _unassessed_years(oligos: list[InclusivityOligoResult]) -> list[str]:
    """Years with records at NCBI but no sampled record: stated, never silently left out."""
    missing: dict[int, tuple[int, list[str]]] = {}
    for o in oligos:
        for w in o.windows:
            if w.sample_size == 0 and w.population_size:
                missing.setdefault(w.year, (w.population_size, []))[1].append(o.role)
    return [
        f"{year}: {population} record(s) at NCBI, but none among the target tier's BLAST hits "
        f"for {', '.join(roles)}; this year was not assessed."
        for year, (population, roles) in sorted(missing.items())
    ]


def _verdict(
    oligos: list[InclusivityOligoResult], rules: InclusivitySettings, *, sampled: bool = True
) -> tuple[Verdict, list[str]]:
    """Worst oligo/window's % at 0-1 mismatch (no 3' mismatch) decides the verdict."""
    rationale: list[str] = []
    worst_pct: float | None = None
    for o in oligos:
        for w in o.windows:
            if w.sample_size == 0:
                continue
            good = w.n_perfect + w.n_one_mismatch - w.n_three_prime_mismatch
            good = max(0, good)
            pct = 100.0 * good / w.sample_size
            if worst_pct is None or pct < worst_pct:
                worst_pct = pct
            if pct < rules.warn_below_percent:
                rationale.append(
                    f"{o.role}, {w.year}: {pct:.0f}% of {w.sample_size} "
                    f"{'sampled' if sampled else 'assessed'} record(s) at "
                    "0-1 mismatch with no 3'-end mismatch (below "
                    f"{rules.warn_below_percent:g}%)."
                )
    if worst_pct is None:
        return Verdict.INCOMPLETE, ["No target-tier record with a known submission year was found."]
    if worst_pct < rules.fail_below_percent:
        return Verdict.FAIL, rationale
    if worst_pct < rules.warn_below_percent:
        return Verdict.WARN, rationale
    return Verdict.PASS, [
        "Every assessed year is at or above the configured inclusivity threshold."
    ]
