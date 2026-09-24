#!/usr/bin/env python3
"""Check the assessment's BLAST assumptions against REAL NCBI hits.  (v0.3.0)

WHY THIS EXISTS
    To avoid fetching a sequence window for every one of thousands of hits, the assessment rules
    out hits that cannot matter using two consequences of BLAST reporting a *locally maximal*
    alignment (extending it over a matching base would have raised its score):

      1. lower bound: a full-length alignment has at least  aligned_mismatches + ceil(u5/4) +
         ceil(u3/4)  mismatches (u5/u3 = oligo bases BLAST left unaligned at the 5'/3' end;
         BLAST scores are match +1, mismatch -3);
      2. the first base beyond the alignment mismatches, so at most  u3 - 1  clean 3' bases remain.

    These follow from BLAST's scoring, but they were derived on paper, not observed. This script
    tests them on real hits: it takes the hits of one tier, re-aligns a SAMPLE of partial hits
    over the full oligo length (including hits the assessment would skip), and reports every case
    where reality contradicts a rule. It also counts how many sequence windows a real run needs.

WHAT IT SENDS TO NCBI
    The oligo sequences of the assay file (search, unless already cached) and one efetch request
    per sampled hit (default 80). Your NCBI_EMAIL is sent as NCBI requires; it is never written to
    the output.

HOW TO RUN (repository root, after `pip install -e .`)
    export NCBI_EMAIL="your.name@example.org"
    export NCBI_API_KEY="..."                # optional
    mkdir -p validation_out
    nohup python scripts/validate_assessment.py > validation_out/run.log 2>&1 &
    tail -f validation_out/run.log

    The default tier is 'background' (human): the search can take an hour, but it is identical to
    the one `qpcr-assay-check run` makes, so results already in your cache (7 days) are reused.
    Options: --tier, --sample N, --assay FILE, --config FILE, --outdir DIR

WHAT TO PASTE BACK
    validation_out/validation_report.json (no secrets). Exit code 0: no rule was contradicted.
    Exit code 1: at least one was; the report lists the cases.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from qpcr_assay_check import __version__
from qpcr_assay_check.align import realign
from qpcr_assay_check.cli import build_assay
from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import QpcrAssayCheckError
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.settings import scrub
from qpcr_assay_check.search.execute import run_remote_search
from qpcr_assay_check.specificity import sites as S
from qpcr_assay_check.specificity.fetch import WindowFetcher

log = logging.getLogger("validate")


def _candidates(remote: Any, cfg: Any, tier: str, assay: Any) -> list[S.Candidate]:
    min_identical = cfg.search.relevance.min_identical_bases
    out: list[S.Candidate] = []
    for ps in remote.plan.searches:
        if ps.tier != tier or ps.key not in remote.parsed:
            continue
        for label in ps.labels:
            oligo = remote.plan.queries[label]
            for hit in remote.parsed[ps.key].queries[label].hits:
                for hsp in hit.hsps:
                    if hsp.identity >= min_identical:
                        role = assay.role_of(label)
                        out.append(S.make_candidate(tier, label, oligo, hit, hsp, role))
    return out


def _sample(partials: list[S.Candidate], n: int) -> list[S.Candidate]:
    """Deterministic, evenly spread sample."""
    ordered = sorted(partials, key=lambda c: (c.label, c.accession, c.hsp.hit_from))
    if len(ordered) <= n:
        return ordered
    step = len(ordered) / n
    return [ordered[int(i * step)] for i in range(n)]


def validate(args: argparse.Namespace) -> dict[str, Any]:
    """Run the search (or reuse it), sample partial hits, re-align them, test the rules."""
    cfg = load_config(args.config)
    assay = build_assay(args.assay, {})
    started = time.time()
    remote = run_remote_search(
        assay, cfg, args.outdir, confirm=lambda *_: True,
        keep_tiers={args.tier}, only_tiers={args.tier},
    )  # fmt: skip
    if not remote.plan.searches:
        raise QpcrAssayCheckError(f"the plan has no '{args.tier}' tier for this assay")
    fetcher = WindowFetcher(Eutils(remote.http, cfg.ncbi.eutils_url), remote.cache)
    rules = cfg.specificity
    scoring = realign.Scoring(
        rules.alignment.match, rules.alignment.mismatch,
        rules.alignment.gap_open, rules.alignment.gap_extend,
    )  # fmt: skip

    cands = _candidates(remote, cfg, args.tier, assay)
    partial = [c for c in cands if c.partial]

    def site_rules(c: S.Candidate) -> Any:
        return rules.probe_site if c.role == "probe" else rules.primer_site

    fetchable = [c for c in partial if S.can_reach_warning(c, site_rules(c))]
    summary = {
        "relevant_alignments": len(cands),
        "full_length_no_fetch_needed": len(cands) - len(partial),
        "partial": len(partial),
        "partial_ruled_out_without_fetching": len(partial) - len(fetchable),
        "partial_needing_a_fetch": len(fetchable),
        "note": "the last number is the number of efetch requests a real run would make "
        "for this tier (fewer if windows are cached)",
    }
    log.info("Summary: %s", summary)

    half = args.sample // 2
    skipped = [c for c in partial if c not in fetchable]
    sample = _sample(fetchable, args.sample - half) + _sample(skipped, half)
    violations: list[dict[str, Any]] = []
    checked = failed = 0
    for i, c in enumerate(sample, start=1):
        lo, hi = S.window_for(c, rules.window_padding_nt, c.hit.length)
        window = fetcher.get(c.accession, lo, hi)
        if window is None:
            failed += 1
            continue
        aln = realign.align_semiglobal(c.oligo, S.oriented_window(window, c.orientation), scoring)
        site = S.site_from_alignment(c, aln, window, lo, site_rules(c), "V")
        checked += 1
        problems = []
        if site.n_mismatch + site.n_gap < c.lower_bound:
            problems.append("lower_bound")
        if c.u3 > 0 and site.clean_3prime_nt > c.u3 - 1:
            problems.append("first_unaligned_base_is_a_mismatch")
        if c not in fetchable and site.level != "minor":
            problems.append("ruled_out_but_relevant")
        for check in problems:
            violations.append(
                {
                    "check": check, "label": c.label, "accession": c.accession,
                    "hit_from": c.hsp.hit_from, "hit_to": c.hsp.hit_to,
                    "hit_strand": c.hsp.hit_strand, "u5": c.u5, "u3": c.u3,
                    "lower_bound": c.lower_bound, "realigned_errors": site.n_mismatch + site.n_gap,
                    "realigned_clean_3prime": site.clean_3prime_nt, "level": site.level,
                    "q_aln": site.q_aln, "s_aln": site.s_aln,
                }
            )  # fmt: skip
        if i % 20 == 0:
            log.info("  %d / %d sampled hits checked", i, len(sample))
    return {
        "schema": 1,
        "tool_version": __version__,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "tier": args.tier,
        "assay": assay.assay_name,
        "counts": summary,
        "sample": {
            "requested": args.sample,
            "checked": checked,
            "fetch_failed": failed,
            "from_hits_that_would_be_fetched": min(len(fetchable), args.sample - half),
            "from_hits_ruled_out": min(len(skipped), half),
        },  # fmt: skip
        "rules_contradicted": len(violations),
        "violations": violations[:25],
        "verdict": "no rule contradicted in the sample"
        if not violations
        else "AT LEAST ONE RULE WAS CONTRADICTED: do not rely on the pruning; report this",
        "seconds": round(time.time() - started),
    }


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--assay", type=Path, default=Path("examples/cdc_2019-nCoV_N1.yaml"))
    ap.add_argument("--config", type=Path, default=None)
    ap.add_argument("--tier", default="background")
    ap.add_argument("--sample", type=int, default=80)
    ap.add_argument("--outdir", type=Path, default=Path("validation_out"))
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S", stream=sys.stdout
    )
    args.outdir.mkdir(parents=True, exist_ok=True)
    try:
        report = validate(args)
    except Exception as exc:  # noqa: BLE001 - the report must say what happened
        log.error("Validation failed: %s", scrub(str(exc)))
        report = {"schema": 1, "tool_version": __version__, "error": scrub(str(exc))}
        (args.outdir / "validation_report.json").write_text(json.dumps(report, indent=2))
        return 2
    (args.outdir / "validation_report.json").write_text(json.dumps(report, indent=2))
    log.info("Verdict: %s", report["verdict"])
    log.info("Wrote %s", args.outdir / "validation_report.json")
    return 1 if report["rules_contradicted"] else 0


if __name__ == "__main__":
    sys.exit(main())
