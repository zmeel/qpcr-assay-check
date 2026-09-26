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
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..align import realign
from ..config import Config, SiteRules
from ..errors import InputError
from ..inclusivity.aggregate import _stats
from ..inclusivity.models import FragmentYear, InclusivityOligoResult, InclusivityResult
from ..models import Assay, Oligo
from ..ncbi.http import NcbiError
from ..oligo import grade, iupac
from ..oligo.amplicon import find_sites
from ..specificity.models import SiteResult
from ..specificity.sites import _result_fields
from ..verdict import Verdict
from .datasets import AssemblyRecord, DatasetsClient, parse_fasta, parse_fasta_records
from .locate import CONTEXT_NT, scan_region
from .models import (
    ChannelCoverageRow,
    CopyCoverage,
    ExhaustiveCoverage,
    OligoCoverageRow,
    RunLengthBreakdown,
    YearCoverage,
)
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


class ReferenceContext:
    """The reference sequence just before and after the amplicon (sense), from the accession.

    Used only to recognise a region wholly hidden by N, so it is fetched on first use (the first
    record in which the amplicon is not found) and kept in ``cache_file`` for later runs.
    ``("", "")`` when the assay names no accession, the fetch fails (retried next run), or the
    amplicon is not in the accession exactly: a wholly masked region then stays 'not found'.
    """

    def __init__(
        self, assay: Assay, amplicon: str, fetch_fasta: Callable[[str], str], cache_file: Path
    ) -> None:
        self.acc = assay.target.accession or ""
        self.amplicon = amplicon.upper()
        self.fetch_fasta = fetch_fasta
        self.cache_file = cache_file
        self._value: tuple[str, str] | None = None
        self.other_amplicons: list[str] = []  # further reference amplicons (other lineages)

    def __call__(self) -> tuple[str, str]:
        if self._value is None:
            self._value = self._load()
        return self._value

    def _load(self) -> tuple[str, str]:
        if not self.acc:
            return "", ""
        try:
            cached = json.loads(self.cache_file.read_text(encoding="utf-8"))
            if cached.get("accession") == self.acc:
                return cached["left"], cached["right"]
        except (OSError, ValueError, KeyError):
            pass
        try:
            ctx = reference_context(self.amplicon, parse_fasta(self.fetch_fasta(self.acc)))
        except NcbiError as exc:
            log.warning("Could not fetch %s for the sequence around the amplicon: %s", self.acc,
                        exc)  # fmt: skip
            return "", ""
        if not any(ctx):
            log.warning(
                "The reference amplicon is not in %s exactly; a region wholly hidden by N will "
                "be reported as not found.", self.acc,
            )  # fmt: skip
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(
            json.dumps({"accession": self.acc, "left": ctx[0], "right": ctx[1]}), encoding="utf-8"
        )
        return ctx


def reference_context(amplicon: str, seqs: dict[str, str]) -> tuple[str, str]:
    """Up to ``CONTEXT_NT`` bases before and after the first exact copy of the amplicon."""
    amp = amplicon.upper()
    for seq in seqs.values():
        for s in (seq.upper(), iupac.reverse_complement(seq.upper())):
            i = s.find(amp)
            if i >= 0:
                return s[max(0, i - CONTEXT_NT) : i], s[i + len(amp) : i + len(amp) + CONTEXT_NT]
    return "", ""


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
    store: RegionStore,
    taxon: int,
    amplicon: str,
    cfg: Config,
    *,
    now: datetime | None = None,
    context: Callable[[], tuple[str, str]] | None = None,
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
                for rec in client.year(taxon, year, **flt):
                    if store.done(rec.accession):
                        continue
                    pending.append(rec)
                    if processed + len(pending) >= budget:
                        break
                stored = sum(
                    1 for it in store.items.values() if it.year == year and store.done(it.accession)
                )
                log.info(
                    "%d: %d assemblies listed, %d already stored, %d to scan in this run%s",
                    year, n_year, stored, len(pending),
                    " (the per-run maximum is reached; the rest follow on later runs)"
                    if processed + len(pending) >= budget else "",
                )  # fmt: skip
                p, f, accs = _process(client, store, pending, amplicon, cfg, context)
                processed, failed = processed + p, failed + f
                failed_accessions += accs
            assessed = sum(1 for it in store.items.values() if it.year == year)
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
    store: RegionStore,
    records: list[AssemblyRecord],
    amplicon: str,
    cfg: Config,
    context: Callable[[], tuple[str, str]] | None = None,
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
                store.record_failure(rec.accession)
                continue
            records_ = parse_fasta_records(fasta)
            contigs = {name: seq for name, (_d, seq) in records_.items()}
            kw = {"seed_length": v.seed_length, "seed_step": v.seed_step, "flank": v.flank_nt}
            others = getattr(context, "other_amplicons", [])
            loci, masked, ref = scan_region(
                contigs, amplicon, context, other_amplicons=others, **kw
            )
            store.add(rec, loci, {name: d for name, (d, _s) in records_.items()}, masked=masked,
                      context_checked=context is not None and any(context()), ref=ref,
                      refs_checked=1 + len(others))  # fmt: skip
            done += 1
        log.info("  %d / %d assemblies scanned in this run", i + len(chunk), len(records))
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

    @property
    def undetermined(self) -> bool:
        """No detectable copy, but no failing role either: only sites without a published basis
        (e.g. a mismatch in an MGB probe); counted neither as detected nor as an escape."""
        states = set(self.role_state.values())
        return self.n_detectable == 0 and "fail" not in states and "undetermined" in states


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
) -> tuple[list[SiteResult], int, list[str]]:
    """One site per role per genome, from the copy of the region the assay binds best.

    Every stored copy is assessed with every alternative oligo of each role (the best one of a
    role binds). A copy is ranked by how many roles are detectable there, then by total
    mismatches and gaps; the genome is judged by its best copy, as a PCR needs only one copy it
    can amplify. ``sites_in_amplicon`` gives the oligo windows per reference amplicon (a locus
    records which reference found it). ``calls``, if given, collects each genome's
    :class:`GenomeCall` (copies, per-oligo coverage). Returns the sites, the number of genomes
    whose only copies are cut by a contig end, and the genomes whose best copy has an N in an
    oligo site (masked, not assessed).
    """
    per_ref = sites_in_amplicon if isinstance(sites_in_amplicon, list) else [sites_in_amplicon]
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    memo: dict[tuple[str, str], tuple[realign.Alignment, str]] = {}
    channel_rule = cfg.variants.probe_channels
    bulges = cfg.variants.homopolymer_bulges_detectable
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
        if not copies:
            contig_break += 1
            continue
        best_i = min(range(len(copies)), key=lambda i: _copy_key(copies[i][0], bulges))
        chosen, all_sites = copies[best_i]
        if any("N" in s.s_aln.upper() for s in chosen.values()):
            masked_site.append(it.accession)  # an N is neither a match nor a variant
            continue
        for role in ROLES:
            n += 1
            sites.append(chosen[role].model_copy(update={"id": f"V{n}"}))
        if calls is not None:
            calls.append(
                GenomeCall(
                    accession=it.accession,
                    n_copies=len(copies),
                    n_detectable=sum(all(roles_ok(c, bulges).values()) for c, _a in copies),
                    best_is_first=best_i == 0,
                    n_detectable_other_rule=sum(
                        all(
                            roles_ok(
                                {
                                    r: _role_site(assay, r, a, channel_rule, not bulges)
                                    for r in ROLES
                                },
                                not bulges,
                            ).values()
                        )
                        for _c, a in copies
                    ),  # fmt: skip
                    oligo_good={name: detectable(x, bulges) for name, x in all_sites.items()},
                    role_good=roles_ok(chosen, bulges),
                    role_state=roles_state(chosen, bulges),
                    assembly_level=it.assembly_level,
                    **_run_length_fields([c for c, _a in copies], chosen),
                )
            )
    return sites, contig_break, masked_site


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
    if graded and grade.pair_fails(fwd.n_mismatch, rev.n_mismatch):  # type: ignore[union-attr]
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
        strand, start, end = windows[role]
        # the site +- SITE_PAD, clamped to the region (a full-length BLAST hit carries no
        # flanks); a site that itself runs off the region cannot be assessed
        if locus.offset + start - 1 < 0 or locus.offset + end > len(locus.region):
            return None
        lo = max(0, locus.offset + start - 1 - SITE_PAD)
        hi = min(len(locus.region), locus.offset + end + SITE_PAD)
        window = locus.region[lo:hi]
        oriented = window if strand == "+" else iupac.reverse_complement(window)
        rules = cfg.specificity.probe_site if role == "probe" else cfg.specificity.primer_site
        for o in assay.by_role(role):  # alternatives in one mix
            key = (o.sequence.upper(), oriented)
            if key not in memo:
                memo[key] = _align(key[0], oriented, scoring, rules)
            aln, note = memo[key]
            site = _site(it, locus, o, strand, lo, len(window), aln, rules, 0, note)
            every[o.name] = assay.graded(site)
        chosen[role] = _role_site(assay, role, every, channel_rule, bulges)
    return chosen, every


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

    if role != "probe" or channel_rule == "any":
        return min((every[o.name] for o in members), key=key)
    channels: dict[str, list[SiteResult]] = defaultdict(list)
    for o in members:
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
    escapes = [c.accession for c in calls if not all(c.role_good.values()) and not c.undetermined]
    out.escapes, out.escape_examples = len(escapes), escapes[:20]
    undet = [c.accession for c in calls if c.undetermined]
    out.undetermined, out.undetermined_examples = len(undet), undet[:20]
    for role in ROLES:
        members = assay.by_role(role)
        for o in members:
            others = [x.name for x in members if x.name != o.name]
            out.oligos.append(
                OligoCoverageRow(
                    role=role,
                    name=o.name,
                    reporter=o.reporter if role == "probe" else None,
                    covered=sum(c.oligo_good.get(o.name, False) for c in calls),
                    only=sum(
                        c.oligo_good.get(o.name, False)
                        and not any(c.oligo_good.get(x, False) for x in others)
                        for c in calls
                    ),
                )  # fmt: skip
            )
        uncovered = [c for c in calls
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
                covered=sum(any(c.oligo_good.get(x, False) for x in names) for c in calls),
            )  # fmt: skip
        )
    per_genome = [
        [any(c.oligo_good.get(x, False) for x in names) for names in channels.values()]
        for c in calls
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
    shown: list[int], bulges: bool,
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
        if outcome == "detectable":
            row.detectable += 1
        elif outcome == "at risk":
            row.at_risk += 1
        elif outcome == "likely failure":
            row.likely_failure += 1
            row.by_pair_rule += by_pair
        elif outcome == "undetermined":
            row.undetermined += 1
    return [out[y] for y in shown]


def fragment_verdict(years: list[FragmentYear], rules: Any) -> tuple[Verdict, list[str]]:
    """The inclusivity verdict from the whole-fragment genome outcome (advisor subagent,
    2026-09-26): pooled over the last ``verdict_window_years`` complete release years plus the
    current one, undetermined genomes left out of the denominator, at risk counted as not
    detected; too few genomes in the window is INCOMPLETE; a single year with at least
    ``min_genomes_per_year`` genomes below ``fail_below_percent`` gives at least WARN. The
    per-oligo figures are diagnostics only."""
    with_data = [y for y in years if y.with_region]
    if not with_data:
        return Verdict.INCOMPLETE, ["No genome with the target region in the years shown."]
    last = max(y.year for y in with_data)
    window = [y for y in years if last - rules.verdict_window_years <= y.year <= last]
    n_region = sum(y.with_region for y in window)
    undet = sum(y.undetermined for y in window)
    n = n_region - undet
    det = sum(y.detectable for y in window)
    risk = sum(y.at_risk for y in window)
    fail = sum(y.likely_failure for y in window)
    span = f"{min(y.year for y in window)}-{last}"
    if n < rules.min_genomes_for_verdict:
        return Verdict.INCOMPLETE, [
            f"Too few recent genomes to judge: {n} with the target region released {span} "
            f"(at least {rules.min_genomes_for_verdict} needed; setting "
            "inclusivity.min_genomes_for_verdict)."
        ]
    pct = 100.0 * det / n
    lines = [
        f"Whole fragment, genomes released {span}: {pct:.1f}% detectable (perfect or "
        f"tolerated), {100.0 * (det + risk) / n:.1f}% including at risk, "
        f"{100.0 * fail / n:.1f}% likely failure, of {n} genomes with the target region "
        f"(undetermined, not counted: {undet}). The per-oligo and per-year figures are "
        "diagnostics; the verdict uses the whole fragment over this window."
    ]
    if pct < rules.fail_below_percent:
        verdict = Verdict.FAIL
    elif pct < rules.warn_below_percent:
        verdict = Verdict.WARN
    else:
        verdict = Verdict.PASS
    lines[0] += f" Verdict {verdict.value}" + (
        f" (below {rules.warn_below_percent:g}%)." if verdict is not Verdict.PASS else "."
    )
    if verdict is Verdict.FAIL:  # a single low year cannot make the verdict worse
        return verdict, lines
    for y in years:
        n_y = y.with_region - y.undetermined
        if n_y >= rules.min_genomes_per_year:
            p_y = 100.0 * y.detectable / n_y
            if p_y < rules.fail_below_percent:
                lines.append(
                    f"Release year {y.year} on its own: {p_y:.1f}% detectable of {n_y} genomes, "
                    f"below the FAIL limit ({rules.fail_below_percent:g}%); at least WARN."
                )
                verdict = Verdict.WARN
    return verdict, lines


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
                   max(len(o.sequence) for o in assay.by_role(role)))
            for y in shown
        ]  # fmt: skip
        oligo = " / ".join(o.sequence for o in assay.by_role(role))
        oligos.append(InclusivityOligoResult(role=role, oligo=oligo, windows=windows))
    fragment_years = _fragment_years(
        sites, year_of, listed, shown, cfg.variants.homopolymer_bulges_detectable
    )
    verdict, rationale = fragment_verdict(fragment_years, cfg.inclusivity)
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
            " and 'With region' the number in which the target region was found and assessed. "
            "Not a sample: the gap between the two is explained below (region not found, hidden "
            "by N, cut by a "
            + ("contig" if source == "datasets" else "record")
            + " end, or not processed yet)."
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


def open_store(
    assay: Assay, cfg: Config, cache_root: Path, amplicon: str, source: str
) -> RegionStore:
    """The assay's region store (keyed by the first reference only, so adding a lineage
    reference keeps the stored regions)."""
    taxon = assay.target.taxid
    if taxon is None:
        raise InputError("The exhaustive variant analysis needs the target's taxonomy ID.")
    path = store_path(
        cache_root, taxon, amplicon, cfg.variants.flank_nt, source, assay.target.excluded_taxids
    )
    store = RegionStore(path)
    store.n_refs = len(assay.reference_amplicons) or 1
    return store


def stored_calls(
    assay: Assay,
    cfg: Config,
    cache_root: Path,
    fetch_fasta: Callable[[str], str],
    source: str,
) -> tuple[list[StoredAssembly], list[GenomeCall], Path]:
    """Every genome already in the assay's region store, judged by its best copy (no new
    downloads): the stored items, one :class:`GenomeCall` per genome with a complete copy, and
    the store's path. ``fetch_fasta`` is only used when the assay has no reference amplicon."""
    amplicon, _src = reference_amplicon(assay, fetch_fasta)
    store = open_store(assay, cfg, cache_root, amplicon, source)
    items = current_items(store)
    calls: list[GenomeCall] = []
    assess(items, assay, amplicon, placements(assay, amplicon, cfg), cfg, calls=calls)
    return items, calls, store.path


Collector = Callable[
    [RegionStore, int, str, Callable[[], tuple[str, str]]],
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
    fetched: dict[str, str] = {}

    def fetch_once(acc: str) -> str:  # the amplicon and its context come from one record
        if acc not in fetched:
            fetched[acc] = fetch_fasta(acc)
        return fetched[acc]

    amplicon, amp_source = reference_amplicon(assay, fetch_once)
    others = [r.sequence.upper() for r in assay.reference_amplicons[1:]]
    placed = placements(assay, amplicon, cfg)
    v = cfg.variants
    exclude = assay.target.excluded_taxids
    store = open_store(assay, cfg, cache_root, amplicon, source)
    context = ReferenceContext(assay, amplicon, fetch_once, store.path.with_suffix(".context.json"))
    context.other_amplicons = others
    if collector is None:
        years, total, processed, failed, _f = collect(
            client, store, taxon, amplicon, cfg, now=now, context=context
        )
    else:
        years, total, processed, failed, _f = collector(store, taxon, amplicon, context)
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
    calls: list[GenomeCall] = []
    sites, contig_break, masked_site = assess(items, assay, amplicon, placed, cfg, calls=calls)
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
        copies=copy_coverage(calls, assay, v.probe_channels, v.homopolymer_bulges_detectable),
    )  # fmt: skip
    coverage.copies.copies_capped = sum(1 for it in items if it.copies_capped)
    inclusivity = exhaustive_inclusivity(sites, items, years, assay, cfg, source=source)
    missing = coverage.not_found + coverage.contig_break + coverage.masked
    if missing:
        unit, end, col = (
            ("assemblies", "contig", "Assemblies") if source == "datasets"
            else ("records", "record", "Records")
        )  # fmt: skip
        inclusivity.rationale.append(
            f"{missing} of {len(items)} assessed {unit} are not in the counts above: "
            f"the target region was not found in {coverage.not_found}, was hidden by N in "
            f"{coverage.masked} and was cut by a {end} end in {coverage.contig_break} "
            f"(see the Variant summary). Per year, '{col}' minus 'With region' is that gap."
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
