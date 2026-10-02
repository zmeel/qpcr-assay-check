#!/usr/bin/env python3
"""A compact summary of one run's results.json, to paste back (overhaul step 8).

Counts, verdicts and accessions only: no oligo or genome sequences, no settings beyond the
variant and inclusivity sections, no credentials (results.json holds none).

    python scripts/run_summary.py work/results/<assay>/<run_id>/results.json

In Docker: scripts/run_assay.sh writes it next to the run log.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

log = logging.getLogger("run_summary")
EXAMPLES = 10  # accessions per list


def _scalars(d: dict[str, Any]) -> dict[str, Any]:
    """The plain values of a dict, and its lists of accessions cut to ``EXAMPLES``."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, list) and all(isinstance(x, str) for x in v):
            out[k] = v[:EXAMPLES] + ([f"... {len(v)} in all"] if len(v) > EXAMPLES else [])
        elif not isinstance(v, (dict, list)):
            out[k] = v
    return out


def summary(data: dict[str, Any]) -> dict[str, Any]:
    """The parts of a results.json that step 8 needs."""
    out: dict[str, Any] = {
        "run_id": data.get("run_id"),
        "tool_version": (data.get("tool") or {}).get("version"),
        "overall": {k: data["overall"].get(k) for k in ("review_status", "verdict", "rationale")},
        "sections": {s["key"]: [s.get("state"), s.get("verdict")] for s in data["sections"]},
        "settings": {k: (data.get("config") or {}).get(k) for k in ("variants", "inclusivity")},
    }
    vs = data.get("variant_summary") or {}
    cov = vs.get("coverage")
    if cov:
        copies = cov.get("copies") or {}
        out["coverage"] = _scalars(cov)
        out["coverage"]["years"] = cov.get("years")
        out["copies"] = _scalars(copies)
        for key in (
            "oligos",
            "role_none",
            "role_undetermined",
            "channels",
            "by_level",
            "escape_reasons",
        ):
            out["copies"][key] = copies.get(key)
        out["channels"] = cov.get("channel_results")
    inc = data.get("inclusivity")
    if inc:
        keys = ("verdict", "rationale", "fragment_years", "status_axis", "distinct")
        out["inclusivity"] = {k: inc.get(k) for k in keys}
        ca = inc.get("collection")
        if ca:
            out["inclusivity"]["collection"] = {
                (r.get("label") or str(r["year"])): [r["with_region"], r["detectable"],
                                                     r["at_risk"], r["likely_failure"],
                                                     r["undetermined"]]
                for r in [*ca["years"], ca["earlier"], ca["undated"], ca["not_read"]]
                if r["with_region"]
            }  # fmt: skip
    out["fragment_variants"] = [
        {
            **{k: row.get(k) for k in ("count", "percent", "level", "example_accession")},
            **{
                role: [row[role].get("n_mismatch"), row[role].get("grade")]
                for role in ("forward", "probe", "reverse")
                if row.get(role)
            },
        }  # fmt: skip
        for row in (vs.get("fragments") or [])[:10]
    ]
    spec = data.get("specificity") or {}
    out["specificity"] = {
        "verdict": spec.get("verdict"),
        "n_sites": spec.get("n_sites"),
        "n_amplicons": len(spec.get("amplicons") or []),
        "partner_scan": spec.get("partner_scan"),
        "score_floors": [
            [f["tier"], f["query"], f["min_score"], f["max_mismatches_reported"]]
            for f in spec.get("score_floors") or []
        ],
    }
    excl = data.get("exclusivity") or {}
    out["exclusivity"] = {k: excl.get(k) for k in ("verdict", "tier_searched")}
    return out


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        log.error("usage: run_summary.py <results.json>")
        return 2
    data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    log.info(json.dumps(summary(data), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
