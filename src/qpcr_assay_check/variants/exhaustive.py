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

import json
import logging
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from ..align import realign
from ..config import Config, SiteRules
from ..errors import InputError
from ..inclusivity.aggregate import _stats
from ..inclusivity.models import (
    CollectionAxis,
    DistinctPatterns,
    FragmentYear,
    InclusivityOligoResult,
    InclusivityResult,
    fragment_window,
    status_years,
)
from ..models import Assay, Channel, Oligo
from ..ncbi.cache import content_key
from ..ncbi.http import NcbiError
from ..oligo import grade, iupac
from ..oligo.amplicon import find_sites
from ..specificity.models import SiteResult
from ..specificity.sites import _result_fields
from ..verdict import STATUS_LABEL, Verdict
from .chain import CopyRule, Reference, context_from, copies_of, overlap
from .collection import collection_year
from .datasets import AssemblyRecord, DatasetsClient, parse_fasta, parse_fasta_records
from .genomestore import (
    GenomeRecord,
    GenomeStore,
    StoredCopy,
    scan_genome,
    scan_settings,
    store_file,
    store_key,
)
from .models import (
    ChannelCoverageRow,
    ChannelResult,
    CopyCoverage,
    CutReason,
    EscapeReason,
    EscapeRow,
    ExhaustiveCoverage,
    LevelCoverage,
    OligoCoverageRow,
    RunLengthBreakdown,
    YearCoverage,
)
from .store import StoredAssembly, StoredLocus

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
    for f in assay.forward:  # any forward/reverse pair of the mix
        for r in assay.reverse:
            fwd, rev_rc = f.sequence.upper(), iupac.reverse_complement(r.sequence.upper())
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


def locus_references(
    assay: Assay, amplicon: str, fetch_fasta: Callable[[str], str], cache_dir: Path
) -> list[Reference]:
    """The first locus's reference fragments, each with the sequence either side of the first
    fragment's best copy in the locus's context accession (overhaul step 5).

    The context is fetched once and kept in ``cache_dir``. A fetch that fails raises NcbiError
    instead of going on without context: the store key includes the context, so a run without
    it would set every stored genome aside and scan them all again.
    """
    lc = assay.loci[0]
    fragments = [amplicon] + [r.sequence.upper() for r in lc.references[1:]]
    left = right = ""
    acc = lc.context_accession
    if acc:
        cache = Path(cache_dir) / f"context-{content_key([acc, amplicon])[:16]}.json"
        try:
            left, right = json.loads(cache.read_text(encoding="utf-8"))["flanks"]
        except (OSError, ValueError, KeyError):
            try:
                found = context_from(parse_fasta(fetch_fasta(acc)), amplicon)
            except NcbiError as exc:
                raise NcbiError(
                    f"Could not fetch {acc} for the sequence either side of the reference "
                    f"fragment ({exc}); try again later."
                ) from exc
            if found is None:
                log.warning("No whole copy of the reference fragment in %s: no context", acc)
            else:
                left, right = found.left, found.right
                log.info("Context from %s (%s at %d; %d anchored bases, identity %s)", acc,
                         found.contig, found.start, found.anchored, found.identity)  # fmt: skip
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"accession": acc, "flanks": [left, right]}), "utf-8")
    return [Reference(f, left, right) for f in fragments]


def copy_rule(cfg: Config) -> CopyRule:
    v = cfg.variants
    return CopyRule(min_anchored=v.min_anchored_bases, min_context=v.min_context_bases,
                    min_identity=v.min_copy_identity,
                    min_identity_anchored=v.min_identity_anchored_bases)  # fmt: skip


def open_genome_store(
    assay: Assay, cfg: Config, cache_root: Path, references: list[Reference], source: str
) -> GenomeStore:
    """The first locus's store: keyed by its references (with context), the scan settings, the
    taxon and the source; a store with another key is set aside and scanned again."""
    taxon = assay.loci[0].scan_taxid or assay.target.taxid
    if taxon is None:
        raise InputError("The exhaustive variant analysis needs the target's taxonomy ID.")
    key = store_key(references, scan_settings(cfg), taxon=taxon, source=source,
                    excluded=assay.target.excluded_taxids)  # fmt: skip
    return GenomeStore(store_file(cache_root, key), key)


def as_items(
    records: list[GenomeRecord], rule: CopyRule, dates: dict[str, str] | None = None
) -> tuple[list[StoredAssembly], list[str], list[str], list[str]]:
    """The stored genomes as the assessment reads them, with the copy rule applied: the items,
    the genomes with only related regions (no copy, but fragment bases anchored), those with
    related regions next to copies, and those without a copy or a related region whose flanks
    were found (``min_context`` bases on a side): the region is there, but the fragment could
    not be located (advisor subagent, 2026-09-30). ``dates``: collection dates by accession
    (the store's side file); a genome without an entry has none read yet."""
    dates = dates or {}
    items: list[StoredAssembly] = []
    related: list[str] = []
    beside: list[str] = []
    flanked: list[str] = []
    for rec in records:
        cands = [c.candidate() for c in rec.copies]
        chosen = copies_of(cands, rule)
        kept = {id(c) for c in chosen}
        copies = [sc for sc, c in zip(rec.copies, cands, strict=True) if id(c) in kept]
        # related regions: fragment bases anchored, not a copy, not at a copy's place (one
        # region found twice is not two), and never a fallback chain (code review 2026-09-30)
        others = [
            sc for sc, c in zip(rec.copies, cands, strict=True)
            if id(c) not in kept and c.anchored > 0 and not c.fallback
            and not any(overlap(c, k) for k in chosen)
        ]  # fmt: skip
        if not copies and others:
            related.append(rec.accession)
        elif copies and others:
            beside.append(rec.accession)
        elif not copies and any(
            max(c.context_left, c.context_right) >= rule.min_context for c in rec.copies
        ):
            flanked.append(rec.accession)
        copies.sort(key=lambda c: (-c.anchored, -(c.identity or 0.0)))
        items.append(StoredAssembly(
            accession=rec.accession, release_date=rec.release_date, organism=rec.organism,
            taxid=rec.taxid, assembly_level=rec.assembly_level,
            status="found" if copies else "not_found", n_loci=len(copies),
            loci=[_as_locus(c) for c in copies], n_contigs=rec.n_sequences,
            plasmid_contigs=len(rec.plasmids), plasmid_examples=rec.plasmids[:3],
            found_by=rec.found_by if copies else None, direct_checked=rec.direct_checked,
            collection_date=dates.get(rec.accession),
        ))  # fmt: skip
    return items, related, beside, flanked


def _as_locus(c: StoredCopy) -> StoredLocus:
    """A stored copy as a region with its anchors (region indices), in forward coordinates."""
    r0, r1 = c.region_start, c.region_start + len(c.region)
    start, end = (r0 + 1, r1) if c.strand == "+" else (c.contig_length - r1 + 1,
                                                      c.contig_length - r0)  # fmt: skip
    return StoredLocus(
        contig=c.contig, strand=c.strand, start=start, end=end, region=c.region,
        offset=c.start - r0, n_seeds=c.anchored, truncated=c.cut,
        on_plasmid=None if c.molecule is None else c.molecule == "Plasmid", ref=c.ref,
        identity=c.identity, anchors=[(f, s - r0, n) for f, s, n in c.anchors],
        fallback=c.fallback,
    )  # fmt: skip


def fragment_not_assembled(items: list[StoredAssembly]) -> tuple[list[StoredAssembly], list[str]]:
    """Genomes whose every copy is cut by a contig end with no fragment base in an exact block:
    only the sequence beside the fragment reaches the contig end, so the fragment itself is not
    in the assembly. They count as "region not found", not as undetermined (user, 2026-10-02,
    after the Legionella breakdown: 161 of 4,441 cut genomes)."""
    out: list[StoredAssembly] = []
    moved: list[str] = []
    for it in items:
        if (
            it.status == "found"
            and it.loci
            and all(lc.truncated and lc.n_seeds == 0 for lc in it.loci)
        ):
            moved.append(it.accession)
            it = it.model_copy(update={"status": "not_found", "loci": [], "n_loci": 0,
                                       "found_by": None})  # fmt: skip
        out.append(it)
    return out, moved


def latest(records: dict[str, GenomeRecord]) -> list[GenomeRecord]:
    """One record per accession base (the highest version wins), oldest release first."""
    best: dict[str, GenomeRecord] = {}
    for rec in records.values():
        base = rec.accession.partition(".")[0]
        cur = best.get(base)
        if cur is None or _version(rec.accession) > _version(cur.accession):
            best[base] = rec
    return sorted(best.values(), key=lambda r: (r.release_date, r.accession))


def oligo_sites(
    assay: Assay, amplicon: str, max_mismatches: int
) -> dict[str, tuple[str, int, int]]:
    """``role -> (strand, start, end)`` where each role binds in the reference amplicon (1-based).

    With several oligos for a role (alternatives in one mix) the window spans every one that fits
    the reference; one meant for another lineage may not fit, and is aligned in the same window.
    """
    out: dict[str, tuple[str, int, int]] = {}
    for role in ROLES:
        placed = []
        for o in assay.by_role(role):
            hits = find_sites(amplicon, o.sequence, o.name, max_mismatches=max_mismatches)
            if hits:
                placed.append(hits[0])
        if not placed:
            names = ", ".join(o.name for o in assay.by_role(role))
            raise InputError(
                f"No {role} oligo ({names}) was found in the reference amplicon with at most "
                f"{max_mismatches} mismatch(es); the variant analysis cannot place it."
            )
        strand = placed[0].strand
        same = [h for h in placed if h.strand == strand]
        out[role] = (strand, min(h.start for h in same), max(h.end for h in same))
    return out


# ------------------------------------------------------------------ collection
def collect(
    client: DatasetsClient,
    store: GenomeStore,
    taxon: int,
    references: list[Reference],
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
            pending: list[AssemblyRecord] = []
            if processed < budget:
                dates: dict[str, str] = {}
                for rec in client.year(taxon, year, **flt):
                    dates[rec.accession] = rec.collection_date
                    if store.done(rec.accession):
                        continue
                    pending.append(rec)
                    if processed + len(pending) >= budget:
                        break
                store.note_dates(dates)
                stored = sum(1 for r in store.items.values() if r.year == year)
                log.info(
                    "%d: %d assemblies listed, %d already stored, %d to scan in this run%s",
                    year, n_year, stored, len(pending),
                    " (the per-run maximum is reached; the rest follow on later runs)"
                    if processed + len(pending) >= budget else "",
                )  # fmt: skip
                p, f, accs = _process(client, store, pending, references, cfg)
                processed, failed = processed + p, failed + f
                failed_accessions += accs
            assessed = sum(1 for r in store.items.values() if r.year == year)
            unavailable = sum(1 for r in pending if store.unavailable(r.accession))
            years.append(YearCoverage(year=year, listed=n_year, assessed=min(assessed, n_year),
                                      unavailable=unavailable))  # fmt: skip
        year -= 1
    log.info(
        "Variant analysis: %d assemblies listed, %d processed this run (%d failed downloads)",
        total, processed, failed,
    )  # fmt: skip
    return years, total, processed, failed, failed_accessions


def _process(
    client: DatasetsClient,
    store: GenomeStore,
    records: list[AssemblyRecord],
    references: list[Reference],
    cfg: Config,
) -> tuple[int, int, list[str]]:
    """Download in batches, scan each genome, store it; a failed batch is tried again in
    halves, down to single assemblies, so one bad assembly does not fail 99 others."""
    batch = cfg.ncbi.datasets_batch_size
    settings = scan_settings(cfg)
    done = failed = 0
    failed_accessions: list[str] = []
    for i in range(0, len(records), batch):
        chunk = records[i : i + batch]
        for rec, fasta, reason in _download(client, chunk):
            if fasta is None:
                failed += 1
                failed_accessions.append(rec.accession)
                store.record_failure(rec.accession, reason)
                continue
            records_ = parse_fasta_records(fasta)
            roles = None
            if len(records_) > 1:  # a single sequence has no plasmid to find
                try:
                    roles = client.sequence_roles(rec.accession)
                except NcbiError as exc:
                    log.warning("No sequence report for %s (%s); FASTA descriptions are used",
                                rec.accession, exc)  # fmt: skip
            store.add(scan_genome(rec, records_, references, settings, roles))
            done += 1
        log.info("  %d / %d assemblies scanned in this run", i + len(chunk), len(records))
    return done, failed, failed_accessions


def _download(
    client: DatasetsClient, chunk: list[AssemblyRecord]
) -> list[tuple[AssemblyRecord, str | None, str]]:
    """``(record, FASTA or None, failure reason)`` for each assembly of ``chunk``."""
    try:
        genomes = client.download([r.accession for r in chunk])
    except NcbiError as exc:
        if len(chunk) == 1:
            return [(chunk[0], None, str(exc))]
        log.warning("Genome download failed for %d assemblies (%s); retrying in halves",
                    len(chunk), exc)  # fmt: skip
        half = len(chunk) // 2
        return _download(client, chunk[:half]) + _download(client, chunk[half:])
    return [(r, genomes.get(r.accession), "not in the download") for r in chunk]


# ------------------------------------------------------------------ assessment
def _version(acc: str) -> int:
    tail = acc.rpartition(".")[2]
    return int(tail) if tail.isdigit() else 0


@dataclass
class GenomeCall:
    """One genome's best-binding copy, and what every oligo does on it."""

    accession: str
    n_copies: int
    n_detectable: int
    best_is_first: bool
    n_detectable_other_rule: int  # copies detectable under the other homopolymer-bulge rule
    oligo_good: dict[str, bool]  # oligo name -> detectable on the best copy
    role_good: dict[str, bool]
    role_state: dict[str, str] = field(default_factory=dict)  # ok | undetermined | fail
    assembly_level: str = ""
    run_variants: list[str] = field(default_factory=list)  # "role: label" in any copy
    run_on_best: bool = False  # the best copy carries a run-length variant
    run_mixed: bool = False  # copies disagree: some read the oligo's run length at that site
    n_truncated: int = 0  # stored copies cut by a contig end (not assessed)
    n_contigs: int | None = None  # sequences in the assembly
    signature: tuple = ()  # the best copy's three genome sites (role, subject alignment)
    unassembled: bool = False  # see mark_unassembled
    from_parts: bool = False  # judged from sites on copies cut by a contig end (_assess_parts)
    channel_state: dict[str, str] = field(default_factory=dict)  # channel -> ok|undetermined|fail
    escape_kind: str = ""  # why the best copy fails, when it does (see escape_reason)
    escape_detail: str = ""

    @property
    def undetermined(self) -> bool:
        """No detectable copy, but no failing role either: only sites without a published basis
        (e.g. a mismatch in an MGB probe); counted neither as detected nor as an escape."""
        states = set(self.role_state.values())
        return self.n_detectable == 0 and "fail" not in states and "undetermined" in states


class GenomeOutcome(StrEnum):
    """What one assessed genome counts as (overhaul step 2: one place decides it)."""

    DETECTED = "detected"
    NOT_DETECTED = "not detected"  # an escape: the region is there, no copy is detectable
    UNDETERMINED = "undetermined"  # only sites without a published basis (rules R6, R9)
    UNASSEMBLED = "possibly unassembled"  # see mark_unassembled
    FROM_PARTS = "detectable from parts"  # cut copies only, not counted (judge_from_parts)


def genome_outcome(c: GenomeCall) -> GenomeOutcome:
    """The one precedence every count uses: parts (not counted), detected, undetermined,
    possibly unassembled, not detected."""
    if c.from_parts and c.n_detectable == 0:
        return GenomeOutcome.FROM_PARTS
    if c.n_detectable > 0 or (c.role_good and all(c.role_good.values())):
        return GenomeOutcome.DETECTED
    if c.undetermined:
        return GenomeOutcome.UNDETERMINED
    if c.unassembled:
        return GenomeOutcome.UNASSEMBLED
    return GenomeOutcome.NOT_DETECTED


def detectable(s: SiteResult, bulges: bool = False) -> bool:
    """Graded class perfect or tolerated (docs/MISMATCH_CLASSES.md); for an ungraded site the
    earlier rule: at most 1 mismatch, no gap, no mismatch in the last 5 nt.

    ``bulges``: also accept a site that differs only by the length of a single-base run (a
    labelled homopolymer bulge without any mismatch); strict (False) by default.
    """
    if s.grade is not None:
        if s.grade in grade.DETECTABLE:
            return True
        # a labelled run-length variant (primer: class R5b at risk or likely failure; probe:
        # indeterminate) counts as detectable only under the lenient setting
        return bulges and bool(s.note) and s.n_mismatch == 0
    if s.n_gap == 0:
        return s.n_mismatch <= 1 and s.mismatches_last5 == 0
    return bulges and bool(s.note) and s.n_mismatch == 0


def undetermined(s: SiteResult) -> bool:
    """No published basis either way: a mismatch in an MGB probe (rule R9) or an ambiguity code
    in the genome in the last 5 nt (R6); counted neither as detected nor as an escape (user
    decision 2026-09-25). Gaps are not: an unexplained gap near a primer's 3' end is often how
    the aligner writes two mismatches, so it keeps counting as not detected; homopolymer bulges
    follow ``homopolymer_bulges_detectable``."""
    return s.grade == grade.INDETERMINATE and s.grade_rule in grade.UNDETERMINED_RULES


def site_state(s: SiteResult, bulges: bool = False) -> str:
    """ok (detectable) | undetermined | fail."""
    if detectable(s, bulges):
        return "ok"
    return "undetermined" if undetermined(s) else "fail"


_STATE_RANK = {"ok": 0, "undetermined": 1, "fail": 2}


def _closeness_key(s: SiteResult, bulges: bool = False) -> tuple[int, int, int]:
    return (_STATE_RANK[site_state(s, bulges)], s.n_mismatch + s.n_gap, -s.clean_3prime_nt)


def assess(
    items: list[StoredAssembly],
    assay: Assay,
    amplicon: str,
    sites_in_amplicon: dict[str, tuple[str, int, int]] | list[dict[str, tuple[str, int, int]]],
    cfg: Config,
    *,
    calls: list[GenomeCall] | None = None,
    cut: list[str] | None = None,
    cut_kinds: dict[str, tuple[str, str]] | None = None,
) -> tuple[list[SiteResult], int, list[str]]:
    """One site per role per genome, from the copy of the region the assay binds best.

    Every stored copy is assessed with every alternative oligo of each role (the best one of a
    role binds). A copy is ranked by how many roles are detectable there, then by total
    mismatches and gaps; the genome is judged by its best copy, as a PCR needs only one copy it
    can amplify. ``sites_in_amplicon`` gives the oligo windows per reference amplicon (a locus
    records which reference found it). ``calls``, if given, collects each genome's
    :class:`GenomeCall` (copies, per-oligo coverage). The items' copies are already chosen by
    the copy rule (:func:`as_items`). Returns the sites, the number of genomes
    whose only copies are cut by a contig end, and the genomes whose best copy has an N in an
    oligo site (masked, not assessed). ``cut_kinds``, if given, collects why each genome in
    ``cut`` has no judged site (:func:`cut_kind`).
    """
    per_ref = sites_in_amplicon if isinstance(sites_in_amplicon, list) else [sites_in_amplicon]
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    memo: dict[tuple[str, str], tuple[realign.Alignment, str]] = {}
    channel_rule = cfg.variants.probe_channels
    bulges = cfg.variants.homopolymer_bulges_detectable
    parts_rule = cfg.variants.judge_from_parts
    sites: list[SiteResult] = []
    contig_break = 0
    masked_site: list[str] = []
    n = 0
    for it in items:
        if it.status != "found":
            continue
        copies = []
        for locus in (lc for lc in it.loci if not lc.truncated):
            windows = per_ref[locus.ref] if locus.ref < len(per_ref) else per_ref[0]
            copy = _assess_copy(it, locus, assay, windows, cfg, scoring, memo, channel_rule, bulges)
            if copy is not None:
                copies.append(copy)
        best_i = (
            min(range(len(copies)), key=lambda i: _copy_key(copies[i][0], bulges)) if copies else 0
        )
        best_ok = bool(copies) and all(roles_ok(copies[best_i][0], bulges).values())
        parts = None
        if parts_rule != "off" and not best_ok and any(lc.truncated for lc in it.loci):
            parts = _assess_parts(it, per_ref, assay, cfg, scoring, memo, channel_rule, bulges)
            if parts is not None and not all(roles_ok(parts[0], bulges).values()):
                parts = None  # only a detectable judgement from parts replaces anything
        if not copies and parts is None:
            contig_break += 1
            if cut is not None:
                cut.append(it.accession)
            if cut_kinds is not None:
                cut_kinds[it.accession] = cut_kind(
                    it, per_ref, assay, cfg, scoring, memo, channel_rule, bulges
                )
            continue
        chosen, all_sites = parts if parts is not None else copies[best_i]
        if any("N" in s.s_aln.upper() for s in chosen.values()):
            masked_site.append(it.accession)  # an N is neither a match nor a variant
            continue
        channels = _channel_sites(assay, all_sites)
        for role in ROLES:
            n += 1
            update: dict[str, Any] = {"id": f"V{n}"}
            if role == "probe" and channels:
                update["channel_sites"] = channels
            sites.append(chosen[role].model_copy(update=update))
        if calls is not None:
            # The same count under the other homopolymer-bulge rule, for the bracketing figure
            # (bulge_alternative): the copies, and the judgement from parts that genome would
            # get under that rule. Without the parts term the alternative drops every genome
            # counted from parts and can fall below the headline, which is impossible over one
            # cohort (user decision 2026-10-07, option 2 of open/bulge-alternative-from-parts).
            n_other = sum(
                all(
                    roles_ok(
                        {r: _role_site(assay, r, a, channel_rule, not bulges) for r in ROLES},
                        not bulges,
                    ).values()
                )
                for _c, a in copies
            )
            parts_other = None
            if parts_rule != "off" and not n_other and any(lc.truncated for lc in it.loci):
                parts_other = _assess_parts(
                    it, per_ref, assay, cfg, scoring, memo, channel_rule, not bulges
                )
                if parts_other is not None and not all(
                    roles_ok(parts_other[0], not bulges).values()
                ):
                    parts_other = None  # as above: only a detectable judgement counts
            calls.append(
                GenomeCall(
                    accession=it.accession,
                    n_copies=len(copies),
                    n_detectable=sum(all(roles_ok(c, bulges).values()) for c, _a in copies)
                    + (parts is not None and parts_rule == "detectable"),
                    from_parts=parts is not None,
                    best_is_first=best_i == 0,
                    n_detectable_other_rule=n_other
                    + (parts_other is not None and parts_rule == "detectable"),
                    oligo_good={name: detectable(x, bulges) for name, x in all_sites.items()},
                    role_good=roles_ok(chosen, bulges),
                    role_state=roles_state(chosen, bulges),
                    assembly_level=it.assembly_level,
                    **_run_length_fields([c for c, _a in copies], chosen),
                    n_truncated=sum(1 for lc in it.loci if lc.truncated),
                    n_contigs=it.n_contigs,
                    # the genome's sites only, not which alternative oligo was chosen, as
                    # the whole-fragment rows group them
                    signature=tuple((r, chosen[r].s_aln) for r in ROLES),
                    channel_state=_channel_states(
                        assay, copies + ([parts] if parts is not None else []), bulges
                    ),
                )
            )
            call = calls[-1]
            call.escape_kind, call.escape_detail = escape_reason(
                chosen, call.role_state, bulges,
                rescued_by_bulges=not bulges and call.n_detectable_other_rule > 0,
            )  # fmt: skip
    return sites, contig_break, masked_site


ESCAPE_KINDS = {
    "run_length": "single-base run length only: detectable if homopolymer bulges are tolerated",
    "gap": "a gap in a site's alignment (an insertion or deletion; near a 3' end often how the "
    "aligner writes two mismatches)",
    "mismatch": "mismatches",
    "pair": "mismatches in both primers together (rule R8)",
}


def _site_reason(role: str, s: SiteResult) -> tuple[str, str]:
    cls = (s.grade or "not detectable").replace("_", " ")
    who = role if s.query == role else f"{role} {s.query}"
    if s.note and s.n_mismatch == 0:
        return "run_length", f"{who}: {cls}, {s.note}"
    parts = [f"{s.n_mismatch} mismatch(es)"]
    if s.n_gap:
        parts.append(f"{s.n_gap} gap(s)")
    if s.mismatches_last5:
        parts.append(f"{s.mismatches_last5} change(s) in the last 5 nt")
    return ("gap" if s.n_gap else "mismatch"), f"{who}: {cls} ({', '.join(parts)})"


def escape_reason(
    chosen: dict[str, SiteResult],
    state: dict[str, str],
    bulges: bool = False,
    rescued_by_bulges: bool = False,
) -> tuple[str, str]:
    """Why a genome's best copy fails (user request 2026-10-02): the kind and the failing sites.

    ``rescued_by_bulges``: some copy would be detectable if homopolymer bulges counted, so the
    genome fails only by the length of a single-base run (rule R5b, the strict setting). Other
    kinds, most telling first: an insertion or deletion, mismatches, then a primer pair that
    fails only together (rule R8: each primer alone would be detectable). ('', '') when no role
    fails."""
    kinds: list[str] = []
    details: list[str] = []
    for role in ROLES:
        if state.get(role) != "fail" or role not in chosen:
            continue
        s = chosen[role]
        if site_state(s, bulges) == "ok":  # detectable alone: failed with the other primer
            kinds.append("pair")
            who = role if s.query == role else f"{role} {s.query}"
            details.append(f"{who}: detectable alone, fails with the other primer (R8)")
            continue
        kind, detail = _site_reason(role, s)
        kinds.append(kind)
        details.append(detail)
    if not kinds:
        return "", ""
    if rescued_by_bulges:
        kind = "run_length"
    else:
        kind = next(k for k in ("gap", "mismatch", "pair", "run_length") if k in kinds)
    return kind, "; ".join(details)


def _channel_sites(assay: Assay, every: dict[str, SiteResult]) -> list[SiteResult]:
    """For probes in more than one reporter channel: the best site of each channel on this copy
    (for a genome detectable from parts: on its cut copies, possibly different ones), in reporter
    order (user, 2026-09-28: the tables showed only the best probe, so the second
    channel, e.g. an L. pneumophila probe next to a genus probe, was invisible)."""
    channels: dict[str, list[SiteResult]] = defaultdict(list)
    for o in assay.probe:
        if o.name in every:
            channels[o.reporter or "unspecified"].append(every[o.name])
    if len(channels) < 2:
        return []
    return [min(v, key=_closeness_key) for _r, v in sorted(channels.items())]


def _channel_states(
    assay: Assay,
    copies: list[tuple[dict[str, SiteResult], dict[str, SiteResult]]],
    bulges: bool,
) -> dict[str, str]:
    """Per channel its best state over the genome's copies: ok when a copy has both primers and
    one of the channel's probes detectable, undetermined when none fails but one has no
    published basis, else fail (overhaul step 5c)."""
    out: dict[str, str] = {}
    for ch in assay.channels:
        best: str | None = None
        for chosen, every in copies:
            probes = [every[p] for p in ch.probes if p in every]
            if not probes or "forward" not in chosen or "reverse" not in chosen:
                continue
            probe = min(probes, key=lambda x: _closeness_key(x, bulges))
            sites = {"forward": chosen["forward"], "reverse": chosen["reverse"], "probe": probe}
            states = set(roles_state(sites, bulges).values())
            st = "ok" if states == {"ok"} else ("fail" if "fail" in states else "undetermined")
            if best is None or _STATE_RANK[st] < _STATE_RANK[best]:
                best = st
        if best is not None:
            out[ch.name] = best
    return out


def _run_length_fields(copies: list[dict[str, SiteResult]],
                       best: dict[str, SiteResult]) -> dict[str, Any]:  # fmt: skip
    """Run-length variants (labelled homopolymer bulges) across a genome's copies."""
    labels: list[str] = []
    mixed = False
    for role in ROLES:
        variant = [c[role] for c in copies if c[role].note]
        if not variant:
            continue
        labels += sorted({f"{role}: {c.note}" for c in variant})
        mixed = mixed or any(not c[role].note and c[role].n_gap == 0 for c in copies)
    return {
        "run_variants": labels,
        "run_on_best": any(s.note for s in best.values()),
        "run_mixed": mixed,
    }


def roles_state(chosen: dict[str, SiteResult], bulges: bool = False) -> dict[str, str]:
    """Per role ok | undetermined | fail on this copy; both primers fail together when the pair
    has too many mismatches in total (rule R8, Lefever 2013; docs/MISMATCH_CLASSES.md)."""
    state = {r: site_state(s, bulges) for r, s in chosen.items()}
    fwd, rev = chosen.get("forward"), chosen.get("reverse")
    graded = fwd is not None and rev is not None and fwd.grade is not None
    if graded and grade.pair_fails(grade.tested_mismatches(fwd), grade.tested_mismatches(rev)):
        state["forward"] = state["reverse"] = "fail"
    return state


def roles_ok(chosen: dict[str, SiteResult], bulges: bool = False) -> dict[str, bool]:
    """Per role whether its site on this copy is detectable (see :func:`roles_state`)."""
    return {r: v == "ok" for r, v in roles_state(chosen, bulges).items()}


def _copy_key(chosen: dict[str, SiteResult], bulges: bool = False) -> tuple[int, int, int, int]:
    roles = list(chosen.values())
    states = list(roles_state(chosen, bulges).values())
    return (
        states.count("fail"),
        states.count("undetermined"),
        sum(x.n_mismatch + x.n_gap for x in roles),
        -sum(x.clean_3prime_nt for x in roles),
    )


def _assess_copy(
    it: StoredAssembly,
    locus: StoredLocus,
    assay: Assay,
    windows: dict[str, tuple[str, int, int]],
    cfg: Config,
    scoring: realign.Scoring,
    memo: dict[tuple[str, str], tuple[realign.Alignment, str]],
    channel_rule: str,
    bulges: bool = False,
) -> tuple[dict[str, SiteResult], dict[str, SiteResult]] | None:
    """Per role the site that counts on this copy, and every oligo's site; None if cut off."""
    chosen: dict[str, SiteResult] = {}
    every: dict[str, SiteResult] = {}
    for role in ROLES:
        got = _role_sites(it, locus, assay, role, windows, cfg, scoring, memo)
        if got is None:
            return None
        every.update(got)
        chosen[role] = _role_site(assay, role, every, channel_rule, bulges)
    return chosen, every


def _role_sites(
    it: StoredAssembly,
    locus: StoredLocus,
    assay: Assay,
    role: str,
    windows: dict[str, tuple[str, int, int]],
    cfg: Config,
    scoring: realign.Scoring,
    memo: dict[tuple[str, str], tuple[realign.Alignment, str]],
) -> dict[str, SiteResult] | None:
    """Every oligo of ``role`` on this copy; None if its site runs off the region."""
    strand, start, end = windows[role]
    # placed through the nearest exact block (chain locator), so a copy longer or shorter than
    # the reference still gets each site in the right place (overhaul step 5: the single
    # offset misplaced 518 of 1,132 Legionella sites)
    off = locus.offset_at(start - 1)
    # the site +- SITE_PAD, clamped to the region (a full-length BLAST hit carries no flanks);
    # a site that itself runs off the region cannot be assessed
    if off + start - 1 < 0 or off + end > len(locus.region):
        return None
    lo = max(0, off + start - 1 - SITE_PAD)
    hi = min(len(locus.region), off + end + SITE_PAD)
    window = locus.region[lo:hi]
    oriented = window if strand == "+" else iupac.reverse_complement(window)
    rules = cfg.specificity.probe_site if role == "probe" else cfg.specificity.primer_site
    out: dict[str, SiteResult] = {}
    for o in assay.by_role(role):  # alternatives in one mix
        key = (o.sequence.upper(), oriented)
        if key not in memo:
            memo[key] = _align(key[0], oriented, scoring, rules)
        aln, note = memo[key]
        site = _site(it, locus, o, strand, lo, len(window), aln, rules, 0, note)
        out[o.name] = assay.graded(site)
    return out


def _assess_parts(
    it: StoredAssembly,
    per_ref: list[dict[str, tuple[str, int, int]]],
    assay: Assay,
    cfg: Config,
    scoring: realign.Scoring,
    memo: dict[tuple[str, str], tuple[realign.Alignment, str]],
    channel_rule: str,
    bulges: bool,
) -> tuple[dict[str, SiteResult], dict[str, SiteResult]] | None:
    """The best site of every oligo on the copies cut by a contig end (user, 2026-09-28: in
    draft genomes the rRNA operons that carry the Legionella 23S-5S spacer break the assembly,
    so the fragment is split over two contigs, while each site is whole on one). Returns the
    sites that count per role and every oligo's site when every role has one, else None. The
    sites may come from different copies: see :func:`assess`."""
    every: dict[str, SiteResult] = {}
    for stored in it.loci:
        if not stored.truncated:
            continue
        locus = stored  # placed by the chain locator (signed, never clamped)
        windows = per_ref[stored.ref] if stored.ref < len(per_ref) else per_ref[0]
        for role in ROLES:
            for name, site in (_role_sites(it, locus, assay, role, windows, cfg, scoring, memo)
                               or {}).items():  # fmt: skip
                if "N" in site.s_aln.upper():
                    continue  # an N is neither a match nor a variant
                if name not in every or _closeness_key(site, bulges) < _closeness_key(
                    every[name], bulges
                ):
                    every[name] = site
    reporters = {o.reporter or "unspecified" for o in assay.probe}
    seen = {o.reporter or "unspecified" for o in assay.probe if o.name in every}
    if channel_rule == "all" and seen != reporters:
        return None  # a channel without any site cannot detect
    chosen: dict[str, SiteResult] = {}
    for role in ROLES:
        if not any(o.name in every for o in assay.by_role(role)):
            return None
        chosen[role] = _role_site(assay, role, every, channel_rule, bulges)
    return chosen, every


CUT_KINDS = {
    "not_assembled": "the fragment itself is not in the assembly: only the sequence beside it "
    "reaches a contig end (no fragment base in an exact block)",
    "no_site": "part of the fragment is there, but no oligo site is whole",
    "site_cut_ok": "{roles} cut off; the whole site(s) are detectable",
    "site_cut_fail": "{roles} cut off; a whole site already fails",
    "sites_fail": "every site is whole on the cut copies, but they are not all detectable",
    "other": "no copy cut by a contig end, but a site runs off the stored region",
}


def cut_kind(
    it: StoredAssembly,
    per_ref: list[dict[str, tuple[str, int, int]]],
    assay: Assay,
    cfg: Config,
    scoring: realign.Scoring,
    memo: dict[tuple[str, str], tuple[realign.Alignment, str]],
    channel_rule: str,
    bulges: bool,
) -> tuple[str, str]:
    """Why a genome with the region has no judged site (user, 2026-10-02: the breakdown of the
    Legionella genomes cut by a contig end). Information only: they stay undetermined."""
    cut = [lc for lc in it.loci if lc.truncated]
    if not cut:
        return "other", CUT_KINDS["other"]
    if all(lc.n_seeds == 0 for lc in cut):
        return "not_assembled", CUT_KINDS["not_assembled"]
    every: dict[str, SiteResult] = {}
    for locus in cut:
        windows = per_ref[locus.ref] if locus.ref < len(per_ref) else per_ref[0]
        for role in ROLES:
            for name, site in (_role_sites(it, locus, assay, role, windows, cfg, scoring, memo)
                               or {}).items():  # fmt: skip
                if "N" in site.s_aln.upper():
                    continue
                if name not in every or _closeness_key(site, bulges) < _closeness_key(
                    every[name], bulges
                ):
                    every[name] = site
    whole = [r for r in ROLES if any(o.name in every for o in assay.by_role(r))]
    if not whole:
        return "no_site", CUT_KINDS["no_site"]
    if len(whole) == len(ROLES):
        return "sites_fail", CUT_KINDS["sites_fail"]
    ok = all(detectable(_role_site(assay, r, every, channel_rule, bulges), bulges) for r in whole)
    missing = [r for r in ROLES if r not in whole]
    roles = " and ".join(f"the {r} site" for r in missing)
    kind = "site_cut_ok" if ok else "site_cut_fail"
    return f"{kind}:{'+'.join(missing)}", CUT_KINDS[kind].format(roles=roles)


def _align(
    oligo: str, oriented: str, scoring: realign.Scoring, rules: SiteRules
) -> tuple[realign.Alignment, str]:
    """The semiglobal alignment, or, when that is not detectable but the site only differs by
    the length of a single-base run, the run-length (bulge) alignment with its label."""
    aln = realign.align_semiglobal(oligo, oriented, scoring)
    m = realign.measure(aln.q_aln, aln.s_aln)
    if m.n_mismatch + m.n_gap == 0:
        return aln, ""
    shift = realign.homopolymer_shift(oligo, oriented)
    if shift is None:
        return aln, ""
    alt = realign.measure(shift.alignment.q_aln, shift.alignment.s_aln)
    # the run-length reading wins when it explains the site with no mismatch at all
    if alt.n_mismatch == 0:
        return shift.alignment, shift.label
    return aln, ""


def _role_site(
    assay: Assay, role: str, every: dict[str, SiteResult], channel_rule: str, bulges: bool = False
) -> SiteResult:
    """The site that counts for a role: its best alternative; for probes in several reporter
    channels, the best of each channel, then any (best) or all (worst) channels."""
    members = assay.by_role(role)

    def key(s: SiteResult) -> tuple[int, int, int]:
        return _closeness_key(s, bulges)

    present = [o for o in members if o.name in every]  # detectable from parts: some may be missing
    if role != "probe" or channel_rule == "any":
        return min((every[o.name] for o in present), key=key)
    channels: dict[str, list[SiteResult]] = defaultdict(list)
    for o in present:
        channels[o.reporter or "unspecified"].append(every[o.name])
    per_channel = [min(v, key=key) for v in channels.values()]
    return max(per_channel, key=key)


def _run_length_breakdown(calls: list[GenomeCall], bulges: bool) -> RunLengthBreakdown | None:
    with_variant = [c for c in calls if c.run_variants]
    if not with_variant:
        return None
    levels: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for c in calls:
        level = c.assembly_level or "unknown"
        levels[level][1] += 1
        levels[level][0] += bool(c.run_variants)
    variants: Counter = Counter(v for c in with_variant for v in set(c.run_variants))
    return RunLengthBreakdown(
        genomes=len(with_variant),
        on_best_copy=sum(c.run_on_best for c in with_variant),
        mixed=sum(c.run_mixed for c in with_variant),
        decided_by_rule=sum((c.n_detectable > 0) != (c.n_detectable_other_rule > 0) for c in calls),
        by_level=dict(sorted(levels.items(), key=lambda x: -x[1][1])),
        variants=variants.most_common(5),
    )


_LEVEL_ORDER = {"Complete Genome": 0, "Chromosome": 1, "Scaffold": 2, "Contig": 3}
COMPLETE_LEVELS = frozenset({"Complete Genome", "Chromosome"})
DRAFT_LEVELS = frozenset({"Scaffold", "Contig"})
MIN_COMPLETE_GENOMES = 5  # fewer complete genomes: no typical copy number, the rule is off


def mark_unassembled(calls: list[GenomeCall], setting: str = "auto") -> float | None:
    """Mark draft genomes whose escape is likely an assembly artefact of a multi-copy target
    (advisor subagent, 2026-09-28; user decision): near-identical repeat copies are often left
    unassembled in drafts (the opa genes of N. gonorrhoeae GCF_000156755.1 sit in scaffold gaps,
    so only a divergent copy was assembled and judged). A genome is marked when its best copy
    fails, it is a fragmented draft (Scaffold or Contig with more than one sequence, or a copy
    cut by a contig end), it has fewer than half the median copy number of the complete and
    chromosome-level genomes of this run (at least 5 of them, median 2 or more), and no complete
    or chromosome-level genome fails with the same three genome sites (then the pattern is
    real). Marked genomes count as
    undetermined, never as detected; this can hide a real loss of copies, so they are listed.
    Returns the typical (median) copy number, or None when the rule does not apply."""
    if setting == "off":
        return None
    complete = [c for c in calls if c.assembly_level in COMPLETE_LEVELS]
    if len(complete) < MIN_COMPLETE_GENOMES:
        return None
    # n_copies counts the whole copies of each genome (every copy is kept, no cap)
    typical = float(statistics.median(c.n_copies for c in complete))
    if typical < 2:
        return None  # a single-copy target: a missing or failing copy is a real escape
    failing_complete = {c.signature for c in complete if c.n_detectable == 0}
    for c in calls:
        if (
            c.assembly_level not in DRAFT_LEVELS
            or c.n_detectable > 0
            or c.undetermined
            or c.from_parts
        ):
            continue
        fragmented = c.n_truncated > 0 or (c.n_contigs or 0) > 1
        if fragmented and c.n_copies * 2 < typical and c.signature not in failing_complete:
            c.unassembled = True
    return typical


_LEVEL_FIELD = {
    GenomeOutcome.DETECTED: "detectable",
    GenomeOutcome.NOT_DETECTED: "escapes",
    GenomeOutcome.UNDETERMINED: "undetermined",
    GenomeOutcome.UNASSEMBLED: "unassembled",
    GenomeOutcome.FROM_PARTS: "from_parts",
}


def _level_coverage(calls: list[GenomeCall]) -> list[LevelCoverage]:
    """Detectable genomes, escapes and undetermined per assembly level, complete genomes first
    (only when the genomes come in more than one level; Nucleotide records have none)."""
    levels: dict[str, LevelCoverage] = {}
    for c in calls:
        name = c.assembly_level or "unknown"
        row = levels.setdefault(name, LevelCoverage(level=name))
        row.genomes += 1
        field_ = _LEVEL_FIELD[genome_outcome(c)]  # from parts: its own class, out of the %
        setattr(row, field_, getattr(row, field_) + 1)
    if len(levels) < 2:
        return []
    return sorted(levels.values(), key=lambda r: (_LEVEL_ORDER.get(r.level, 9), r.level))


def copy_coverage(
    calls: list[GenomeCall], assay: Assay, rule: str, bulges: bool = False
) -> CopyCoverage:
    """Copies, coverage per oligo and per probe channel, and the escape list.

    ``bulges`` is the homopolymer-bulge rule used; the count under the other rule is kept too.
    """
    other = sum(c.n_detectable_other_rule > 0 for c in calls)
    configured = sum(c.n_detectable > 0 for c in calls)
    out = CopyCoverage(
        genomes=len(calls),
        multi_copy=sum(c.n_copies > 1 for c in calls),
        max_copies=max((c.n_copies for c in calls), default=0),
        best_copy_not_first=sum(not c.best_is_first for c in calls),
        with_detectable_copy=configured,
        probe_channels=rule,
        homopolymer_bulges_detectable=bulges,
        with_detectable_copy_strict=other if bulges else configured,
        with_detectable_copy_bulges=configured if bulges else other,
    )
    out.run_length = _run_length_breakdown(calls, bulges)
    outcome = {c.accession: genome_outcome(c) for c in calls}

    def having(o: GenomeOutcome) -> list[str]:
        return [acc for acc, x in outcome.items() if x == o]

    escapes = having(GenomeOutcome.NOT_DETECTED)
    parts = [c.accession for c in calls if c.from_parts]
    out.from_parts, out.from_parts_accessions = len(parts), parts
    out.from_parts_counted = any(c.from_parts and c.n_detectable > 0 for c in calls)
    out.escapes, out.escape_examples = len(escapes), escapes[:20]
    by_acc = {c.accession: c for c in calls}
    out.escape_rows = [
        EscapeRow(accession=acc, kind=by_acc[acc].escape_kind or "mismatch",
                  detail=by_acc[acc].escape_detail, assembly_level=by_acc[acc].assembly_level,
                  copies=by_acc[acc].n_copies)
        for acc in escapes
    ]  # fmt: skip
    kinds = Counter(r.kind for r in out.escape_rows)
    out.escape_reasons = [
        EscapeReason(kind=k, label=ESCAPE_KINDS.get(k, k), genomes=n,
                     examples=[r.accession for r in out.escape_rows if r.kind == k][:10])
        for k, n in kinds.most_common()
    ]  # fmt: skip
    unassembled = having(GenomeOutcome.UNASSEMBLED)
    out.unassembled, out.unassembled_accessions = len(unassembled), unassembled
    undet = having(GenomeOutcome.UNDETERMINED)
    out.undetermined, out.undetermined_examples = len(undet), undet[:20]
    out.by_level = _level_coverage(calls)
    # detectable from parts and not counted as detected: out of the per-oligo and channel counts
    # too, as out of the whole-fragment figures (code review, 2026-09-28)
    judged = [c for c in calls if outcome[c.accession] != GenomeOutcome.FROM_PARTS]
    for role in ROLES:
        members = assay.by_role(role)
        for o in members:
            others = [x.name for x in members if x.name != o.name]
            out.oligos.append(
                OligoCoverageRow(
                    role=role,
                    name=o.name,
                    reporter=o.reporter if role == "probe" else None,
                    covered=sum(c.oligo_good.get(o.name, False) for c in judged),
                    only=sum(
                        c.oligo_good.get(o.name, False)
                        and not any(c.oligo_good.get(x, False) for x in others)
                        for c in judged
                    ),
                )  # fmt: skip
            )
        uncovered = [c for c in judged
                     if not any(c.oligo_good.get(o.name, False) for o in members)]  # fmt: skip
        none = [c.accession for c in uncovered if c.role_state.get(role) != "undetermined"]
        out.role_none[role], out.role_none_examples[role] = len(none), none[:20]
        out.role_undetermined[role] = sum(
            c.role_state.get(role) == "undetermined" for c in uncovered
        )
    channels: dict[str, list[str]] = defaultdict(list)
    for o in assay.probe:
        channels[o.reporter or "unspecified"].append(o.name)
    for reporter, names in channels.items():
        out.channels.append(
            ChannelCoverageRow(
                reporter=reporter,
                probes=names,
                covered=sum(any(c.oligo_good.get(x, False) for x in names) for c in judged),
            )  # fmt: skip
        )
    per_genome = [
        [any(c.oligo_good.get(x, False) for x in names) for names in channels.values()]
        for c in judged
    ]
    out.any_channel = sum(any(g) for g in per_genome)
    out.all_channels = sum(all(g) for g in per_genome)
    return out


def _site(it: StoredAssembly, locus: StoredLocus, o: Oligo, strand: str, lo: int, wlen: int,
          aln: realign.Alignment, rules, n: int, note: str = "") -> SiteResult:  # fmt: skip
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
        id=f"V{n}", tier="target", query=o.name, role=o.role,  # type: ignore[arg-type]
        oligo=aln.q_aln.replace("-", ""), accession=it.accession, taxid=it.taxid,
        organism=it.organism, title=f"{locus.contig} ({it.assembly_level})",
        orientation=contig_orientation,  # type: ignore[arg-type]
        subject_start=c0, subject_end=c1, source="realigned", note=note,
        **_result_fields(aln.q_aln, aln.s_aln, m, rules),
    )  # fmt: skip


def _fragment_years(
    sites: list[SiteResult], year_of: dict[str, int | None], listed: dict[int, int],
    shown: list[int], bulges: bool, unassembled: set[str] | None = None,
    from_parts: set[str] | None = None, unjudged: set[str] | None = None,
) -> list[FragmentYear]:  # fmt: skip
    """Per year, each genome's outcome from its three best-copy sites together, as in the
    whole-fragment table (user, 2026-09-25: one summary next to the per-oligo tables)."""
    by_genome: dict[str, dict[str, SiteResult]] = defaultdict(dict)
    for s in sites:
        by_genome[s.accession][s.role] = s
    out = {y: FragmentYear(year=y, population_size=listed.get(y), with_region=0) for y in shown}
    for acc, roles in by_genome.items():
        row = out.get(year_of.get(acc))  # type: ignore[arg-type]
        if row is None or len(roles) < len(ROLES):
            continue
        outcome, by_pair = grade.combination_outcome(
            roles["forward"], roles["probe"], roles["reverse"], bulges
        )
        row.with_region += 1
        if acc in (from_parts or ()):
            row.undetermined += 1  # detectable from parts, not counted as detected
            row.from_parts += 1
        elif outcome != "detectable" and acc in (unassembled or ()):
            row.undetermined += 1  # copies possibly unassembled: neither detected nor escaped
            row.unassembled += 1
        elif outcome == "detectable":
            row.detectable += 1
        elif outcome == "at risk":
            row.at_risk += 1
        elif outcome == "likely failure":
            row.likely_failure += 1
            row.by_pair_rule += by_pair
        elif outcome == "undetermined":
            row.undetermined += 1
    for acc in unjudged or ():  # region there, no site judged (cut, or hidden by N)
        row = out.get(year_of.get(acc))  # type: ignore[arg-type]
        if row is not None:
            row.with_region += 1
            row.undetermined += 1
            row.unjudged += 1
    return [out[y] for y in shown]


def distinct_patterns(
    sites: list[SiteResult], year_of: dict[str, int], first: int, last: int, bulges: bool,
    unassembled: set[str] | None = None, from_parts: set[str] | None = None,
    axis: str = "release",
) -> DistinctPatterns | None:  # fmt: skip
    """The judged genomes of the window ``first``-``last`` (by ``year_of``), with genomes whose
    three best-copy sites are identical (oligo and aligned genome bases) counted once (theory
    reviews 2026-10-01, user 2026-10-02). Undetermined genomes are left out, as in the status.
    Identical sites give the same outcome, so each pattern has one."""
    by_genome: dict[str, dict[str, SiteResult]] = defaultdict(dict)
    for s in sites:
        if first <= year_of.get(s.accession, _NOT_READ) <= last:
            by_genome[s.accession][s.role] = s
    outcome_of: dict[tuple, str] = {}
    carriers: Counter[tuple] = Counter()
    for acc, roles in by_genome.items():
        if len(roles) < len(ROLES) or acc in (from_parts or ()):
            continue
        outcome, _ = grade.combination_outcome(
            roles["forward"], roles["probe"], roles["reverse"], bulges
        )
        if outcome == "undetermined" or (outcome != "detectable" and acc in (unassembled or ())):
            continue
        key = tuple((r, roles[r].query, roles[r].s_aln.upper()) for r in ROLES)
        outcome_of[key] = outcome
        carriers[key] += 1
    if not carriers:
        return None
    by_outcome = Counter(outcome_of.values())
    return DistinctPatterns(
        first=first, last=last, axis=axis, genomes=sum(carriers.values()),
        patterns=len(carriers), detectable=by_outcome["detectable"],
        at_risk=by_outcome["at risk"], likely_failure=by_outcome["likely failure"],
        largest=max(carriers.values()),
        likely_failure_genomes=sum(n for k, n in carriers.items()
                                   if outcome_of[k] == "likely failure"),
    )  # fmt: skip


def bulge_alternative(
    sites: list[SiteResult], year_of: dict[str, int], first: int, last: int, bulges: bool,
    unassembled: set[str], from_parts: set[str], other_rule: set[str],
) -> float | None:  # fmt: skip
    """The status window's detectable percentage under the other homopolymer-bulge setting: of
    the same judged genomes (undetermined ones left out, as in the status), those with a copy
    detectable under the other setting (theory reviews 2026-10-01: report the strict-lenient
    spread as an interval)."""
    by_genome: dict[str, dict[str, SiteResult]] = defaultdict(dict)
    for s in sites:
        if first <= year_of.get(s.accession, _NOT_READ) <= last:
            by_genome[s.accession][s.role] = s
    judged = detectable = 0
    for acc, roles in by_genome.items():
        if len(roles) < len(ROLES) or acc in from_parts:
            continue
        outcome, _ = grade.combination_outcome(
            roles["forward"], roles["probe"], roles["reverse"], bulges
        )
        if outcome == "undetermined" or (outcome != "detectable" and acc in unassembled):
            continue
        judged += 1
        detectable += acc in other_rule
    return 100.0 * detectable / judged if judged else None


def _bulge_line(alternative: float | None, percent: float | None, bulges: bool) -> list[str]:
    """One rationale line: the headline figure under the other homopolymer-bulge setting."""
    if alternative is None or percent is None or abs(alternative - percent) < 0.05:
        return []
    other = "tolerated" if not bulges else "not tolerated (strict)"
    this = "not tolerated (strict)" if not bulges else "tolerated"
    return [
        f"Homopolymer setting: {alternative:.1f}% detectable if single-base run-length "
        f"differences were {other}, against {percent:.1f}% with them {this} as in the status "
        "(setting variants.homopolymer_bulges_detectable). Whether a primer binds over a run "
        "one base longer or shorter has no published PCR data; a wet-lab test of the commonest "
        "run-length variant decides which figure applies."
    ]


def _distinct_line(d: DistinctPatterns | None, genome_percent: float | None) -> list[str]:
    """One rationale line: the window with identical site patterns counted once (information)."""
    if d is None or d.percent is None:
        return []
    done = "collected" if d.axis == "collection" else "released"
    line = (
        f"Distinct site patterns (information only; the status counts genomes): the "
        f"{d.genomes:,} judged genomes {done} {d.first}-{d.last} carry {d.patterns:,} "
        f"different combinations of the three sites; counted once each, {d.percent:.1f}% "
        f"of the patterns are detectable"
    )
    if genome_percent is not None:
        line += f" (against {genome_percent:.1f}% of the genomes)"
    line += (
        f", {100.0 * d.at_risk / d.patterns:.1f}% at risk and "
        f"{100.0 * d.likely_failure / d.patterns:.1f}% likely failure"
    )
    if d.likely_failure:
        line += (
            f" ({d.likely_failure:,} failing pattern{'s' if d.likely_failure != 1 else ''} "
            f"in {d.likely_failure_genomes:,} genomes)"
        )
    line += (
        f". The most common pattern is carried by {d.largest:,} genomes "
        f"({100.0 * d.largest / d.genomes:.1f}%). A large gap between the two figures means "
        "a few lineages dominate the database; neither figure is the share of strains in "
        "circulation."
    )
    return [line]


_EARLIER, _UNDATED, _NOT_READ = -1, -2, -3  # collection-axis rows that are not a year


def collection_bucket(items: list[StoredAssembly], shown: list[int]) -> dict[str, int]:
    """Each genome released in the window ``shown``: its collection year, or a row that is not
    a year (collected earlier, no usable date, not read yet)."""
    if not shown:
        return {}
    first, last = min(shown), max(shown)
    bucket: dict[str, int] = {}
    for it in items:
        if not first <= it.year <= last:
            continue
        if it.collection_date is None:
            bucket[it.accession] = _NOT_READ
            continue
        y = collection_year(it.collection_date, latest=last)
        bucket[it.accession] = _UNDATED if y is None else (_EARLIER if y < first else y)
    return bucket


def collection_axis(
    sites: list[SiteResult], items: list[StoredAssembly], shown: list[int], bulges: bool,
    unassembled: set[str] | None = None, from_parts: set[str] | None = None,
    unjudged: set[str] | None = None,
) -> CollectionAxis | None:  # fmt: skip
    """The genomes released in the window ``shown``, by collection year (user, 2026-09-30: a
    batch of old samples uploaded late must not make an old lineage look new)."""
    if not shown:
        return None
    first, last = min(shown), max(shown)
    bucket = collection_bucket(items, shown)
    keys = [*range(first, last + 1), _EARLIER, _UNDATED, _NOT_READ]
    rows = {r.year: r for r in _fragment_years(sites, bucket, {}, keys, bulges, unassembled,
                                                from_parts, unjudged)}  # fmt: skip
    for key, label in ((_EARLIER, f"before {first}"), (_UNDATED, "no usable date"),
                       (_NOT_READ, "not read yet")):  # fmt: skip
        rows[key].label = label
    return CollectionAxis(
        first_year=first, last_year=last,
        years=[rows[y] for y in range(first, last + 1) if rows[y].with_region],
        earlier=rows[_EARLIER], undated=rows[_UNDATED], not_read=rows[_NOT_READ],
    )  # fmt: skip


def _collection_line(
    axis: CollectionAxis | None, unit: str, status_axis: str = "release"
) -> list[str]:
    """One rationale line when the collection dates tell a different story (information), or,
    with the status by collection year, what that status leaves out."""
    if axis is None:
        return []
    total = sum(r.with_region for r in axis.years) + axis.earlier.with_region
    total += axis.undated.with_region + axis.not_read.with_region
    if status_axis == "collection":
        apart = axis.undated.with_region + axis.not_read.with_region
        if not apart:
            return []
        return [
            f"Left out of the status by collection year: {apart} of {total} {unit} released "
            f"{axis.first_year}-{axis.last_year} with the region "
            f"({100.0 * apart / total:.1f}%) have no collection year to place them by "
            f"({axis.undated.with_region} without a usable date"
            + (f", {axis.not_read.with_region} not read yet" if axis.not_read.with_region else "")
            + "); they are in the table by collection year and in the figures by release year."
        ]
    if not total or not (axis.earlier.with_region or axis.undated.with_region):
        return []
    line = (
        f"By collection date (information only; the status uses the release year): of {total} "
        f"{unit} released {axis.first_year}-{axis.last_year} with the region, "
        f"{axis.earlier.with_region} were collected before {axis.first_year} and "
        f"{axis.undated.with_region} carry no usable collection date"
    )
    if axis.not_read.with_region:
        line += f"; for {axis.not_read.with_region} it was not read yet"
    return [line + "."]


def _bracket(detected: int, undetermined: int, total: int, unit: str) -> str:
    """The two extremes the undetermined genomes allow (theory reviews 2026-10-01)."""
    low, high = 100.0 * detected / total, 100.0 * (detected + undetermined) / total
    return (
        f"With the {undetermined:,} undetermined {unit} counted: {low:.1f}% detectable if all "
        f"of them were escapes, {high:.1f}% if all were detected."
    )


def hold_back(verdict: Verdict, rules: Any, coverage_complete: bool) -> tuple[Verdict, str]:
    """Whether a crossed limit waits for complete coverage, and the words for it.

    While genomes or records are still to assess the figure is not the population's: they are
    worked newest publication year first, so a partial run is weighted to the most recent year and
    a figure can cross a limit and cross back (user, 2026-10-07: "Keep incomplete for now"). A
    Review has waited since the code review of 2026-09-27, which asked only that missing evidence
    never read as no flags; holding an Exceeds limit back as well is the 2026-10-07 decision, and
    ``inclusivity.limits_need_complete_coverage: false`` restores the older rule for it. Returns
    the verdict unchanged and an empty string when nothing is held back.
    """
    if coverage_complete or verdict not in (Verdict.FAIL, Verdict.WARN):
        return verdict, ""
    if verdict is Verdict.FAIL and not getattr(rules, "limits_need_complete_coverage", True):
        return verdict, ""
    note = (
        "held back while genomes are still to assess: the newest are assessed first, so this "
        "subset is weighted to the most recent year"
    )
    if verdict is Verdict.FAIL:
        note += "; setting inclusivity.limits_need_complete_coverage"
    return Verdict.INCOMPLETE, note


def fragment_verdict(
    years: list[FragmentYear], rules: Any, axis: str = "release",
    undated: tuple[int, int] | None = None, coverage_complete: bool = True,
) -> tuple[Verdict, list[str]]:  # fmt: skip
    """The inclusivity verdict from the whole-fragment genome outcome (advisor subagent,
    2026-09-26): pooled over the last ``verdict_window_years`` complete release years plus the
    current one, undetermined genomes left out of the denominator, at risk counted as not
    detected; too few genomes in the window is INCOMPLETE; when the pooled figure passes, a
    single window year with at least ``min_genomes_per_year`` genomes below
    ``fail_below_percent`` gives WARN (years outside the window never decide). The
    per-oligo figures are diagnostics only. ``axis``: whether ``years`` are release years or
    collection years (``inclusivity.status_axis``); the window counts that year. ``undated``:
    with collection years, (genomes with the region and no collection year to place them by,
    all genomes with the region released in the years shown); more than
    ``max_undetermined_percent`` undated is INCOMPLETE (user, 2026-10-02), as for undetermined
    genomes, so a status is never carried by the dated minority.

    ``coverage_complete``: whether every listed genome or record has been assessed. While it is
    False, a crossed limit is held back to INCOMPLETE and the sentence names what it would have
    been; :func:`hold_back` says which limits wait and which setting releases an Exceeds
    limit."""
    w = fragment_window(years, rules.verdict_window_years)
    by_collection = axis == "collection"
    done, year_word = ("collected", "Collection") if by_collection else ("released", "Release")
    if w is None:
        return Verdict.INCOMPLETE, ["No genome with the target region in the years shown."]
    n, undet = w.n, w.undetermined
    det, risk, fail = w.detectable, w.at_risk, w.likely_failure
    span = f"{w.first}-{w.last}"
    if n < rules.min_genomes_for_verdict:
        return Verdict.INCOMPLETE, [
            f"Too few recent genomes to judge: {n} with the target region {done} {span} "
            f"(at least {rules.min_genomes_for_verdict} needed; setting "
            "inclusivity.min_genomes_for_verdict)."
        ]
    pct = 100.0 * det / n
    total = n + undet
    share = 100.0 * undet / total if total else 0.0
    lines = [
        f"Whole fragment, genomes {done} {span}: {pct:.1f}% detectable (perfect or "
        f"tolerated), {100.0 * (det + risk) / n:.1f}% including at risk, "
        f"{100.0 * fail / n:.1f}% likely failure, of {n} genomes with the target region "
        f"(undetermined, not counted: {undet}"
        + (f", of which {w.unassembled} with copies possibly unassembled" if w.unassembled else "")
        + (f", {w.from_parts} detectable from parts" if w.from_parts else "")
        + (f", {w.unjudged} with the region cut or hidden by N" if w.unjudged else "")
        + "). The per-oligo and per-year figures are "
        "diagnostics; the status uses the whole fragment over this window."
    ]
    if undet:
        lines.append(_bracket(det, undet, total, "genomes"))
    if share > rules.max_undetermined_percent:
        verdict, why = (
            Verdict.INCOMPLETE,
            (
                f" ({share:.1f}% of the genomes with the region are undetermined, more than "
                f"{rules.max_undetermined_percent:g}%: setting "
                "inclusivity.max_undetermined_percent)"
            ),
        )
    elif (
        undated and undated[1] and 100.0 * undated[0] / undated[1] > rules.max_undetermined_percent
    ):
        verdict, why = (
            Verdict.INCOMPLETE,
            (
                f" ({100.0 * undated[0] / undated[1]:.1f}% of the genomes with the region have "
                f"no usable collection year, more than {rules.max_undetermined_percent:g}%: "
                "settings inclusivity.max_undetermined_percent and inclusivity.status_axis)"
            ),
        )
    elif pct < rules.fail_below_percent:
        verdict, why = Verdict.FAIL, f" (below {rules.fail_below_percent:g}%)"
    elif pct < rules.warn_below_percent:
        verdict, why = Verdict.WARN, f" (below {rules.warn_below_percent:g}%)"
    else:
        verdict, why = Verdict.PASS, ""
    if verdict is Verdict.PASS:  # only a year inside the window, and only when it changes things
        for y in w.years:
            n_y = y.with_region - y.undetermined
            if n_y >= rules.min_genomes_per_year:
                p_y = 100.0 * y.detectable / n_y
                if p_y < rules.fail_below_percent:
                    lines.append(
                        f"{year_word} year {y.year} on its own: {p_y:.1f}% detectable of {n_y} "
                        f"genomes, below the limit of {rules.fail_below_percent:g}% "
                        "(fail_below_percent)."
                    )
                    verdict, why = (
                        Verdict.WARN,
                        f" (a single {year_word.lower()} year below the limit)",
                    )
    held, note = hold_back(verdict, rules, coverage_complete)
    if held is not verdict:
        why = f" ({STATUS_LABEL[verdict]}{why} on the {done} genomes assessed so far, {note})"
        verdict = held
    # written last, so the sentence always names the status the section ends with
    lines[0] += f" Status: {STATUS_LABEL[verdict]}{why}."
    return verdict, lines


def exhaustive_inclusivity(
    sites: list[SiteResult],
    items: list[StoredAssembly],
    years: list[YearCoverage],
    assay: Assay,
    cfg: Config,
    *,
    source: str = "datasets",
    unassembled: set[str] | None = None,
    from_parts: set[str] | None = None,
    unjudged: set[str] | None = None,
    other_rule: set[str] | None = None,
    coverage_complete: bool = True,
) -> InclusivityResult:
    """Per-release-year inclusivity over every assessed assembly (not a sample).
    ``other_rule``: genomes with a copy detectable under the other homopolymer-bulge setting,
    for the status window's figure under both settings (theory reviews 2026-10-01).
    ``unassembled``: genomes whose copies are possibly unassembled (:func:`mark_unassembled`),
    counted as undetermined in the whole-fragment outcome. ``unjudged``: genomes with the
    region but no judged site (cut by a contig end, or hidden by N), counted as undetermined
    too, as in the channels."""
    year_of = {it.accession: it.year for it in items}
    listed = {y.year: y.listed for y in years}
    lookback = cfg.inclusivity.lookback_years
    shown = sorted(listed)[-lookback:] if listed else []
    oligos: list[InclusivityOligoResult] = []
    for role in ROLES:
        # detectable from parts and not counted as detected: out of the per-oligo windows too
        role_sites = [s for s in sites if s.role == role and s.accession not in (from_parts or ())]
        windows = [
            _stats([s for s in role_sites if year_of.get(s.accession) == y], y, listed[y],
                   max(len(o.sequence) for o in assay.by_role(role)))
            for y in shown
        ]  # fmt: skip
        oligo = " / ".join(o.sequence for o in assay.by_role(role))
        oligos.append(InclusivityOligoResult(role=role, oligo=oligo, windows=windows))
    bulges = cfg.variants.homopolymer_bulges_detectable
    fragment_years = _fragment_years(
        sites, year_of, listed, shown, bulges,
        unassembled or set(), from_parts or set(), unjudged or set(),
    )  # fmt: skip
    collection = collection_axis(
        sites, items, shown, bulges, unassembled or set(), from_parts or set(), unjudged or set()
    )
    axis = cfg.inclusivity.status_axis
    by_collection = axis == "collection"
    status_rows = (collection.years if collection else []) if by_collection else fragment_years
    undated = None
    if by_collection and collection is not None:
        apart = collection.undated.with_region + collection.not_read.with_region
        placed = sum(r.with_region for r in collection.years) + collection.earlier.with_region
        undated = (apart, apart + placed)
    verdict, rationale = fragment_verdict(
        status_rows, cfg.inclusivity, axis, undated, coverage_complete
    )
    unit = "assemblies" if source == "datasets" else "records"
    if by_collection:
        rw = fragment_window(fragment_years, cfg.inclusivity.verdict_window_years)
        if rw is not None and rw.percent is not None:
            rationale.append(
                f"By release year (information only; the status uses the collection year): "
                f"{rw.percent:.1f}% detectable of {rw.n} {unit} released {rw.first}-{rw.last} "
                f"(undetermined, not counted: {rw.undetermined})."
            )
    rationale += _collection_line(collection, unit, axis)
    w = fragment_window(status_rows, cfg.inclusivity.verdict_window_years)
    distinct = None
    alternative = None
    if w is not None:
        axis_year = collection_bucket(items, shown) if by_collection else year_of
        distinct = distinct_patterns(
            sites, axis_year, w.first, w.last, bulges, unassembled or set(), from_parts or set(),
            axis,
        )  # fmt: skip
        rationale += _distinct_line(distinct, w.percent)
        if other_rule is not None:
            alternative = bulge_alternative(
                sites, axis_year, w.first, w.last, bulges, unassembled or set(),
                from_parts or set(), other_rule,
            )  # fmt: skip
            rationale += _bulge_line(alternative, w.percent, bulges)
    rationale += [
        f"{y.year}: {y.listed} "
        + (
            f"assembl{'y' if y.listed == 1 else 'ies'}"
            if source == "datasets"
            else f"record{'' if y.listed == 1 else 's'}"
        )
        + " listed, "
        f"{y.assessed} assessed so far"
        + (
            f", {y.unavailable} could not be downloaded after repeated attempts"
            if y.unavailable
            else ""
        )
        + ("; the rest follow on later runs." if y.assessed + y.unavailable < y.listed else ".")
        for y in sorted(years, key=lambda y: y.year)
        if y.year in shown and y.assessed < y.listed
    ]
    return InclusivityResult(
        tier_searched=True,
        exhaustive=True,
        target_taxid=assay.target.taxid,
        oligos=oligos,
        fragment_years=fragment_years,
        collection=collection,
        status_axis=axis,
        distinct=distinct,
        bulge_alternative=alternative,
        bulges_tolerated=bulges,
        sample_scheme=(
            (
                "Every genome assembly of the target in NCBI Datasets (current versions, one copy "
                "per GenBank/RefSeq pair), by release year; 'Assemblies' is the number NCBI lists "
                "for that year"
            )
            if source == "datasets"
            else (
                "Every NCBI Nucleotide record of the target, by publication year; 'Records' "
                "is the number ESearch lists for that year"
            )
        )
        + (
            " and 'With region' the number in which the target region was found; those with the "
            "region cut by a "
            + ("contig" if source == "datasets" else "record")
            + " end or hidden by N are counted as undetermined. Not a sample: the gap between "
            "the two is explained below (region not found, or not processed yet)."
        ),
        verdict=verdict,
        rationale=rationale,
        limitations=(
            [
                (
                    "The status window counts the collection year the submitter recorded; "
                    "assemblies without a usable one are left out of it and counted. The NCBI "
                    "release year is shown as the first table."
                    if by_collection
                    else "Assemblies are grouped by NCBI release year; the collection date "
                    "recorded with the sample is shown as a second axis (information only)."
                ),
                "Only genome assemblies are covered; sequences submitted without an assembly "
                "(single genes, amplicons) are not part of NCBI Datasets' genome collection.",
            ]
            if source == "datasets"
            else [
                (
                    "The status window counts the collection year the submitter recorded; "
                    "records without a usable one are left out of it and counted. The NCBI "
                    "publication year is shown as the first table."
                    if by_collection
                    else "Records are grouped by NCBI publication year; the collection date "
                    "recorded with the sequence is shown as a second axis (information only)."
                ),
                "Records that do not contain the target region (other genes, partial sequences) "
                "are counted as 'not found' and are not part of the per-year counts.",
            ]
        ),
    )


# ------------------------------------------------------------------ one call for the CLI
def placements(assay: Assay, amplicon: str, cfg: Config) -> list[dict[str, tuple[str, int, int]]]:
    """The oligo windows per reference amplicon (the first, then each further one)."""
    mm = cfg.thresholds.amplicon.max_site_mismatches
    placed = [oligo_sites(assay, amplicon, mm)]
    for ref in assay.reference_amplicons[1:]:  # one that cannot place a role uses the first's
        try:
            placed.append(oligo_sites(assay, ref.sequence.upper(), mm))
        except InputError:
            placed.append(placed[0])
    return placed


def channel_results(
    assay: Assay,
    items: list[StoredAssembly],
    calls: list[GenomeCall],
    scan_taxon: int | None,
    ancestors_of: Callable[[list[int]], dict[int, set[int]]] | None = None,
) -> list[ChannelResult]:
    """Every channel of the first locus over every assessed genome (overhaul step 5c).

    A genome belongs to a channel's target when its NCBI lineage holds the channel's target
    taxon (no lookup needed when that is the scanned taxon itself); a genome in one of the
    channel's out-of-scope taxa counts for information only. User decision (2026-09-29): a
    complete genome without the locus counts as not detected (a possible deletion); a draft
    without it is 'no locus'.
    """
    probes0 = set(assay.loci[0].probes)
    channels = [ch for ch in assay.channels if set(ch.probes) <= probes0]
    need = [ch for ch in channels
            if ch.taxa or ch.target_taxid not in (None, scan_taxon)]  # fmt: skip
    anc: dict[int, set[int]] = {}
    if need and ancestors_of is not None:
        try:
            anc = ancestors_of(sorted({it.taxid for it in items if it.taxid}))
        except NcbiError as exc:
            log.warning("Could not look up genome lineages for the channels: %s", exc)
    call_of = {c.accession: c for c in calls}
    out: list[ChannelResult] = []
    for ch in channels:
        r = ChannelResult(name=ch.name, reporter=ch.reporter, probes=list(ch.probes),
                          target_taxid=ch.target_taxid)  # fmt: skip
        for it in items:
            member = _membership(ch, it.taxid, anc, scan_taxon, ch in need)
            if member is None:
                r.membership_unknown += 1
                continue
            state = _genome_channel_state(it, call_of.get(it.accession), ch.name)
            if member == "target":
                r.target_genomes += 1
                if state == "ok":
                    r.detected += 1
                elif state == "none":
                    if it.assembly_level in COMPLETE_LEVELS:
                        r.not_detected += 1  # no locus in a complete genome: possible deletion
                        r.not_detected_examples.append(it.accession)
                    else:
                        r.no_locus += 1
                elif state == "fail":
                    r.not_detected += 1
                    r.not_detected_examples.append(it.accession)
                else:
                    r.undetermined += 1
            elif member == "nontarget":
                r.nontarget_genomes += 1
                if state == "ok":
                    r.signal += 1
                    r.signal_examples.append(it.accession)
                elif state in ("fail", "none"):
                    r.silent += 1
                else:
                    r.nontarget_undetermined += 1
            else:
                r.out_of_scope_genomes += 1
                r.out_of_scope_signal += state == "ok"
        r.not_detected_examples = r.not_detected_examples[:20]
        r.signal_examples = r.signal_examples[:20]
        out.append(r)
    return out


def channels_shown(coverage: ExhaustiveCoverage | None) -> bool:
    """Whether the per-channel results add anything to the whole-assay figures: more than one
    channel, or a channel whose target differs from the scanned taxon."""
    if coverage is None or not coverage.channel_results:
        return False
    rs = coverage.channel_results
    return len(rs) > 1 or any(r.target_taxid not in (None, coverage.taxon) for r in rs)


def channel_verdict(
    r: ChannelResult, rules: Any, coverage_complete: bool = True
) -> tuple[Verdict, str]:
    """A channel's status, with a crossed limit held back while genomes are still to assess.

    The whole-assay figure and every channel are combined into the inclusivity status, and
    :func:`combine` ranks a crossed limit above INCOMPLETE, so a channel judging its own limits
    on a partial run would carry the status past the hold-back (code review, 2026-10-08). See
    :func:`hold_back`.
    """
    verdict, why, from_figure = _channel_limits(r, rules)
    if not from_figure:
        return verdict, why  # a signal outside the target cannot cross back: never held back
    held, note = hold_back(verdict, rules, coverage_complete)
    if held is not verdict:
        return held, f"{STATUS_LABEL[verdict]} on the genomes assessed so far ({why}), {note}"
    return verdict, why


def _channel_limits(r: ChannelResult, rules: Any) -> tuple[Verdict, str, bool]:
    """A channel's status over all assessed genomes (``inclusivity`` limits): below the FAIL
    limit detected FAIL, below the review limit or any signal outside its target WARN, no
    judged target genome or unknown lineages INCOMPLETE.

    The third value says whether the detection figure alone crossed a limit, which is what more
    records can still move; a signal outside the target, or an unknown lineage, cannot cross back
    and so is never held back for coverage (code review, 2026-10-08).
    """
    pct = r.detected_percent
    if r.target_genomes == 0 or pct is None:
        why = ("no genome of its target was assessed"
               + (f" ({r.membership_unknown:,} genomes without a known lineage)"
                  if r.membership_unknown else ""))  # fmt: skip
        return Verdict.INCOMPLETE, why, False
    judged = r.detected + r.not_detected
    total = judged + r.undetermined
    bracket = (
        f" ({_bracket(r.detected, r.undetermined, total, 'genomes')[:-1]})"
        if r.undetermined and total
        else ""
    )
    share = 100.0 * r.undetermined / total if total else 0.0
    if share > rules.max_undetermined_percent:
        return (
            Verdict.INCOMPLETE,
            f"{pct:.1f}% detected of {judged:,} judged, but {share:.1f}% of its target genomes "
            f"with the region are undetermined, more than {rules.max_undetermined_percent:g}%"
            f"{bracket}",
            False,
        )
    if pct < rules.fail_below_percent:
        return (
            Verdict.FAIL,
            f"{pct:.1f}% detected, below your limit of {rules.fail_below_percent:g}%{bracket}",
            True,
        )
    reasons = []
    level = Verdict.PASS
    from_figure = False
    if pct < rules.warn_below_percent:
        level = Verdict.WARN
        from_figure = True
        reasons.append(f"{pct:.1f}% detected, below your review limit of "
                       f"{rules.warn_below_percent:g}%{bracket}")  # fmt: skip
    if r.signal:
        level = Verdict.WARN
        reasons.append(f"a signal in {r.signal:,} of {r.nontarget_genomes:,} genomes outside "
                       "its target")  # fmt: skip
    if r.membership_unknown and level is Verdict.PASS:
        return (
            Verdict.INCOMPLETE,
            f"{r.membership_unknown:,} genomes without a known lineage",
            False,
        )
    # a signal alongside a figure below the limit: the figure can still move, so it is held back
    return level, "; ".join(reasons), from_figure and not r.signal


def _membership(
    ch: Channel, taxid: int | None, anc: dict[int, set[int]], scan_taxon: int | None, lookup: bool
) -> str | None:
    """target | nontarget | out_of_scope for one genome and channel; None if unknown."""
    if not lookup:
        return "target"
    lineage = anc.get(taxid) if taxid else None
    if lineage is None:
        return None
    for x in ch.taxa:
        if x.taxid in lineage:
            return "out_of_scope" if x.role == "out_of_scope" else "nontarget"
    return "target" if ch.target_taxid in lineage else "nontarget"


def _genome_channel_state(it: StoredAssembly, call: GenomeCall | None, channel: str) -> str:
    """ok | fail | undetermined | none (no locus) for one genome and channel."""
    if it.status != "found":
        return "none"
    if call is None:  # only copies cut by a contig end, or an N in a site
        return "undetermined"
    state = call.channel_state.get(channel, "fail")
    if state != "ok" and genome_outcome(call) in (
        GenomeOutcome.FROM_PARTS,
        GenomeOutcome.UNASSEMBLED,
    ):
        return "undetermined"
    if state == "ok" and genome_outcome(call) == GenomeOutcome.FROM_PARTS:
        return "undetermined"  # from parts is never counted as detected (judge_from_parts)
    return state


Collector = Callable[
    [GenomeStore, int, list[Reference]],
    tuple[list[YearCoverage], int, int, int, list[str]],
]


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
    ancestors_of: Callable[[list[int]], dict[int, set[int]]] | None = None,
) -> ExhaustiveResult:
    """Collect new assemblies (or Nucleotide records), then assess every stored one.

    ``collector`` replaces the NCBI Datasets collection (``source`` names it, e.g.
    ``blast_partitioned``); it receives the store, the taxon, the amplicon and the reference
    sequence on each side of it. Raises InputError
    or NcbiError.
    """
    taxon = assay.target.taxid
    if taxon is None:
        raise InputError("The exhaustive variant analysis needs the target's taxonomy ID.")
    if assay.target.excluded_taxids and source == "datasets":
        raise InputError(
            "Taxa left out of the target (target.taxa / exclude_taxids) are not supported "
            "with variants.source: datasets (the NCBI Datasets genome listing has no 'NOT' "
            "filter); use blast_partitioned."
        )
    if len(assay.loci) > 1:
        log.warning(
            "The assay has %d loci; the variant analysis covers only the first (%s) until the "
            "per-locus analysis is built.", len(assay.loci), assay.loci[0].name,
        )  # fmt: skip
    fetched: dict[str, str] = {}

    def fetch_once(acc: str) -> str:  # the amplicon and its context may come from one record
        if acc not in fetched:
            fetched[acc] = fetch_fasta(acc)
        return fetched[acc]

    amplicon, amp_source = reference_amplicon(assay, fetch_once)
    placed = placements(assay, amplicon, cfg)
    v = cfg.variants
    exclude = assay.target.excluded_taxids
    refs = locus_references(assay, amplicon, fetch_once, Path(cache_root) / "genomes")
    store = open_genome_store(assay, cfg, cache_root, refs, source)
    taxon = assay.loci[0].scan_taxid or taxon
    if collector is None:
        years, total, processed, failed, _f = collect(client, store, taxon, refs, cfg, now=now)
    else:
        years, total, processed, failed, _f = collector(store, taxon, refs)
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
    items, related, related_ignored, flanked = as_items(
        latest(store.items), copy_rule(cfg), store.dates
    )
    items, unassembled_fragment = fragment_not_assembled(items)
    calls: list[GenomeCall] = []
    cut: list[str] = []
    kinds: dict[str, tuple[str, str]] = {}
    sites, contig_break, masked_site = assess(
        items, assay, amplicon, placed, cfg, calls=calls, cut=cut, cut_kinds=kinds
    )
    level_of = {it.accession: it.assembly_level for it in items}
    by_kind: dict[tuple[str, str], list[str]] = defaultdict(list)
    for acc in cut:
        by_kind[kinds[acc]].append(acc)
    cut_breakdown = [
        CutReason(kind=k, label=label, genomes=len(accs), examples=accs[:10],
                  complete=sum(1 for a in accs if level_of.get(a) in COMPLETE_LEVELS))
        for (k, label), accs in sorted(by_kind.items(), key=lambda kv: -len(kv[1]))
    ]  # fmt: skip
    # the region is there but no site could be judged: undetermined in the whole fragment, as
    # in the channels (user, 2026-10-01: "both")
    unjudged = set(cut) | set(masked_site)
    typical = mark_unassembled(calls, v.multicopy_unassembled) if source == "datasets" else None
    outcomes = {c.accession: genome_outcome(c) for c in calls}
    unassembled = {a for a, o in outcomes.items() if o == GenomeOutcome.UNASSEMBLED}
    # detectable from parts and not counted as detected: undetermined in the whole-fragment outcome
    parts_undetermined = {a for a, o in outcomes.items() if o == GenomeOutcome.FROM_PARTS}
    not_found = [it for it in items if it.status == "not_found" and it.accession not in related]
    not_located = set(flanked)
    by_fallback = [it.accession for it in items if it.status == "found" and it.loci
                   and all(lc.fallback for lc in it.loci)]  # fmt: skip
    found_loci = [it.loci[0] for it in items if it.status == "found" and it.loci]
    known = [lc.on_plasmid for lc in found_loci if lc.on_plasmid is not None]
    # plasmids are a property of genome assemblies; a Nucleotide record's title is no molecule
    # label (a patent record titled "..., and plasmids" is not a plasmid)
    on_plasmid = (sum(known) * 2 >= len(known)) if known and source == "datasets" else None
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
        )
        | ({"excluded_taxids": ", ".join(map(str, exclude))} if exclude else {}),
        listed_total=total,
        assessed_total=len(items),
        processed_this_run=processed,
        download_failed_this_run=failed,
        unavailable=sum(y.unavailable for y in years),
        unavailable_examples=sorted(a for a in store.failures if store.unavailable(a))[:20],
        budget_per_run=(
            v.max_assemblies_per_run if source == "datasets" else v.blast_max_records_per_run
        ),
        found=len(sites) // len(ROLES),
        not_found=len(not_found),
        contig_break=contig_break,
        cut_reasons=cut_breakdown,
        multi_copy=sum(1 for it in items if len(it.loci) > 1),
        years=years,
        listed_at=(now or datetime.now(UTC)).isoformat(timespec="seconds"),
        not_found_examples=[it.accession for it in not_found[:20]],
        target_on_plasmid=on_plasmid,
        not_found_without_plasmid=(
            sum(1 for it in not_found if it.plasmid_contigs == 0) if source == "datasets" else 0
        ),
        not_found_with_plasmid=len(with_plasmid) if source == "datasets" else 0,
        not_found_with_plasmid_examples=(
            [it.accession for it in with_plasmid[:20]] if source == "datasets" else []
        ),
        plasmid_header_examples=(
            [x for it in items for x in it.plasmid_examples][:5] if source == "datasets" else []
        ),
        masked=len(masked_site),
        masked_examples=masked_site[:20],
        found_by_direct_scan=sum(
            1 for it in items if it.found_by == "direct_scan" and it.status == "found"
        ),
        not_checked_directly=sum(
            1 for it in not_found if it.assembly_level == "Nucleotide record"
            and it.direct_checked is False
        ),
        copies=copy_coverage(calls, assay, v.probe_channels, v.homopolymer_bulges_detectable),
        related_only=len(related),
        related_only_examples=related[:20],
        related_ignored=len(related_ignored),
        min_copy_identity=v.min_copy_identity,
        not_located=len(not_located),
        not_assembled=len(unassembled_fragment),
        not_assembled_examples=unassembled_fragment[:20],
        not_located_examples=sorted(not_located)[:20],
        found_by_fallback=len(by_fallback),
        found_by_fallback_examples=by_fallback[:20],
    )  # fmt: skip
    coverage.copies.typical_copies = typical
    coverage.channel_results = channel_results(assay, items, calls, taxon, ancestors_of)
    inclusivity = exhaustive_inclusivity(
        sites, items, years, assay, cfg, source=source,
        unassembled=unassembled, from_parts=parts_undetermined, unjudged=unjudged,
        other_rule={c.accession for c in calls if c.n_detectable_other_rule > 0},
        coverage_complete=coverage.complete,
    )  # fmt: skip
    missing = coverage.not_found + coverage.related_only
    if coverage.contig_break or coverage.masked:
        end_word = "contig" if source == "datasets" else "record"
        unit_word = "assemblies" if source == "datasets" else "records"
        inclusivity.rationale.append(
            f"{coverage.contig_break + coverage.masked} {unit_word} "
            f"carry the region but no site could be judged (cut by a {end_word} end in "
            f"{coverage.contig_break}, hidden by N in {coverage.masked}): they are counted as "
            "undetermined, in the whole fragment as in the channels."
        )
    if missing:
        unit, end, col = (
            ("assemblies", "contig", "Assemblies") if source == "datasets"
            else ("records", "record", "Records")
        )  # fmt: skip
        inclusivity.rationale.append(
            f"{missing} of {len(items)} assessed {unit} are not in the counts above: "
            f"the target region was not found in {coverage.not_found}"
            + (
                f" and only resembled by related regions in {coverage.related_only}"
                if coverage.related_only
                else ""
            )
            + " "
            f"(see the Variant summary). Per year, '{col}' minus 'With region' is that gap."
        )
    w = fragment_window(status_years(inclusivity), cfg.inclusivity.verdict_window_years)
    if w is not None and w.percent is not None and not_located:
        by_collection = inclusivity.status_axis == "collection"
        if by_collection:
            shown = [f.year for f in inclusivity.fragment_years]
            year_of = collection_bucket(items, shown)
        else:
            year_of = {it.accession: int(it.release_date[:4]) for it in items}
        k = sum(1 for acc in not_located if w.first <= year_of.get(acc, _NOT_READ) <= w.last)
        if k:
            worst = 100.0 * w.detectable / (w.n + k)
            inclusivity.rationale.append(
                f"{k} {'record' if source != 'datasets' else 'genome'}(s) "
                f"{'collected' if by_collection else 'released'} "
                f"{w.first}-{w.last} carry the sequence either side of the region but no "
                "locatable copy of the fragment (not in the counts above): if all were escapes, "
                f"{worst:.1f}% would be detectable instead of {w.percent:.1f}%."
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
