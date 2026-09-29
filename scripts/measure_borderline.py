#!/usr/bin/env python3
"""List the borderline candidates of measure_locator.py reports, one line each.  (step 0)

Borderline: fewer than 32 anchored bases (M) with identity >= 0.60, or M from 24 to 31. These
decide the copy rule of the locator overhaul, so each line says whether the candidate is whole
or cut by a contig end. Then the candidates found only through the context (nothing of the
fragment anchored): they test rule (b) without a fragment block. Output: coordinates and
numbers only, no sequences.

    python scripts/measure_borderline.py work/measure_out/legionella2/measure_report.json ...

In Docker: scripts/measure_borderline.sh (see there).
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

log = logging.getLogger("measure_borderline")
HEADER = (
    "accession organism M identity length_diff whole/cut start contig_len ctx_left ctx_right "
    "mismatches"
)


def borderline(report: dict[str, Any]) -> Iterator[str]:
    """One line per borderline candidate of one report."""
    for g in report.get("genomes", []):
        for c in g.get("candidates", []):
            m, ident = c["M_amp"]["1"], c.get("identity_chain", 0)
            if c["context_only"] or not ((m < 32 and ident >= 0.60) or 24 <= m < 32):
                continue
            cut = "cut" if c["cut_left"] or c["cut_right"] else "whole"
            mm = " ".join(f"{s['oligo']}:{s['mm_chain']}" for s in c["sites"])
            organism = (g.get("organism") or "?").replace(" ", "_")[:28]
            yield (f"{g['accession']} {organism} {m} {ident} {c['length_diff']} {cut} "
                   f"{c['amp_start']} {c['contig_len']} {c.get('M_ctx_left', '-')} "
                   f"{c.get('M_ctx_right', '-')} {mm}")  # fmt: skip


CONTEXT_HEADER = (
    "accession organism ctx_left ctx_right length_diff whole/cut start contig_len N_inside"
)


def context_only(report: dict[str, Any]) -> Iterator[str]:
    """One line per candidate anchored only in the context (rule (b) without a fragment block)."""
    for g in report.get("genomes", []):
        for c in g.get("candidates", []):
            if not c["context_only"]:
                continue
            cut = "cut" if c["cut_left"] or c["cut_right"] else "whole"
            organism = (g.get("organism") or "?").replace(" ", "_")[:28]
            yield (f"{g['accession']} {organism} {c.get('M_ctx_left', '-')} "
                   f"{c.get('M_ctx_right', '-')} {c['length_diff']} {cut} {c['amp_start']} "
                   f"{c['contig_len']} {c.get('N_inside', '-')}")  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path in argv if argv is not None else sys.argv[1:]:
        lines = list(borderline(json.loads(Path(path).read_text(encoding="utf-8"))))
        log.info("== %s: %d borderline candidates", path, len(lines))
        log.info(HEADER)
        for line in lines:
            log.info(line)
        report = json.loads(Path(path).read_text(encoding="utf-8"))
        ctx = list(context_only(report))
        log.info("== %s: %d candidates found only through the context", path, len(ctx))
        log.info(CONTEXT_HEADER)
        for line in ctx:
            log.info(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
