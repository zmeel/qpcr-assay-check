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
from .locate import find_loci
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
            loci = find_loci(
                {name: seq for name, (_d, seq) in records_.items()}, amplicon,
                seed_length=v.seed_length, seed_step=v.seed_step, flank=v.flank_nt,
            )  # fmt: skip
            store.add(rec, loci, {name: d for name, (d, _s) in records_.items()})
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
) -> tuple[list[SiteResult], int]:
    """One site per oligo per assembly (best complete copy); returns sites and contig breaks."""
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    memo: dict[tuple[str, str], realign.Alignment] = {}
    sites: list[SiteResult] = []
    contig_break = 0
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
            lo = locus.offset + start - 1 - SITE_PAD
            hi = locus.offset + end + SITE_PAD
            if lo < 0 or hi > len(locus.region):
                break
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
        if len(per_role) == len(ROLES):
            sites += per_role
        else:
            contig_break += 1
    return sites, contig_break


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
        f"{y.year}: {y.listed} assembl{'y' if y.listed == 1 else 'ies'} listed, "
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
            "Every genome assembly of the target in NCBI Datasets (current versions, one copy per "
            "GenBank/RefSeq pair), by release year; 'Population' is the number of assemblies "
            "listed for that year and 'Sample' the number assessed so far. Not a sample: any gap "
            "between the two is coverage still to be processed."
        ),
        verdict=verdict,
        rationale=rationale,
        limitations=[
            "Assemblies are grouped by NCBI release year, not by sample collection date.",
            "Only genome assemblies are covered; sequences submitted without an assembly (single "
            "genes, amplicons) are not part of NCBI Datasets' genome collection.",
        ],
    )


# ------------------------------------------------------------------ one call for the CLI
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
) -> ExhaustiveResult:
    """Collect new assemblies, then assess every stored one. Raises InputError / NcbiError."""
    taxon = assay.target.taxid
    if taxon is None:
        raise InputError("The exhaustive variant analysis needs the target's taxonomy ID.")
    amplicon, amp_source = reference_amplicon(assay, fetch_fasta)
    placed = oligo_sites(assay, amplicon, cfg.thresholds.amplicon.max_site_mismatches)
    v = cfg.variants
    store = RegionStore(store_path(cache_root, taxon, amplicon, v.flank_nt))
    years, total, processed, failed, _failed = collect(client, store, taxon, amplicon, cfg, now=now)
    if total == 0:
        raise InputError(
            f"NCBI Datasets lists no genome assemblies for taxon {taxon} with the configured "
            "filters, so there is nothing to analyse exhaustively."
        )
    items = current_items(store)
    sites, contig_break = assess(items, assay, amplicon, placed, cfg)
    not_found = [it for it in items if it.status == "not_found"]
    found_loci = [it.loci[0] for it in items if it.status == "found" and it.loci]
    known = [lc.on_plasmid for lc in found_loci if lc.on_plasmid is not None]
    on_plasmid = (sum(known) * 2 >= len(known)) if known else None
    with_plasmid = [it for it in not_found if it.plasmid_contigs]
    coverage = ExhaustiveCoverage(
        taxon=taxon,
        amplicon_length=len(amplicon),
        amplicon_source=amp_source,
        filters={"current_assemblies_only": v.current_assemblies_only,
                 "exclude_atypical": v.exclude_atypical, "one_copy_per_genbank_refseq_pair": True},
        listed_total=total,
        assessed_total=len(items),
        processed_this_run=processed,
        download_failed_this_run=failed,
        budget_per_run=v.max_assemblies_per_run,
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
    )  # fmt: skip
    inclusivity = exhaustive_inclusivity(sites, items, years, assay, cfg)
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
