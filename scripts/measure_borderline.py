#!/usr/bin/env python3
"""List the borderline candidates of measure_locator.py reports, one line each.  (step 0)

Borderline: fewer than 32 anchored bases (M) with identity >= 0.65, or M from 24 to 31. These
decide the copy rule of the locator overhaul, so each line says whether the candidate is whole
or cut by a contig end. Output: coordinates and numbers only, no sequences.

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
HEADER = "accession organism M identity length_diff whole/cut start contig_len mismatches"


def borderline(report: dict[str, Any]) -> Iterator[str]:
    """One line per borderline candidate of one report."""
    for g in report.get("genomes", []):
        for c in g.get("candidates", []):
            m, ident = c["M_amp"]["1"], c.get("identity_chain", 0)
            if c["context_only"] or not ((m < 32 and ident >= 0.65) or 24 <= m < 32):
                continue
            cut = "cut" if c["cut_left"] or c["cut_right"] else "whole"
            mm = " ".join(f"{s['oligo']}:{s['mm_chain']}" for s in c["sites"])
            organism = (g.get("organism") or "?").replace(" ", "_")[:28]
            yield (f"{g['accession']} {organism} {m} {ident} {c['length_diff']} {cut} "
                   f"{c['amp_start']} {c['contig_len']} {mm}")  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for path in argv if argv is not None else sys.argv[1:]:
        lines = list(borderline(json.loads(Path(path).read_text(encoding="utf-8"))))
        log.info("== %s: %d borderline candidates", path, len(lines))
        log.info(HEADER)
        for line in lines:
            log.info(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
