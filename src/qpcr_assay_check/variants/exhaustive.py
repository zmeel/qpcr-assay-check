"""Exhaustive variant analysis: every genome assembly of the target, not BLAST's best hits.

1. The reference amplicon comes from the assay (``reference_amplicon``) or is cut out of the
   target's reference accession by the primers.
2. The target taxon's assemblies are listed in NCBI Datasets, one copy per GenBank/RefSeq pair,
   newest release year first. Assemblies already in the region store are skipped; the rest are
   downloaded in batches (at most ``max_assemblies_per_run`` per run), scanned for the amplicon
   (:mod:`.locate`) and discarded; only the region is stored (:mod:`.store`).
3. Every stored assembly is assessed: each oligo is re-aligned end to end in its expected window
   of the best copy of the region. The result feeds the existing variant tables and an
   exhaustive, per-release-year inclusivity.

Nothing here is a sample: coverage is counted per year (listed vs assessed) and reported, so an
unfinished first run of a very large species says exactly how far it got.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ..align import realign
from ..config import Config
from ..errors import InputError
from ..inclusivity.aggregate import _stats, _verdict
from ..inclusivity.models import InclusivityOligoResult, InclusivityResult
from ..models import Assay
from ..ncbi.http import NcbiError
from ..oligo import iupac
from ..oligo.amplicon import find_sites
from ..specificity.models import SiteResult
from ..specificity.sites import _result_fields
from .datasets import AssemblyRecord, DatasetsClient, parse_fasta, parse_fasta_records
from .locate import find_loci, find_masked
from .models import ExhaustiveCoverage, YearCoverage
from .store import RegionStore, StoredAssembly, StoredLocus, store_path

log = logging.getLogger(__name__)

ROLES = ("forward", "reverse", "probe")
SITE_PAD = 15  # bases around an oligo's expected site, to allow indels in the variant
EARLIEST_YEAR = 1980  # guard for the year walk; Datasets assemblies are far more recent


# ------------------------------------------------------------------ reference amplicon
def reference_amplicon(assay: Assay, fetch_fasta: Callable[[str], str]) -> tuple[str, str]:
    """``(amplicon, where it came from)``: the assay's own, or cut out of the target accession."""
    if assay.reference_amplicon:
        return assay.reference_amplicon.upper(), "assay reference_amplicon"
    acc = assay.target.accession
    if not acc:
        raise InputError(
            "The exhaustive variant analysis needs the reference amplicon: give the assay a "
            "'reference_amplicon' or a target 'accession' that contains both primers."
        )
    seqs = parse_fasta(fetch_fasta(acc))
    fwd, rev_rc = assay.forward.upper(), iupac.reverse_complement(assay.reverse.upper())
    for seq in seqs.values():
        for s in (seq, iupac.reverse_complement(seq)):
            i = s.find(fwd)
            j = s.find(rev_rc, i + 1) if i >= 0 else -1
            if i >= 0 and j >= 0:
                return s[i : j + len(rev_rc)], f"cut from {acc} by exact primer matches"
    raise InputError(
        f"Both primers were not found exactly (facing each other) in {acc}; give the assay a "
        "'reference_amplicon' so the variant analysis knows which region to look for."
    )


def oligo_sites(
    assay: Assay, amplicon: str, max_mismatches: int
) -> dict[str, tuple[str, int, int]]:
    """``role -> (strand, start, end)`` of each oligo in the reference amplicon (1-based)."""
    out: dict[str, tuple[str, int, int]] = {}
    for role in ROLES:
        hits = find_sites(amplicon, assay.oligos[role], role, max_mismatches=max_mismatches)
        if not hits:
            raise InputError(
                f"The {role} oligo was not found in the reference amplicon with at most "
                f"{max_mismatches} mismatch(es); the variant analysis cannot place it."
            )
        out[role] = (hits[0].strand, hits[0].start, hits[0].end)
    return out


# ------------------------------------------------------------------ collection
def collect(
    client: DatasetsClient,
    store: RegionStore,
    taxon: int,
    amplicon: str,
    cfg: Config,
    *,
    now: datetime | None = None,
) -> tuple[list[YearCoverage], int, int, int, list[str]]:
    """List, download and scan new assemblies; returns per-year coverage and run counters."""
    v = cfg.variants
    flt = {"current_only": v.current_assemblies_only, "exclude_atypical": v.exclude_atypical}
    total = client.count(taxon, **flt)
    budget = v.max_assemblies_per_run
    year = (now or datetime.now(UTC)).year
    years: list[YearCoverage] = []
    listed = processed = failed = 0
    failed_accessions: list[str] = []
    while listed < total and year >= EARLIEST_YEAR:
        n_year = client.count(taxon, first=f"{year}-01-01", last=f"{year}-12-31", **flt)
        if n_year:
            listed += n_year
            if processed < budget:
                pending: list[AssemblyRecord] = []
                for rec in client.year(taxon, year, **flt):
                    if store.done(rec.accession):
                        continue
                    pending.append(rec)
                    if processed + len(pending) >= budget:
                        break
                p, f, accs = _process(client, store, pending, amplicon, cfg)
                processed, failed = processed + p, failed + f
                failed_accessions += accs
            assessed = sum(1 for it in store.items.values() if it.year == year)
            years.append(YearCoverage(year=year, listed=n_year, assessed=min(assessed, n_year)))
        year -= 1
    log.info(
        "Variant analysis: %d assemblies listed, %d processed this run (%d failed downloads)",
        total, processed, failed,
    )  # fmt: skip
    return years, total, processed, failed, failed_accessions


def _process(
    client: DatasetsClient,
    store: RegionStore,
    records: list[AssemblyRecord],
    amplicon: str,
    cfg: Config,
) -> tuple[int, int, list[str]]:
    batch = cfg.ncbi.datasets_batch_size
    v = cfg.variants
    done = failed = 0
    failed_accessions: list[str] = []
    for i in range(0, len(records), batch):
        chunk = records[i : i + batch]
        try:
            genomes = client.download([r.accession for r in chunk])
        except NcbiError as exc:
            log.warning("Genome download failed for %d assemblies: %s", len(chunk), exc)
            genomes = {}
        for rec in chunk:
            fasta = genomes.get(rec.accession)
            if fasta is None:
                failed += 1
                failed_accessions.append(rec.accession)
                continue
            records_ = parse_fasta_records(fasta)
            contigs = {name: seq for name, (_d, seq) in records_.items()}
            kw = {"seed_length": v.seed_length, "seed_step": v.seed_step, "flank": v.flank_nt}
            loci = find_loci(contigs, amplicon, **kw)
            masked = [] if loci else find_masked(contigs, amplicon, **kw)
            store.add(rec, loci, {name: d for name, (d, _s) in records_.items()}, masked=masked)
            done += 1
        log.info("  %d / %d assemblies scanned", i + len(chunk), len(records))
    return done, failed, failed_accessions


# ------------------------------------------------------------------ assessment
def current_items(store: RegionStore) -> list[StoredAssembly]:
    """Stored assemblies, one per accession base (the highest version wins)."""
    best: dict[str, StoredAssembly] = {}
    for it in store.items.values():
        base = it.accession.partition(".")[0]
        cur = best.get(base)
        if cur is None or _version(it.accession) > _version(cur.accession):
            best[base] = it
    return sorted(best.values(), key=lambda it: (it.release_date, it.accession))


def _version(acc: str) -> int:
    tail = acc.rpartition(".")[2]
    return int(tail) if tail.isdigit() else 0


def assess(
    items: list[StoredAssembly],
    assay: Assay,
    amplicon: str,
    sites_in_amplicon: dict[str, tuple[str, int, int]],
    cfg: Config,
) -> tuple[list[SiteResult], int, list[str]]:
    """One site per oligo per assembly (best complete copy).

    Returns the sites, the number of assemblies whose region is cut by a contig end, and the
    accessions whose best copy has an N inside an oligo site (masked, not assessed).
    """
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    memo: dict[tuple[str, str], realign.Alignment] = {}
    sites: list[SiteResult] = []
    contig_break = 0
    masked_site: list[str] = []
    n = 0
    for it in items:
        if it.status != "found":
            continue
        locus = next((lc for lc in it.loci if not lc.truncated), None)
        if locus is None:
            contig_break += 1
            continue
        per_role = []
        for role in ROLES:
            strand, start, end = sites_in_amplicon[role]
            # the site +- SITE_PAD, clamped to the region (a full-length BLAST hit carries no
            # flanks); a site that itself runs off the region cannot be assessed
            if locus.offset + start - 1 < 0 or locus.offset + end > len(locus.region):
                break
            lo = max(0, locus.offset + start - 1 - SITE_PAD)
            hi = min(len(locus.region), locus.offset + end + SITE_PAD)
            window = locus.region[lo:hi]
            oriented = window if strand == "+" else iupac.reverse_complement(window)
            oligo = assay.oligos[role].upper()
            key = (oligo, oriented)
            if key not in memo:
                memo[key] = realign.align_semiglobal(oligo, oriented, scoring)
            aln = memo[key]
            rules = cfg.specificity.probe_site if role == "probe" else cfg.specificity.primer_site
            n += 1
            per_role.append(_site(it, locus, role, strand, lo, len(window), aln, rules, n))
        if len(per_role) != len(ROLES):
            contig_break += 1
        elif any("N" in s.s_aln.upper() for s in per_role):
            masked_site.append(it.accession)  # an N is neither a match nor a variant
        else:
            sites += per_role
    return sites, contig_break, masked_site


def _site(it: StoredAssembly, locus: StoredLocus, role: str, strand: str, lo: int, wlen: int,
          aln: realign.Alignment, rules, n: int) -> SiteResult:  # fmt: skip
    """A SiteResult on the assembly's contig (coordinates on the contig's forward strand)."""
    # indices in the region (sense orientation) covered by the aligned subject bases
    if strand == "+":
        r0, r1 = lo + aln.s_start, lo + aln.s_end - 1
    else:
        r0, r1 = lo + wlen - aln.s_end, lo + wlen - 1 - aln.s_start
    if locus.strand == "+":
        c0, c1 = locus.start + r0, locus.start + r1
    else:
        c0, c1 = locus.end - r1, locus.end - r0
    contig_orientation = "+" if (strand == "+") == (locus.strand == "+") else "-"
    m = realign.measure(aln.q_aln, aln.s_aln)
    return SiteResult(
        id=f"V{n}", tier="target", query=role, role=role,  # type: ignore[arg-type]
        oligo=aln.q_aln.replace("-", ""), accession=it.accession, taxid=it.taxid,
        organism=it.organism, title=f"{locus.contig} ({it.assembly_level})",
        orientation=contig_orientation,  # type: ignore[arg-type]
        subject_start=c0, subject_end=c1, source="realigned",
        **_result_fields(aln.q_aln, aln.s_aln, m, rules),
    )  # fmt: skip


def exhaustive_inclusivity(
    sites: list[SiteResult],
    items: list[StoredAssembly],
    years: list[YearCoverage],
    assay: Assay,
    cfg: Config,
    *,
    source: str = "datasets",
) -> InclusivityResult:
    """Per-release-year inclusivity over every assessed assembly (not a sample)."""
    year_of = {it.accession: it.year for it in items}
    listed = {y.year: y.listed for y in years}
    lookback = cfg.inclusivity.lookback_years
    shown = sorted(listed)[-lookback:] if listed else []
    oligos: list[InclusivityOligoResult] = []
    for role in ROLES:
        role_sites = [s for s in sites if s.role == role]
        windows = [
            _stats([s for s in role_sites if year_of.get(s.accession) == y], y, listed[y],
                   len(assay.oligos[role]))
            for y in shown
        ]  # fmt: skip
        oligos.append(InclusivityOligoResult(role=role, oligo=assay.oligos[role], windows=windows))
    verdict, rationale = _verdict(oligos, cfg.inclusivity)
    rationale += [
        f"{y.year}: {y.listed} "
        + (
            f"assembl{'y' if y.listed == 1 else 'ies'}"
            if source == "datasets"
            else f"record{'' if y.listed == 1 else 's'}"
        )
        + " listed, "
        f"{y.assessed} assessed so far; the rest follow on later runs."
        for y in sorted(years, key=lambda y: y.year)
        if y.year in shown and y.assessed < y.listed
    ]
    return InclusivityResult(
        tier_searched=True,
        exhaustive=True,
        target_taxid=assay.target.taxid,
        oligos=oligos,
        sample_scheme=(
            (
                "Every genome assembly of the target in NCBI Datasets (current versions, one copy "
                "per GenBank/RefSeq pair), by release year; 'Assemblies' is the number NCBI lists "
                "for that year"
            )
            if source == "datasets"
            else (
                "Every NCBI Nucleotide record of the target, by publication year; 'Assemblies' "
                "is the number of records ESearch lists for that year"
            )
        )
        + (
            " and 'With region' the number in which the target region was found and assessed. "
            "Not a sample: the gap between the two is explained below (region not found, cut by "
            "a contig end, or not processed yet)."
        ),
        verdict=verdict,
        rationale=rationale,
        limitations=(
            [
                "Assemblies are grouped by NCBI release year, not by sample collection date.",
                "Only genome assemblies are covered; sequences submitted without an assembly "
                "(single genes, amplicons) are not part of NCBI Datasets' genome collection.",
            ]
            if source == "datasets"
            else [
                "Records are grouped by NCBI publication year, not by sample collection date.",
                "Records that do not contain the target region (other genes, partial sequences) "
                "are counted as 'not found' and are not part of the per-year counts.",
            ]
        ),
    )


# ------------------------------------------------------------------ one call for the CLI
Collector = Callable[[RegionStore, int, str], tuple[list[YearCoverage], int, int, int, list[str]]]


@dataclass
class ExhaustiveResult:
    """Everything the exhaustive analysis hands to :func:`qpcr_assay_check.pipeline.evaluate`."""

    sites: list[SiteResult]
    coverage: ExhaustiveCoverage
    inclusivity: InclusivityResult
    release_dates: dict[str, str]


def run_exhaustive(
    assay: Assay,
    cfg: Config,
    client: DatasetsClient,
    cache_root: Path,
    fetch_fasta: Callable[[str], str],
    *,
    now: datetime | None = None,
    collector: Collector | None = None,
    source: str = "datasets",
) -> ExhaustiveResult:
    """Collect new assemblies (or Nucleotide records), then assess every stored one.

    ``collector`` replaces the NCBI Datasets collection (``source`` names it, e.g.
    ``blast_partitioned``); it receives the store, the taxon and the amplicon. Raises InputError
    or NcbiError.
    """
    taxon = assay.target.taxid
    if taxon is None:
        raise InputError("The exhaustive variant analysis needs the target's taxonomy ID.")
    amplicon, amp_source = reference_amplicon(assay, fetch_fasta)
    placed = oligo_sites(assay, amplicon, cfg.thresholds.amplicon.max_site_mismatches)
    v = cfg.variants
    store = RegionStore(store_path(cache_root, taxon, amplicon, v.flank_nt, source))
    if collector is None:
        years, total, processed, failed, _f = collect(client, store, taxon, amplicon, cfg, now=now)
    else:
        years, total, processed, failed, _f = collector(store, taxon, amplicon)
    if total == 0:
        what = (
            "genome assemblies in NCBI Datasets"
            if source == "datasets"
            else "Nucleotide records in NCBI"
        )
        raise InputError(
            f"There are no {what} for taxon {taxon} with the configured filters, so there is "
            "nothing to analyse exhaustively."
        )
    items = current_items(store)
    sites, contig_break, masked_site = assess(items, assay, amplicon, placed, cfg)
    not_found = [it for it in items if it.status == "not_found"]
    found_loci = [it.loci[0] for it in items if it.status == "found" and it.loci]
    known = [lc.on_plasmid for lc in found_loci if lc.on_plasmid is not None]
    on_plasmid = (sum(known) * 2 >= len(known)) if known else None
    with_plasmid = [it for it in not_found if it.plasmid_contigs]
    coverage = ExhaustiveCoverage(
        taxon=taxon,
        amplicon_length=len(amplicon),
        amplicon_source=amp_source,
        source=source,
        filters=(
            {"current_assemblies_only": v.current_assemblies_only,
             "exclude_atypical": v.exclude_atypical, "one_copy_per_genbank_refseq_pair": True}
            if source == "datasets"
            else {"nucleotide_query": v.nucleotide_query or ""}
        ),
        listed_total=total,
        assessed_total=len(items),
        processed_this_run=processed,
        download_failed_this_run=failed,
        budget_per_run=(
            v.max_assemblies_per_run if source == "datasets" else v.blast_max_records_per_run
        ),
        found=len(sites) // len(ROLES),
        not_found=len(not_found),
        contig_break=contig_break,
        multi_copy=sum(1 for it in items if it.n_loci > 1),
        years=years,
        listed_at=(now or datetime.now(UTC)).isoformat(timespec="seconds"),
        not_found_examples=[it.accession for it in not_found[:20]],
        target_on_plasmid=on_plasmid,
        not_found_without_plasmid=sum(1 for it in not_found if it.plasmid_contigs == 0),
        not_found_with_plasmid=len(with_plasmid),
        not_found_with_plasmid_examples=[it.accession for it in with_plasmid[:20]],
        plasmid_header_examples=[x for it in items for x in it.plasmid_examples][:5],
        plasmid_info_recorded=any(it.plasmid_contigs is not None for it in items),
        masked=sum(1 for it in items if it.status == "masked") + len(masked_site),
        masked_examples=(
            [it.accession for it in items if it.status == "masked"] + masked_site
        )[:20],
        found_by_direct_scan=sum(
            1 for it in items if it.found_by == "direct_scan" and it.status == "found"
        ),
        not_checked_directly=sum(
            1 for it in not_found if it.assembly_level == "Nucleotide record"
            and it.direct_checked is False
        ),
    )  # fmt: skip
    inclusivity = exhaustive_inclusivity(sites, items, years, assay, cfg, source=source)
    missing = coverage.not_found + coverage.contig_break + coverage.masked
    if missing:
        inclusivity.rationale.append(
            f"{missing} of {len(items)} assessed "
            f"{'assemblies' if source == 'datasets' else 'records'} are not in the counts above: "
            f"the target region was not found in {coverage.not_found}, was hidden by N in "
            f"{coverage.masked} and was cut by a contig or record end in {coverage.contig_break} "
            "(see the Variant summary). Per year, 'Assemblies' minus 'With region' is that gap."
        )
    if coverage.target_on_plasmid and coverage.not_found_with_plasmid:
        inclusivity.rationale.append(
            f"{coverage.not_found_with_plasmid} assembl"
            f"{'y carries' if coverage.not_found_with_plasmid == 1 else 'ies carry'} plasmid "
            "sequence but not the target region; they are not in the counts above. If the region "
            "is really deleted there (not just an incomplete plasmid assembly), the assay would "
            "miss those strains."
        )
    return ExhaustiveResult(
        sites=sites,
        coverage=coverage,
        inclusivity=inclusivity,
        release_dates={it.accession: it.release_date for it in items},
    )
