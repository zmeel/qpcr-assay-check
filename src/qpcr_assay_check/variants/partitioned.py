"""Variant source for targets without genome assemblies: partitioned remote BLAST (v1.1.0).

Every NCBI Nucleotide record of the target taxon (optionally narrowed by
``variants.nucleotide_query``) is listed with ESearch, newest publication year first. The records
are BLASTed in lists of at most ``blast_records_per_search`` accessions: the reference amplicon is
the query and the ENTREZ_QUERY names exactly those accessions, so no search can fill its hit
list. Live check (docs/ARCHITECTURE.md, "Verified for the v1.1.0 design"): a 100-accession list
was accepted, all 100 were hit, and 43 records outside the list came back too -- so every hit is
filtered back to its own list here.

A hit covering the whole amplicon gives the region directly (BLAST writes the subject in the
query's orientation, verified live); a partial hit is completed by fetching the record around it
(``efetch`` window, cached) and locating the amplicon with the same seeds as the assembly source.
A record without a hit is stored as "not found": for Nucleotide records that is usually a
different gene or a partial sequence, not an absent target.

UIDs are mapped to accessions and dates with ESummary, which is keyed by UID (``createdate`` is
``YYYY/MM/DD`` and ``accessionversion`` is present, both verified live); the order of an
``efetch rettype=acc`` answer is never relied on.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime

from ..config import Config
from ..ncbi import blast
from ..ncbi.eutils import Eutils
from ..ncbi.http import NcbiError
from ..ncbi.jobs import Job, JobStore
from ..ncbi.parser import Hsp, parse_blast_json
from ..ncbi.runner import BlastRunner
from ..specificity.fetch import WindowFetcher
from .datasets import AssemblyRecord, parse_fasta_records
from .locate import INDEL_TOLERANCE, Locus, find_loci
from .models import YearCoverage
from .store import RegionStore

log = logging.getLogger(__name__)

EARLIEST_YEAR = 1980
UID_PAGE = 5000
ESUMMARY_BATCH = 200
_DATE_RE = re.compile(r"(\d{4})/(\d{2})/(\d{2})")


def base_term(taxon: int, extra: str | None) -> str:
    term = f"txid{taxon}[ORGN]"
    return f"{term} AND ({extra})" if extra else term


def _year_term(term: str, year: int) -> str:
    return f"{term} AND {year}/01/01:{year}/12/31[PDAT]"


def _record(uid: str, docsum: dict, year: int) -> AssemblyRecord | None:
    acc = docsum.get("accessionversion") or ""
    if not acc:
        return None
    m = _DATE_RE.search(str(docsum.get("createdate") or ""))
    date = f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else str(year)
    try:
        length = int(docsum.get("slen") or 0)
    except (TypeError, ValueError):
        length = 0
    taxid = docsum.get("taxid")
    return AssemblyRecord(
        accession=acc,
        release_date=date,
        assembly_level="Nucleotide record",
        total_length=length,
        organism=str(docsum.get("organism") or ""),
        taxid=int(taxid) if str(taxid or "").isdigit() else None,
    )


def collect_partitioned(
    eutils: Eutils,
    runner: BlastRunner,
    jobs: JobStore,
    fetcher: WindowFetcher,
    store: RegionStore,
    taxon: int,
    amplicon: str,
    cfg: Config,
    *,
    now: datetime | None = None,
) -> tuple[list[YearCoverage], int, int, int, list[str]]:
    """List, BLAST in accession lists, and store the region of new records."""
    v = cfg.variants
    term = base_term(taxon, v.nucleotide_query)
    total = eutils.esearch_count("nuccore", term)
    budget = v.blast_max_records_per_run
    year = (now or datetime.now(UTC)).year
    years: list[YearCoverage] = []
    listed = processed = 0
    n_searches = 0
    while listed < total and year >= EARLIEST_YEAR:
        yterm = _year_term(term, year)
        n_year = eutils.esearch_count("nuccore", yterm)
        if n_year:
            listed += n_year
            start = 0
            while processed < budget and start < n_year:
                uids = eutils.esearch_page("nuccore", yterm, retstart=start, retmax=UID_PAGE)
                start += UID_PAGE
                new = [u for u in uids if u not in store.aliases]
                recs: list[AssemblyRecord] = []
                for i in range(0, len(new), ESUMMARY_BATCH):
                    chunk = new[i : i + ESUMMARY_BATCH]
                    docsums = eutils.esummary("nuccore", chunk)
                    for uid in chunk:
                        rec = _record(uid, docsums.get(uid, {}), year)
                        if rec is None:
                            continue
                        store.aliases.add(uid)
                        if not store.done(rec.accession):
                            recs.append(rec)
                    if processed + len(recs) >= budget:
                        break
                recs = recs[: budget - processed]
                size = v.blast_records_per_search
                for i in range(0, len(recs), size):
                    _search(recs[i : i + size], amplicon, cfg, runner, jobs, fetcher, store)
                    n_searches += 1
                processed += len(recs)
            assessed = sum(1 for it in store.items.values() if it.year == year)
            years.append(YearCoverage(year=year, listed=n_year, assessed=min(assessed, n_year)))
        year -= 1
    log.info(
        "Variant analysis (partitioned BLAST): %d records listed, %d processed this run in %d "
        "search(es)", total, processed, n_searches,
    )  # fmt: skip
    if n_searches > cfg.search.max_searches_warn:
        log.warning(
            "%d BLAST searches in one run: NCBI asks for more than %d to be run at weekends or "
            "between 21:00 and 05:00 US Eastern time.", n_searches, cfg.search.max_searches_warn,
        )  # fmt: skip
    return years, total, processed, 0, []


def _search(
    recs: list[AssemblyRecord],
    amplicon: str,
    cfg: Config,
    runner: BlastRunner,
    jobs: JobStore,
    fetcher: WindowFetcher,
    store: RegionStore,
) -> None:
    """One BLAST of the amplicon against an explicit accession list; store every record."""
    by_acc = {r.accession: r for r in recs}
    entrez = "(" + " OR ".join(f"{a}[ACCN]" for a in by_acc) + ")"
    fasta = f">amplicon\n{amplicon}\n"
    params = blast.build_put_params(cfg, fasta, entrez)
    params.update(WORD_SIZE="11", EXPECT="10", HITLIST_SIZE=str(max(500, 5 * len(recs))))
    key = blast.request_key(params)
    job = jobs.jobs.get(key) or Job(
        key=key, tier="variants", label=f"variants {recs[0].accession}..", taxids=[],
        entrez_query=entrez, params={k: val for k, val in params.items() if k != "QUERY"},
        query_labels=["amplicon"],
    )  # fmt: skip
    jobs.upsert(job)
    parsed = parse_blast_json(runner.run(job, fasta, params), ["amplicon"])
    hsps: dict[str, list[tuple[Hsp, int | None, str]]] = {}
    for hit in parsed.queries["amplicon"].hits:
        for d in hit.descriptions:
            if d.accession_version in by_acc:  # hits outside the list are leaks: ignored
                hsps.setdefault(d.accession_version, []).extend(
                    (h, hit.length, d.title or "") for h in hit.hsps
                )
    missed: list[AssemblyRecord] = []
    for acc, rec in by_acc.items():
        loci: list[Locus] = []
        found = sorted(hsps.get(acc, []), key=lambda x: -x[0].bit_score)
        title = found[0][2] if found else ""
        for h, length, _title in found:
            locus = _locus(acc, h, length, amplicon, cfg, fetcher)
            if locus is not None and not any(
                abs(locus.start - lc.start) <= INDEL_TOLERANCE for lc in loci
            ):
                loci.append(locus)
        if loci:
            store.add(rec, loci, {acc: title}, found_by="blast")
        else:
            missed.append(rec)
    _direct_scan(missed, amplicon, cfg, fetcher, store)


def _direct_scan(
    recs: list[AssemblyRecord],
    amplicon: str,
    cfg: Config,
    fetcher: WindowFetcher,
    store: RegionStore,
) -> None:
    """Records BLAST did not hit: fetch them and scan for the amplicon before calling them absent.

    Found live (CDC N1, 2026-09-23): all 300 of the newest SARS-CoV-2 records came back without a
    hit, most likely because they were not yet in the BLAST database. Records longer than
    ``direct_scan_max_length`` are not fetched and stay "not found" (not checked directly).
    """
    v = cfg.variants
    small = [r for r in recs if 0 < r.total_length <= v.direct_scan_max_length]
    fetched: dict[str, tuple[str, str]] = {}
    for i in range(0, len(small), v.direct_scan_batch):
        chunk = small[i : i + v.direct_scan_batch]
        try:
            text = fetcher.eutils.fetch_fasta_many([r.accession for r in chunk])
        except NcbiError as exc:
            log.warning("Could not fetch %d records for a direct scan: %s", len(chunk), exc)
            continue
        fetched.update(parse_fasta_records(text))
    for rec in recs:
        got = fetched.get(rec.accession)
        if got is None:
            store.add(rec, [], {rec.accession: ""}, direct_checked=False)
            continue
        desc, seq = got
        loci = find_loci({rec.accession: seq}, amplicon, seed_length=v.seed_length,
                         seed_step=v.seed_step, flank=v.flank_nt)  # fmt: skip
        store.add(rec, loci, {rec.accession: desc}, found_by="direct_scan", direct_checked=True)


def _locus(
    acc: str, h: Hsp, length: int | None, amplicon: str, cfg: Config, fetcher: WindowFetcher
) -> Locus | None:
    n = len(amplicon)
    lo, hi = min(h.hit_from, h.hit_to), max(h.hit_from, h.hit_to)
    strand = "+" if h.hit_strand.lower().startswith("plus") else "-"
    if h.query_from == 1 and h.query_to == n and h.hseq:
        region = h.hseq.replace("-", "").upper()  # already in the amplicon's orientation
        return Locus(contig=acc, strand=strand, start=lo, end=hi, region=region, offset=0,
                     n_seeds=0, truncated=False)  # fmt: skip
    # partial hit: fetch the record around it and locate the whole amplicon there
    pad = n + cfg.variants.flank_nt + INDEL_TOLERANCE
    w_lo, w_hi = max(1, lo - pad), hi + pad
    if length:
        w_hi = min(w_hi, length)
    window = fetcher.get(acc, w_lo, w_hi)  # None (counted, logged) when the fetch failed
    if not window:
        return None
    v = cfg.variants
    found = find_loci({acc: window.upper()}, amplicon, seed_length=v.seed_length,
                      seed_step=v.seed_step, flank=v.flank_nt)  # fmt: skip
    if not found:
        return None
    lc = found[0]
    return Locus(contig=acc, strand=lc.strand, start=lc.start + w_lo - 1, end=lc.end + w_lo - 1,
                 region=lc.region, offset=lc.offset, n_seeds=lc.n_seeds,
                 truncated=lc.truncated)  # fmt: skip
