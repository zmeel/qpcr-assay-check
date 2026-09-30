"""Show whether cached BLAST results carry NCBI's search statistics (``search.stat``).

Reads only the local cache (no network). Prints, for the most recently cached BLAST results,
each query's title, the keys of its ``search`` object and its ``stat``, so a missing or moved
``stat`` can be seen. Usage (in the container): python /scripts/check_blast_stats.py [cache] [n]
"""

from __future__ import annotations

import glob
import gzip
import json
import logging
import os
import sys

log = logging.getLogger("check_blast_stats")


def describe(path: str) -> list[str]:
    """One line per query (at most 3) of a cached BLAST result."""
    name = os.path.basename(path)[:12]
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            record = json.load(fh)
        # the cache's envelope: {"created": ..., "text": <NCBI's answer as text>}
        text = record.get("text") if isinstance(record, dict) else None
        doc = json.loads(text) if isinstance(text, str) else record
    except (OSError, ValueError) as exc:
        return [f"{name} unreadable or not JSON: {exc}"]
    outputs = doc.get("BlastOutput2", []) if isinstance(doc, dict) else []
    outputs = outputs if isinstance(outputs, list) else [outputs]
    keys = sorted(doc)[:6] if isinstance(doc, dict) else type(doc).__name__
    lines = [f"{name} {len(outputs)} report(s), top-level keys {keys}"]
    for out in outputs[:3]:
        report = out.get("report", {})
        search = report.get("results", {}).get("search", {})
        lines.append(
            f"  {search.get('query_title')!r}: search keys {sorted(search)}; "
            f"stat {search.get('stat')}; results keys {sorted(report.get('results', {}))}"
        )
    return lines


def main(argv: list[str]) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    cache = argv[1] if len(argv) > 1 else "/work/cache"
    n = int(argv[2]) if len(argv) > 2 else 6
    files = sorted(glob.glob(f"{cache}/blast/*/*.json.gz"), key=os.path.getmtime)[-n:]
    if not files:
        log.info("No cached BLAST results under %s/blast", cache)
        return 1
    for f in files:
        for line in describe(f):
            log.info(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
