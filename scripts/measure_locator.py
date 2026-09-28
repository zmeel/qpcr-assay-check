#!/usr/bin/env python3
"""Measure the current copy locator against a prototype chain locator, on real genomes.  (step 0)

WHY THIS EXISTS
    The exhaustive variant analysis finds each copy of the amplicon region through exact 16-mer
    seeds, groups seeds whose implied starts lie within 20 nt, and (since v1.6) sets a region
    aside as "related, not the target" when its identity to the reference amplicon is below
    variants.min_copy_identity (0.75). On the Legionella run that set aside real copies of
    L. longbeachae and L. dumoffii (identity 0.59-0.74). The planned overhaul replaces this with
    CHAINS of exact blocks (same order on the reference and the genome) and a copy rule
    "anchored bases M >= 32 OR identity >= 0.75". The numbers behind that rule are estimates.
    This script measures them before any default is chosen; it changes nothing in the tool.

    Per genome it reports, for every candidate region:
      * the prototype chain: exact blocks, anchored bases inside the amplicon (M) at seed step
        1, 2 and 4, the implied amplicon start/end (signed; negative = cut by the contig start),
        the length difference to the reference amplicon, N next to and inside the copy, and the
        identity measured along the chain (band widened by the length difference);
      * the current locator's loci matched to it (seeds, identity as stored, how many loci one
        copy was split into);
      * per oligo: mismatches at the site the chain places it vs the site the current single
        offset places it (a difference is a suspected false escape).
    And per genome: sequences, length, N, gaps (N runs >= 10), seconds per method, and a NULL:
    the same chaining with shuffled and reversed copies of the reference amplicon (no homology),
    to see how large M gets by chance in a real genome.

WHAT IT SENDS TO NCBI
    Genome downloads from NCBI Datasets (assemblies; variants.source datasets) or E-utilities
    EFetch FASTA (Nucleotide records; other sources), in small batches, with the tool's own
    throttling and backoff. Optionally one EFetch of --context-accession and one probe of the
    Datasets sequence-report endpoint (--probe-sequence-report). Your NCBI_EMAIL is sent as NCBI
    requires; it is never written to the output. Genomes are held in memory only, one batch at a
    time, and never written to disk (project rule); the report holds coordinates and numbers,
    no sequences.

HOW TO RUN (repository root, after `pip install -e .`)
    export NCBI_EMAIL="your.name@example.org"
    export NCBI_API_KEY="..."                # optional
    mkdir -p measure_out

    # Legionella (the store of your last run is read to pick genomes; nothing is re-downloaded
    # for the store itself):
    nohup python scripts/measure_locator.py --assay <your Legionella assay.yaml> \\
        --group related --group single-seed --group organism:anisa --group organism:micdadei \\
        --group organism:longbeachae --group organism:dumoffii --group sample \\
        --accessions GCF_000176095.1,GCF_000236165.1,GCF_000586155.1 \\
        --context-accession <a complete L. pneumophila genome of your choice, optional> \\
        --probe-sequence-report GCF_000586155.1 \\
        --outdir measure_out/legionella > measure_out/legionella.log 2>&1 &

    # Neisseria:
    ... --assay <Neisseria assay.yaml> --group related --group single-seed --group sample \\
        --accessions GCF_000156755.1,GCF_013030075.1 --outdir measure_out/neisseria

    # Enterovirus (Nucleotide records, variants.source blast_partitioned):
    ... --assay <enterovirus assay.yaml> --group related --group sample \\
        --group organism:D68 --group organism:A71 --group organism:polio --outdir measure_out/ev

    Groups: related (found, but every stored copy below min_copy_identity), single-seed (best
    stored copy found by one seed), not-found, sample (random found genomes), organism:TEXT
    (organism name contains TEXT). --per-group N (default 25) and --max-genomes N (default 200)
    bound the downloads. Time: about 15-20 s per bacterial genome on one core (most of it the
    null; --null 0 halves it) plus the download, so 200 genomes take about an hour.
    Other options: --config FILE, --max-indel N (default 150), --null N (shuffled references
    per genome, default 2), --rule-m 32, --rule-identity 0.75.

WHAT TO PASTE BACK
    <outdir>/measure_report.json (no secrets). It is rewritten after every genome, so it can be
    pasted while the script still runs. If it is too large, paste its "summary" section and the
    rows of the named accessions.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import statistics
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qpcr_assay_check import __version__
from qpcr_assay_check.cli import build_assay
from qpcr_assay_check.config import Config, load_config
from qpcr_assay_check.errors import QpcrAssayCheckError
from qpcr_assay_check.models import Assay
from qpcr_assay_check.oligo import iupac
from qpcr_assay_check.oligo.amplicon import find_sites
from qpcr_assay_check.variants.datasets import parse_fasta, parse_fasta_records
from qpcr_assay_check.variants.exhaustive import SITE_PAD, current_items, reference_context
from qpcr_assay_check.variants.locate import (
    INDEL_TOLERANCE,
    Locus,
    _occurrences,
    amplicon_identity,
    find_loci,
    locus_identity,
)
from qpcr_assay_check.variants.store import RegionStore, StoredAssembly, store_path

log = logging.getLogger("measure_locator")

ACGT = frozenset("ACGT")
CONTEXT_STEP = 8  # seed step in the reference context (as locate.CONTEXT_SEED_STEP)
STEPS = (1, 2, 4)  # seed steps measured inside the amplicon (4 = the current default)
MAX_CANDIDATES = 60  # per genome in the report; the rest are counted
MIN_CONTEXT_ONLY_M = 48  # a chain that anchors only in the context is reported from this size
GAP_RE = re.compile("N{10,}")
M_BINS = ((0, 24), (24, 32), (32, 48), (48, 96), (96, 10**9))
ID_BINS = ((0.0, 0.65), (0.65, 0.75), (0.75, 1.01))


# ------------------------------------------------------------------ prototype chain locator
@dataclass
class Block:
    """An exact match: reference ``[r0, r1)`` equals sequence ``[s0, s0 + r1 - r0)``."""

    r0: int
    r1: int
    s0: int

    @property
    def s1(self) -> int:
        return self.s0 + self.r1 - self.r0

    @property
    def diag(self) -> int:
        return self.s0 - self.r0


@dataclass
class Chain:
    """Co-linear exact blocks on one sequence (a contig or its reverse complement)."""

    blocks: list[Block]

    def anchored(self, lo: int, hi: int) -> int:
        """Reference bases in ``[lo, hi)`` covered by the blocks (union)."""
        spans = sorted((max(lo, b.r0), min(hi, b.r1)) for b in self.blocks)
        total, end = 0, lo
        for a, b in spans:
            if b <= a:
                continue
            a = max(a, end)
            if b > a:
                total, end = total + b - a, b
        return total

    def place(self, r: int) -> int:
        """Where reference position ``r`` lies on the sequence, through the nearest block
        (signed: may be before 0 or past the sequence end)."""
        best = min(
            self.blocks, key=lambda b: 0 if b.r0 <= r < b.r1 else min(abs(r - b.r0), abs(r - b.r1))
        )
        return best.s0 + (r - best.r0)


def seed_positions(ref_len: int, k: int, amp_lo: int, amp_hi: int, step: int) -> list[int]:
    """Seed starts: every ``step`` inside the amplicon (plus its last k-mer), every
    ``CONTEXT_STEP`` in the context on either side."""
    pos = set(range(amp_lo, amp_hi - k + 1, step))
    if amp_hi - k >= amp_lo:
        pos.add(amp_hi - k)
    pos |= set(range(0, amp_lo - k + 1, CONTEXT_STEP))
    pos |= set(range(amp_hi, ref_len - k + 1, CONTEXT_STEP))
    return sorted(pos)


def find_blocks(seq: str, ref: str, positions: Iterable[int], k: int) -> list[Block]:
    """Exact seed hits of ``ref`` in ``seq``, merged into maximal blocks per diagonal."""
    hits: list[tuple[int, int]] = []
    for p in positions:
        kmer = ref[p : p + k]
        if len(kmer) < k or not set(kmer) <= ACGT:
            continue
        hits.extend((s - p, p) for s in _occurrences(seq, kmer))
    hits.sort()
    blocks: list[Block] = []
    for d, p in hits:
        last = blocks[-1] if blocks else None
        if last is not None and last.diag == d and p <= last.r1:
            last.r1 = max(last.r1, p + k)
        else:
            blocks.append(Block(p, p + k, p + d))
    return blocks


def chain_blocks(blocks: list[Block], max_indel: int, max_gap: int) -> list[Chain]:
    """Greedy best chains (most anchored bases first) inside local groups of blocks."""
    out: list[Chain] = []
    group: list[Block] = []
    end = -(10**12)
    for b in sorted(blocks, key=lambda x: (x.s0, x.r0)):
        if group and b.s0 - end > max_gap:
            out += _chains(group, max_indel)
            group = []
        group.append(b)
        end = max(end, b.s1) if len(group) > 1 else b.s1
    if group:
        out += _chains(group, max_indel)
    return out


def _chains(group: list[Block], max_indel: int) -> list[Chain]:
    left = list(group)
    out: list[Chain] = []
    while left:
        n = len(left)
        score = [b.r1 - b.r0 for b in left]
        prev = [-1] * n
        for j in range(n):
            bj = left[j]
            for i in range(j):
                bi = left[i]
                if bj.r0 <= bi.r0 or bj.s0 <= bi.s0 or abs(bj.diag - bi.diag) > max_indel:
                    continue
                gain = (bj.r1 - bj.r0) - max(0, bi.r1 - bj.r0, bi.s1 - bj.s0)
                if gain > 0 and score[i] + gain > score[j]:
                    score[j], prev[j] = score[i] + gain, i
        j = max(range(n), key=lambda x: score[x])
        picked: list[int] = []
        while j != -1:
            picked.append(j)
            j = prev[j]
        out.append(Chain([left[i] for i in reversed(picked)]))
        left = [b for i, b in enumerate(left) if i not in set(picked)]
    return out


def locate_chains(
    contigs: dict[str, str], ref: str, amp_lo: int, amp_hi: int, *, k: int, step: int,
    max_indel: int,
) -> list[tuple[str, str, str, Chain]]:  # fmt: skip
    """``(contig, strand, sense sequence, chain)`` for every chain touching the reference."""
    positions = seed_positions(len(ref), k, amp_lo, amp_hi, step)
    max_gap = (amp_hi - amp_lo) + max_indel
    out = []
    for name, seq in contigs.items():
        for strand, s in (("+", seq), ("-", iupac.reverse_complement(seq))):
            for ch in chain_blocks(find_blocks(s, ref, positions, k), max_indel, max_gap):
                out.append((name, strand, s, ch))
    return out


# ------------------------------------------------------------------ measuring one genome
def _n_run_left(s: str, at: int) -> int:
    i = min(max(at, 0), len(s)) - 1
    n = 0
    while i >= 0 and s[i] == "N":
        n, i = n + 1, i - 1
    return n


def _n_run_right(s: str, at: int) -> int:
    i, n = max(min(at, len(s)), 0), 0
    while i < len(s) and s[i] == "N":
        n, i = n + 1, i + 1
    return n


def best_mismatches(s: str, pos: int, site: str) -> int | None:
    """Fewest mismatches of ``site`` (sense orientation) within ``SITE_PAD`` of ``pos``; None
    when the sequence does not cover a whole site there."""
    lo, hi = max(0, pos - SITE_PAD), min(len(s), pos + len(site) + SITE_PAD)
    counts = [iupac.count_mismatches(site, s[i : i + len(site)])
              for i in range(lo, hi - len(site) + 1)]  # fmt: skip
    return min(counts) if counts else None


def current_start(lc: Locus, contig_len: int) -> int:
    """The amplicon start the current locator implies, on the sense sequence."""
    lo = lc.start - 1 if lc.strand == "+" else contig_len - lc.end
    return lo + lc.offset


@dataclass
class Oligo:
    name: str
    role: str
    at: int  # 0-based start in the reference amplicon (sense)
    site: str  # the oligo as it reads on the amplicon's sense strand


def oligo_sites(assay: Assay, amplicon: str, max_mm: int) -> list[Oligo]:
    """Each oligo that fits the reference amplicon, with its sense-strand site."""
    out = []
    for role in ("forward", "reverse", "probe"):
        for o in assay.by_role(role):
            hits = find_sites(amplicon, o.sequence.upper(), o.name, max_mismatches=max_mm)
            if hits:
                h = hits[0]
                seq = o.sequence.upper()
                out.append(
                    Oligo(
                        o.name,
                        role,
                        h.start - 1,
                        seq if h.strand == "+" else iupac.reverse_complement(seq),
                    )
                )
    return out


def measure_genome(
    contigs: dict[str, str],
    refs: list[str],
    context: tuple[str, str],
    oligos: list[list[Oligo]],
    *,
    k: int,
    current_step: int,
    flank: int,
    max_indel: int,
    n_null: int,
    rule_m: int,
    rule_identity: float,
    min_copy_identity: float,
) -> dict[str, Any]:
    """Every measurement for one genome (see the module docstring)."""
    lengths = {name: len(s) for name, s in contigs.items()}
    row: dict[str, Any] = {
        "n_sequences": len(contigs),
        "total_length": sum(lengths.values()),
        "total_N": sum(s.count("N") for s in contigs.values()),
        "n_gaps": sum(len(GAP_RE.findall(s)) for s in contigs.values()),
        "seconds": {},
    }
    # the current locator, every reference (as scan_region would try them)
    t = time.perf_counter()
    current: list[tuple[int, Locus, float]] = []
    for i, amp in enumerate(refs):
        for lc in find_loci(contigs, amp, seed_length=k, seed_step=current_step, flank=flank):
            current.append((i, lc, round(locus_identity(lc, amp, k), 3)))
    row["seconds"]["current"] = round(time.perf_counter() - t, 3)

    candidates: list[dict[str, Any]] = []
    matched: set[int] = set()
    for ri, amp in enumerate(refs):
        left, right = context if ri == 0 else ("", "")
        ref = left + amp + right
        lo, hi = len(left), len(left) + len(amp)
        by_step: dict[int, list[tuple[str, str, str, Chain]]] = {}
        for step in STEPS:
            t = time.perf_counter()
            by_step[step] = locate_chains(contigs, ref, lo, hi, k=k, step=step,
                                          max_indel=max_indel)  # fmt: skip
            row["seconds"][f"chain_step{step}_ref{ri}"] = round(time.perf_counter() - t, 3)
        for contig, strand, s, ch in by_step[1]:
            m_amp = ch.anchored(lo, hi)
            if m_amp == 0 and ch.anchored(0, len(ref)) < MIN_CONTEXT_ONLY_M:
                continue
            a0, a1 = ch.place(lo), ch.place(hi)
            cand: dict[str, Any] = {
                "ref": ri, "contig": contig, "strand": strand, "contig_len": len(s),
                "n_blocks": len(ch.blocks), "M_amp": {1: m_amp}, "M_all": ch.anchored(0, len(ref)),
                "context_only": m_amp == 0, "amp_start": a0, "amp_end": a1,
                "length_diff": (a1 - a0) - len(amp), "cut_left": a0 < 0, "cut_right": a1 > len(s),
                "dist_to_start": a0, "dist_to_end": len(s) - a1,
                "N_left": _n_run_left(s, a0), "N_right": _n_run_right(s, a1),
                "N_inside": s[max(0, a0) : max(0, min(len(s), a1))].count("N"),
            }  # fmt: skip
            for step in STEPS[1:]:  # the same copy found with sparser seeds
                same = [c for cn, st, _s, c in by_step[step]
                        if cn == contig and st == strand and _overlap(c, ch)]  # fmt: skip
                cand["M_amp"][step] = max((c.anchored(lo, hi) for c in same), default=0)
            if m_amp:
                pad = abs(cand["length_diff"]) + INDEL_TOLERANCE
                w0 = max(0, a0 - pad)
                region = s[w0 : max(w0, a1 + pad)]
                band = max(INDEL_TOLERANCE, abs(cand["length_diff"]) + INDEL_TOLERANCE)
                cand["identity_chain"] = round(amplicon_identity(region, amp, a0 - w0, band)[0], 3)
            # the current loci of this copy
            cur = []
            for idx, (ci, lc, ident) in enumerate(current):
                if ci != ri or lc.contig != contig or lc.strand != strand:
                    continue
                c0 = current_start(lc, len(s))
                if c0 < a1 + INDEL_TOLERANCE and c0 + len(amp) > a0 - INDEL_TOLERANCE:
                    cur.append((idx, lc, ident, c0))
                    matched.add(idx)
            cand["current"] = [
                {"n_seeds": lc.n_seeds, "identity": ident, "start": c0, "truncated": lc.truncated}
                for _i, lc, ident, c0 in cur
            ]
            cand["current_split"] = len(cur) > 1
            best_cur = max(cur, key=lambda x: x[1].n_seeds, default=None)
            sites = []
            for o in oligos[ri]:
                p_chain = ch.place(lo + o.at)
                site: dict[str, Any] = {
                    "oligo": o.name,
                    "role": o.role,
                    "mm_chain": best_mismatches(s, p_chain, o.site),
                }
                if best_cur is not None:
                    p_cur = best_cur[3] + o.at
                    site["mm_current"] = best_mismatches(s, p_cur, o.site)
                    site["placement_diff"] = p_chain - p_cur
                sites.append(site)
            cand["sites"] = sites
            cand["copy_by_rule"] = bool(m_amp) and (
                m_amp >= rule_m or cand.get("identity_chain", 0.0) >= rule_identity
            )
            candidates.append(cand)
    candidates.sort(key=lambda c: (-c["M_amp"][1], c["contig"], c["amp_start"]))
    row["n_candidates"] = len(candidates)
    row["candidates"] = candidates[:MAX_CANDIDATES]
    row["current_unmatched"] = [
        {"ref": ci, "contig": lc.contig, "strand": lc.strand, "n_seeds": lc.n_seeds,
         "identity": ident}
        for idx, (ci, lc, ident) in enumerate(current) if idx not in matched
    ]  # fmt: skip
    row["copy_current"] = any(ident >= min_copy_identity for _i, _lc, ident in current)
    row["copy_chain"] = any(c["copy_by_rule"] for c in candidates)
    row["best_M_amp"] = max((c["M_amp"][1] for c in candidates), default=0)
    row["best_identity_chain"] = max((c.get("identity_chain", 0.0) for c in candidates),
                                     default=0.0)  # fmt: skip
    row["null_max_M"] = null_max_m(contigs, refs[0], k=k, max_indel=max_indel, n=n_null)
    return row


def _overlap(a: Chain, b: Chain) -> bool:
    return min(a.blocks[-1].s1, b.blocks[-1].s1) > max(a.blocks[0].s0, b.blocks[0].s0)


def null_max_m(contigs: dict[str, str], amp: str, *, k: int, max_indel: int, n: int) -> list[int]:
    """Largest M of any chain for references without homology: ``n`` shuffles of the amplicon
    (fixed seeds, reproducible) and the amplicon reversed (not complemented)."""
    decoys = ["".join(random.Random(i).sample(amp, len(amp))) for i in range(n)] + [amp[::-1]]
    out = []
    for d in decoys:
        chains = locate_chains(contigs, d, 0, len(d), k=k, step=1, max_indel=max_indel)
        out.append(max((ch.anchored(0, len(d)) for *_x, ch in chains), default=0))
    return out


# ------------------------------------------------------------------ choosing genomes
def select(items: list[StoredAssembly], groups: list[str], refs: list[str], k: int,
           min_identity: float, per_group: int) -> dict[str, list[str]]:  # fmt: skip
    """Accessions per group, from the region store (deterministic)."""
    rng = random.Random(1)
    found = [it for it in items if it.status == "found" and it.loci]

    def identity(it: StoredAssembly) -> float:
        vals = []
        for lc in it.loci:
            if lc.identity is not None:
                vals.append(lc.identity)
            elif lc.ref < len(refs):
                vals.append(locus_identity(lc, refs[lc.ref], k))
        return max(vals, default=0.0)

    out: dict[str, list[str]] = {}
    for g in groups:
        if g == "related":
            pool = [it for it in found if identity(it) < min_identity]
        elif g == "single-seed":
            pool = [it for it in found if max(lc.n_seeds for lc in it.loci) == 1]
        elif g == "not-found":
            pool = [it for it in items if it.status == "not_found"]
        elif g == "sample":
            pool = list(found)
        elif g.startswith("organism:"):
            text = g.split(":", 1)[1].lower()
            pool = [it for it in items if text in it.organism.lower()]
        else:
            raise SystemExit(f"unknown group {g!r}")
        pool.sort(key=lambda it: it.accession)
        rng.shuffle(pool)
        out[g] = [it.accession for it in pool[:per_group]]
        log.info("group %s: %d in the store, %d taken", g, len(pool), len(out[g]))
    return out


# ------------------------------------------------------------------ summary
def _bin(value: float, bins: tuple[tuple[float, float], ...]) -> str:
    for lo, hi in bins:
        if lo <= value < hi:
            return f"{lo}-{hi}" if hi < 10**8 else f">={lo}"
    return "?"


def summarise(genomes: list[dict[str, Any]], rule_m: int, rule_identity: float) -> dict[str, Any]:
    """Distributions over every measured genome and candidate."""
    ok = [g for g in genomes if "error" not in g]
    cands = [c for g in ok for c in g["candidates"] if not c["context_only"]]
    grid: dict[str, int] = {}
    for c in cands:
        m_bin, id_bin = _bin(c["M_amp"][1], M_BINS), _bin(c.get("identity_chain", 0), ID_BINS)
        key = f"M {m_bin} / identity {id_bin}"
        grid[key] = grid.get(key, 0) + 1
    copies = [c for c in cands if c["copy_by_rule"]]
    diffs = sorted(abs(c["length_diff"]) for c in copies)
    nulls = [m for g in ok for m in g["null_max_M"]]
    sites = [s for c in copies for s in c["sites"] if "mm_current" in s]
    per_group: dict[str, dict[str, int]] = {}
    for g in ok:
        for name in g["groups"]:
            d = per_group.setdefault(
                name,
                {
                    "genomes": 0,
                    "copy_current": 0,
                    "copy_chain": 0,
                    "chain_not_current": 0,
                    "current_not_chain": 0,
                },
            )
            d["genomes"] += 1
            d["copy_current"] += g["copy_current"]
            d["copy_chain"] += g["copy_chain"]
            d["chain_not_current"] += g["copy_chain"] and not g["copy_current"]
            d["current_not_chain"] += g["copy_current"] and not g["copy_chain"]
    secs: dict[str, list[float]] = {}
    for g in ok:
        for key, v in g["seconds"].items():
            secs.setdefault(key, []).append(v)
    return {
        "genomes_measured": len(ok),
        "genomes_failed": len(genomes) - len(ok),
        "rule": f"copy when M_amp >= {rule_m} or identity_chain >= {rule_identity}",
        "candidates_by_M_and_identity": dict(sorted(grid.items())),
        "copies_by_rule": len(copies),
        "copies_min_M_amp_step1": min((c["M_amp"][1] for c in copies), default=None),
        "copies_M_amp_by_step_min": {
            str(st): min((c["M_amp"][st] for c in copies), default=None) for st in STEPS
        },
        "copies_length_diff": {
            "median": statistics.median(diffs) if diffs else None,
            "max": diffs[-1] if diffs else None,
            "over_indel_tolerance": sum(d > INDEL_TOLERANCE for d in diffs),
        },
        "copies_split_by_current": sum(c["current_split"] for c in copies),
        "copies_cut": sum(c["cut_left"] or c["cut_right"] for c in copies),
        "copies_with_N_next_to_them": sum(bool(c["N_left"] or c["N_right"]) for c in copies),
        "sites_worse_at_current_placement": sum(
            (s["mm_current"] is None) != (s["mm_chain"] is None)
            or (
                s["mm_current"] is not None
                and s["mm_chain"] is not None
                and s["mm_current"] > s["mm_chain"]
            )
            for s in sites
        ),  # fmt: skip
        "sites_compared": len(sites),
        "null_max_M": {
            "n": len(nulls),
            "max": max(nulls, default=None),
            f">= {rule_m}": sum(m >= rule_m for m in nulls),
            ">= 24": sum(m >= 24 for m in nulls),
        },
        "per_group": per_group,
        "seconds_median": {k: round(statistics.median(v), 3) for k, v in sorted(secs.items())},
        "current_unmatched_loci": sum(len(g["current_unmatched"]) for g in ok),
    }


# ------------------------------------------------------------------ the run
Fetch = Callable[[list[str]], dict[str, dict[str, str]]]


def run(
    args: argparse.Namespace,
    assay: Assay,
    cfg: Config,
    fetch_genomes: Fetch,
    fetch_fasta: Callable[[str], str] | None = None,
    probe: Callable[[str], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Select genomes, measure them batch by batch, and keep the report file up to date."""
    v = cfg.variants
    refs = [r.sequence.upper() for r in assay.reference_amplicons]
    if not refs:
        raise SystemExit("the assay needs reference_amplicons for this measurement")
    mm = cfg.thresholds.amplicon.max_site_mismatches
    oligos = [oligo_sites(assay, amp, mm) for amp in refs]
    context: tuple[str, str] = ("", "")
    ctx_acc = args.context_accession or assay.target.accession
    if ctx_acc and fetch_fasta is not None:
        context = reference_context(refs[0], parse_fasta(fetch_fasta(ctx_acc)))
        if not any(context):
            log.warning("The first reference amplicon is not in %s exactly: no context", ctx_acc)
    groups: dict[str, list[str]] = {}
    if args.group:
        taxon = assay.target.taxid
        path = store_path(Path(args.cache_root), taxon, refs[0], v.flank_nt, v.source,
                          assay.target.excluded_taxids)  # fmt: skip
        if not path.exists():
            raise SystemExit(
                f"No region store at {path}: --group needs the store of an earlier run. Pass the "
                "same --config as for 'run' (its ncbi.cache_dir), and the same assay file."
            )
        store = RegionStore(path)
        log.info("Region store %s: %d assemblies", path, len(store.items))
        items = current_items(store)
        groups = select(items, args.group, refs, v.seed_length, v.min_copy_identity,
                        args.per_group)  # fmt: skip
        stored = {it.accession: it for it in items}
    else:
        stored = {}
    if args.accessions:
        groups["named"] = [a.strip() for a in args.accessions.split(",") if a.strip()]
    order: dict[str, list[str]] = {}
    for g, accs in groups.items():
        for a in accs:
            order.setdefault(a, []).append(g)
    accessions = list(order)[: args.max_genomes]
    report: dict[str, Any] = {
        "script": "measure_locator",
        "tool_version": __version__,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "assay": assay.assay_name,
        "references": [
            {"name": r.name, "length": len(r.sequence)} for r in assay.reference_amplicons
        ],  # fmt: skip
        "oligos_placed": [[o.name for o in os_] for os_ in oligos],
        "settings": {
            "seed_length": v.seed_length,
            "current_seed_step": v.seed_step,
            "flank": v.flank_nt,
            "max_indel": args.max_indel,
            "min_copy_identity": v.min_copy_identity,
            "rule_m": args.rule_m,
            "rule_identity": args.rule_identity,
            "null_per_genome": args.null + 1,
            "context_accession": ctx_acc if any(context) else None,
            "context_lengths": [len(context[0]), len(context[1])],
        },  # fmt: skip
        "groups": groups,
        "genomes": [],
    }
    if args.probe_sequence_report and probe is not None:
        report["sequence_report_probe"] = probe(args.probe_sequence_report)
    out = Path(args.outdir) / "measure_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    batch = max(1, args.batch)
    for i in range(0, len(accessions), batch):
        chunk = accessions[i : i + batch]
        try:
            genomes = fetch_genomes(chunk)
        except (QpcrAssayCheckError, OSError) as exc:
            log.warning("Download failed for %s: %s", ",".join(chunk), exc)
            genomes = {}
        for acc in chunk:
            it = stored.get(acc)
            row: dict[str, Any] = {"accession": acc, "groups": order[acc]}
            if it is not None:
                row.update(organism=it.organism, assembly_level=it.assembly_level,
                           stored_status=it.status,
                           stored_max_seeds=max((lc.n_seeds for lc in it.loci), default=0),
                           stored_identity=[lc.identity for lc in it.loci][:10])  # fmt: skip
            contigs = genomes.get(acc)
            if contigs is None:
                row["error"] = "not downloaded"
            else:
                row.update(measure_genome(
                    contigs, refs, context, oligos, k=v.seed_length, current_step=v.seed_step,
                    flank=v.flank_nt, max_indel=args.max_indel, n_null=args.null,
                    rule_m=args.rule_m, rule_identity=args.rule_identity,
                    min_copy_identity=v.min_copy_identity,
                ))  # fmt: skip
                log.info("%s: %d candidates, best M %d, copy now %s / by the rule %s", acc,
                         row["n_candidates"], row["best_M_amp"], row["copy_current"],
                         row["copy_chain"])  # fmt: skip
            report["genomes"].append(row)
            report["summary"] = summarise(report["genomes"], args.rule_m, args.rule_identity)
            out.write_text(json.dumps(report, indent=1), encoding="utf-8")
        del genomes
    report["summary"] = summarise(report["genomes"], args.rule_m, args.rule_identity)
    out.write_text(json.dumps(report, indent=1), encoding="utf-8")
    log.info("Report written to %s", out)
    return report


def _by_accession(text: str, wanted: list[str]) -> dict[str, dict[str, str]]:
    """Split a multi-record Nucleotide FASTA per requested accession (version-insensitive)."""
    base = {a.split(".")[0]: a for a in wanted}
    out: dict[str, dict[str, str]] = {}
    for name, (_d, seq) in parse_fasta_records(text).items():
        acc = base.get(name.split("|")[-1].split(".")[0]) or base.get(name.split(".")[0])
        if acc:
            out.setdefault(acc, {})[name] = seq
    return out


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--assay", type=Path, required=True)
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--group", action="append", default=[])
    ap.add_argument("--accessions", default="")
    ap.add_argument("--per-group", type=int, default=25)
    ap.add_argument("--max-genomes", type=int, default=200)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--max-indel", type=int, default=150,
                    help="largest length difference to the reference allowed within a chain "
                         "(an assumption for this measurement, not a tool default)")  # fmt: skip
    ap.add_argument("--null", type=int, default=2)
    ap.add_argument("--rule-m", type=int, default=32)
    ap.add_argument("--rule-identity", type=float, default=0.75)
    ap.add_argument("--context-accession", default="")
    ap.add_argument("--probe-sequence-report", default="")
    ap.add_argument("--outdir", type=Path, default=Path("measure_out"))
    args = ap.parse_args(argv)

    from qpcr_assay_check.ncbi.cache import Cache
    from qpcr_assay_check.ncbi.eutils import Eutils
    from qpcr_assay_check.ncbi.http import NcbiError, NcbiHttp
    from qpcr_assay_check.ncbi.settings import credentials_from_env, scrub
    from qpcr_assay_check.variants.datasets import DatasetsClient

    try:
        assay = build_assay(args.assay, {})
        cfg = load_config(args.config, assay.settings)
        http = NcbiHttp(cfg.ncbi, credentials_from_env())
    except QpcrAssayCheckError as exc:
        log.error("%s", exc)
        return 2
    args.cache_root = Cache(cfg.ncbi.cache_dir).root
    eutils = Eutils(http, cfg.ncbi.eutils_url)
    datasets = DatasetsClient(http, cfg.ncbi.datasets_url)

    def fetch_genomes(accs: list[str]) -> dict[str, dict[str, str]]:
        if cfg.variants.source == "datasets":
            return {a: parse_fasta(f) for a, f in datasets.download(accs).items()}
        return _by_accession(eutils.fetch_fasta_many(accs), accs)

    def probe(acc: str) -> dict[str, Any]:
        """UNVERIFIED endpoint: tests whether Datasets answers a per-sequence report for an
        assembly (and with which fields), for the planned plasmid/chromosome role."""
        url = f"{cfg.ncbi.datasets_url.rstrip('/')}/genome/accession/{acc}/sequence_reports"
        try:
            doc = http.request("GET", url, service="datasets").json()
        except (NcbiError, ValueError) as exc:
            return {
                "endpoint": "/genome/accession/{acc}/sequence_reports",
                "error": scrub(str(exc)),
            }
        reports = doc.get("reports") or [] if isinstance(doc, dict) else []
        fields = sorted({key for r in reports for key in r})
        return {
            "endpoint": "/genome/accession/{acc}/sequence_reports",
            "top_level_keys": sorted(doc) if isinstance(doc, dict) else str(type(doc)),
            "n_reports": len(reports),
            "report_fields": fields,
            "values": {f: sorted({str(r.get(f)) for r in reports})[:10] for f in fields
                       if f in ("role", "assigned_molecule_location_type", "assembly_unit")},
        }  # fmt: skip

    try:
        run(args, assay, cfg, fetch_genomes, eutils.fetch_fasta, probe)
    except (QpcrAssayCheckError, NcbiError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
