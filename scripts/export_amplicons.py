"""Export the distinct target amplicons of an exhaustive run, with their genome outcomes.

Reads one genome store (``<cache>/genomes/<taxon>-<key>.jsonl``) read-only and judges every
genome with the package's own functions, as a run would: no NCBI request, nothing written to the
store. For each genome judged on a whole copy it takes the fragment of its best-binding copy
(the copy the outcome is based on) and groups genomes with an identical fragment. The output is
small enough to paste back (a few hundred distinct sequences for tens of thousands of genomes).

Usage, in the Docker image (from the folder with work/ and scripts/):
    docker run --rm -v $PWD/work:/work -v $PWD/docs/examples:/examples:ro \\
        -v $PWD/scripts:/scripts:ro -v $PWD/src:/src:ro -e PYTHONPATH=/src \\
        --entrypoint python qpcr-assay-check /scripts/export_amplicons.py \\
        /examples/<assay>.yaml /work/cache/genomes/<taxon>-<key>.jsonl -c /work/config.yaml \\
        > work/runs/<name>-amplicons.json

Exploratory data for the whole-amplicon map; not part of a run's record.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from qpcr_assay_check.align import realign
from qpcr_assay_check.cli import build_assay
from qpcr_assay_check.config import load_config
from qpcr_assay_check.variants.chain import copies_of
from qpcr_assay_check.variants.exhaustive import (
    GenomeOutcome,
    _assess_copy,
    _copy_key,
    as_items,
    assess,
    copy_rule,
    genome_outcome,
    latest,
    mark_unassembled,
    placements,
)
from qpcr_assay_check.variants.genomestore import SCHEMA, GenomeRecord

log = logging.getLogger("export_amplicons")


def read_store(path: Path) -> tuple[dict[str, Any], dict[str, GenomeRecord], dict[str, str]]:
    """The header, the records (last line of an accession wins) and the collection dates."""
    lines = path.read_text(encoding="utf-8").splitlines()
    header = json.loads(lines[0])
    if header.get("schema") != SCHEMA:
        raise SystemExit(
            f"{path}: store schema {header.get('schema')}, this code reads {SCHEMA}; "
            "use the code version that wrote it"
        )
    records: dict[str, GenomeRecord] = {}
    for line in lines[1:]:
        if line.strip():
            rec = GenomeRecord.model_validate_json(line)
            records[rec.accession] = rec
    dates_path = path.with_name(path.name + ".dates.json")
    dates = json.loads(dates_path.read_text("utf-8")) if dates_path.exists() else {}
    return header, records, dates


def best_fragments(
    records: list[GenomeRecord], items: list[Any], assay: Any, amplicon: str, cfg: Any
) -> dict[str, str]:
    """Per genome, the fragment of the whole copy the assay binds best (as ``assess`` ranks it)."""
    rule = copy_rule(cfg)
    placed = placements(assay, amplicon, cfg)
    scoring = realign.Scoring(
        cfg.specificity.alignment.match, cfg.specificity.alignment.mismatch,
        cfg.specificity.alignment.gap_open, cfg.specificity.alignment.gap_extend,
    )  # fmt: skip
    memo: dict[Any, Any] = {}
    bulges = cfg.variants.homopolymer_bulges_detectable
    out: dict[str, str] = {}
    by_acc = {r.accession: r for r in records}
    for it in items:
        if it.status != "found":
            continue
        rec = by_acc[it.accession]
        cands = [c.candidate() for c in rec.copies]
        kept = {id(c) for c in copies_of(cands, rule)}
        stored = [sc for sc, c in zip(rec.copies, cands, strict=True) if id(c) in kept]
        stored.sort(key=lambda c: (-c.anchored, -(c.identity or 0.0)))  # as as_items orders loci
        best = None
        for sc, lc in zip(stored, it.loci, strict=True):
            if lc.truncated:
                continue
            windows = placed[lc.ref] if lc.ref < len(placed) else placed[0]
            copy = _assess_copy(it, lc, assay, windows, cfg, scoring, memo,
                                cfg.variants.probe_channels, bulges)  # fmt: skip
            if copy is None:
                continue
            key = _copy_key(copy[0], bulges)
            if best is None or key < best[0]:
                best = (key, sc)
        if best is not None:
            sc = best[1]
            out[it.accession] = sc.region[sc.start - sc.region_start : sc.end - sc.region_start]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("assay", type=Path)
    ap.add_argument("store", type=Path)
    ap.add_argument("-c", "--config", type=Path)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    assay = build_assay(args.assay, {})
    cfg = load_config(args.config, assay.settings)
    header, by_acc, dates = read_store(args.store)
    amplicon = header["key"]["references"][0][0]
    records = latest(by_acc)
    items, _related, _beside, _flanked = as_items(records, copy_rule(cfg), dates)
    calls: list[Any] = []
    cut: list[str] = []
    assess(items, assay, amplicon, placements(assay, amplicon, cfg), cfg, calls=calls, cut=cut)
    mark_unassembled(calls, cfg.variants.multicopy_unassembled)
    outcome = {c.accession: genome_outcome(c) for c in calls}
    frags = best_fragments(records, items, assay, amplicon, cfg)
    meta = {it.accession: it for it in items}
    groups: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "n": 0, "outcomes": Counter(), "organisms": Counter(), "levels": Counter(),
        "collected": Counter(), "first": "9999", "last": "0000", "example": "",
    })  # fmt: skip
    for acc, seq in frags.items():
        it, o = meta[acc], outcome.get(acc)
        g = groups[seq]
        g["n"] += 1
        g["outcomes"][o.value if isinstance(o, GenomeOutcome) else "no call"] += 1
        g["organisms"][it.organism or "?"] += 1
        g["levels"][it.assembly_level or "?"] += 1
        g["collected"][(it.collection_date or "")[:4] or "none"] += 1
        g["first"], g["last"] = min(g["first"], it.release_date), max(g["last"], it.release_date)
        g["example"] = g["example"] or acc
    seqs = sorted(groups.items(), key=lambda kv: -kv[1]["n"])
    json.dump({
        "assay": assay.assay_name, "store": args.store.name, "reference": amplicon,
        "genomes_in_store": len(records), "judged_on_a_whole_copy": len(frags),
        "found": sum(1 for it in items if it.status == "found"), "cut": len(cut),
        "distinct_amplicons": len(seqs),
        "amplicons": [{"seq": s, **{k: (dict(v.most_common()) if isinstance(v, Counter) else v)
                                    for k, v in g.items()}} for s, g in seqs],
    }, sys.stdout, indent=1)  # fmt: skip
    log.info("%d genomes, %d judged on a whole copy, %d distinct amplicons",
             len(records), len(frags), len(seqs))  # fmt: skip


if __name__ == "__main__":
    main()
