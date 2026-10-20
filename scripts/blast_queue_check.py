#!/usr/bin/env python3
"""Is a BLAST search slow because of its size, or because NCBI moved us to the slow queue?

WHY THIS EXISTS
    On 2026-10-20 the influenza A (matrix) run stopped getting anywhere: the target-tier search
    stayed WAITING, four runs in a row, on an assay that had completed before. Two explanations
    fit that symptom equally well from the client side, and they need opposite responses:

      * THE SEARCH IS TOO BIG. The target tier searches the whole target taxon; for influenza A
        (txid11320) that was 1,680,151 Nucleotide records on 2026-10-20, about ten times the
        173,234 records the assay itself cares about. Fix: make the search smaller.
      * NCBI MOVED US TO THE SLOW QUEUE. Their developer guidelines say: "We will move searches
        of users who submit more than 100 searches in a 24 hour period to a slower queue" or,
        "in extreme cases, will block the requests", and ask that scripts submitting more than
        50 searches run "weekends or between 9 pm and 5 am Eastern time on weekdays".
        Fix: submit less, and wait. No code change helps, and none should be attempted.

    A search in the slow queue does not fail and does not say anything: it stays WAITING, exactly
    as an oversized search does. This script tells the two apart by submitting ONE deliberately
    trivial search and timing it. Queue placement follows the submitter, so this has to run from
    the same machine and network as the real runs -- its result says nothing about anyone else's.

WHAT IT SENDS TO NCBI
    * one BLAST search: a single 23-nt primer (infa_fwd of the influenza A matrix example,
      published with the permission of the source protocol's author) against core_nt, restricted
      by ENTREZ_QUERY to influenza A records published in the last --days days -- of the order of
      10,000 records, well under 1% of what the target tier asks for. The search uses this
      project's own BLAST settings, so its speed is comparable with a real run.
    * one E-utilities count, to record how many records that restriction actually covers.
    * with --rid: status polls for a search that is already running. A status poll is not a
      submission and does not count against the 100-per-24-hours budget.
    Your NCBI_EMAIL is sent to NCBI as NCBI requires. Neither it nor NCBI_API_KEY is written to
    the report.

HOW TO RUN (from the repository root, after `git pull`)
    export NCBI_EMAIL="your.name@example.org"
    python scripts/blast_queue_check.py --rid DEPS5BKC014

    In the Docker image, if the package is not installed on the host:
      docker run --rm --user $(id -u):$(id -g) -v "$PWD":/repo -w /repo \
          -e NCBI_EMAIL -e NCBI_API_KEY --entrypoint python qpcr-assay-check \
          scripts/blast_queue_check.py --rid DEPS5BKC014

    Options:
      --rid RID             also report the status of a search already running (repeatable),
                            e.g. the stuck target-tier search. Costs no submission.
      --days N              restrict the control search to records published in the last N days
                            (default 20; raise it if the count comes back very small)
      --max-wait-minutes N  stop waiting for the control search after N minutes (default 20)
      --status-only         submit nothing at all; only report --rid statuses
      -v                    more logging

HOW TO READ THE RESULT
    verdict "queue_looks_healthy"  the trivial search came back quickly, so the queue is fine and
                                   the real problem is the size of the target-tier search.
    verdict "slow_queue_likely"    even a trivial search did not come back. Submit nothing for
                                   24 hours, then run once off-peak. Do not restart the run in
                                   the meantime: every restart is another submission.
    verdict "inconclusive"         read control.polls; the report says why.

WHAT TO PASTE BACK
    The contents of smoke_out/blast_queue_report.json. It holds no secrets.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from qpcr_assay_check import __version__
from qpcr_assay_check.config import load_config
from qpcr_assay_check.errors import QpcrAssayCheckError
from qpcr_assay_check.ncbi import blast
from qpcr_assay_check.ncbi.blast import BlastApi
from qpcr_assay_check.ncbi.eutils import Eutils
from qpcr_assay_check.ncbi.http import NcbiError, NcbiHttp
from qpcr_assay_check.ncbi.settings import credentials_from_env

log = logging.getLogger("blast_queue_check")

# infa_fwd of docs/examples/influenza_a_matrix.yaml: one oligo is enough for a control, and this
# one makes the timing directly comparable with the run that is stuck.
CONTROL_OLIGO = "CTTCTRACCGAGGTCGAAACGTA"
CONTROL_LABEL = "control_infa_fwd"
TARGET_TAXID = 11320

# A control that comes back this fast cannot be sitting in a slow queue.
HEALTHY_MINUTES = 6.0
REPORT = Path("smoke_out/blast_queue_report.json")


@dataclass
class Report:
    """Everything the user pastes back. No credentials, by construction."""

    tool_version: str = __version__
    started_at: str = ""
    finished_at: str = ""
    verdict: str = "inconclusive"
    verdict_reason: str = ""
    guidance: list[str] = field(default_factory=list)
    control: dict[str, Any] = field(default_factory=dict)
    running_searches: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def write(self, redact: Any) -> None:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        text = redact(json.dumps(self.__dict__, indent=2, default=str))
        REPORT.write_text(text, encoding="utf-8")


def _entrez_query(days: int) -> str:
    """Influenza A records published in the last ``days`` days."""
    today = date.today()
    start = (today - timedelta(days=days)).strftime("%Y/%m/%d")
    return f"txid{TARGET_TAXID}[ORGN] AND {start}:{today.strftime('%Y/%m/%d')}[PDAT]"


def _count(eutils: Eutils, query: str) -> int | None:
    """How many Nucleotide records the control restriction covers, or None if the count failed."""
    try:
        return eutils.esearch_count("nuccore", query)
    except (NcbiError, QpcrAssayCheckError) as exc:  # a failed count must not stop the test
        log.warning("Could not count the control restriction: %s", exc)
        return None


def _poll_running(api: BlastApi, rids: list[str], report: Report) -> None:
    """Report the status of searches that are already running. Not a submission."""
    for rid in rids:
        try:
            status, has_hits = api.status(rid)
            log.info("Running search %s: %s", rid, status)
            report.running_searches.append({"rid": rid, "status": str(status), "hits": has_hits})
        except (NcbiError, QpcrAssayCheckError) as exc:
            log.warning("Could not read the status of %s: %s", rid, exc)
            report.running_searches.append({"rid": rid, "status": "unreadable", "error": str(exc)})


def _run_control(
    api: BlastApi,
    cfg: Any,
    eutils: Eutils,
    days: int,
    max_wait: float,
    report: Report,
    redact: Callable[[str], str],
) -> None:
    """Submit one trivial search and time it; fill in report.control and the verdict."""
    entrez = _entrez_query(days)
    subjects = _count(eutils, entrez)
    fasta = blast.build_query_fasta({CONTROL_LABEL: CONTROL_OLIGO})
    params = blast.build_put_params(cfg, fasta, entrez)
    report.control = {
        "entrez_query": entrez,
        "subject_records": subjects,
        "word_size": cfg.search.word_size,
        "database": cfg.search.database,
        "expect": cfg.search.expect,
        "queries": 1,
        "polls": [],
    }

    rid, rtoe = api.submit(params)
    submitted = time.monotonic()
    log.info("Control search submitted: RID %s, NCBI estimates %s s until ready", rid, rtoe)
    report.control.update({"rid": rid, "rtoe_s": rtoe})
    report.write(redact)  # so the RID survives an interrupt before the first poll

    deadline = submitted + max_wait * 60
    # NCBI asks that a single RID is not polled more often than once a minute.
    interval = max(cfg.ncbi.poll_interval_s, 60.0)
    while True:
        status, has_hits = api.status(rid)
        elapsed = (time.monotonic() - submitted) / 60
        log.info("Control search %s: %s (%.1f min)", rid, status, elapsed)
        report.control["polls"].append(
            {"minutes": round(elapsed, 1), "status": str(status), "hits": has_hits}
        )
        if str(status) == "READY":
            report.control["ready_after_minutes"] = round(elapsed, 1)
            if elapsed <= HEALTHY_MINUTES:
                report.verdict = "queue_looks_healthy"
                report.verdict_reason = (
                    f"A single oligo against {subjects if subjects is not None else 'about 10,000'}"
                    f" records came back in {elapsed:.1f} min, so searches are not being held in a"
                    " slow queue. The target tier is slow because of its size:"
                    f" {TARGET_TAXID} covered 1,680,151 records on 2026-10-20."
                )
                report.guidance = [
                    "Shrink or skip the target-tier search; the queue is not the problem.",
                    "The inclusivity analysis of this assay needs no BLAST at all"
                    " (variants.direct_scan_max_length covers the ~1,000 nt segment 7 records).",
                ]
            else:
                report.verdict = "inconclusive"
                report.verdict_reason = (
                    f"The control took {elapsed:.1f} min, which is slow for one oligo against"
                    f" {subjects} records but did finish. Either the queue is mildly degraded or"
                    " NCBI is simply busy; re-run this check off-peak to compare."
                )
                report.guidance = ["Re-run this check between 9 pm and 5 am Eastern to compare."]
            return
        if str(status) == "FAILED":
            report.verdict = "inconclusive"
            report.verdict_reason = f"NCBI reported that the control search {rid} FAILED."
            report.errors.append(f"control search {rid} FAILED")
            return
        if str(status) == "UNKNOWN":
            report.verdict = "inconclusive"
            report.verdict_reason = f"NCBI does not know RID {rid} (expired or never queued)."
            report.errors.append(f"control search {rid} UNKNOWN")
            return
        if time.monotonic() >= deadline:
            report.verdict = "slow_queue_likely"
            report.verdict_reason = (
                f"A single oligo against {subjects if subjects is not None else 'about 10,000'}"
                f" records was still {status} after {elapsed:.1f} min. A search that small cannot"
                " be slow on its own merits, so the searches are very likely in the slower queue"
                " NCBI documents for submitters of more than 100 searches in 24 hours."
            )
            report.guidance = [
                "Submit nothing to BLAST for 24 hours: the limit is a rolling 24-hour window."
                " Do not restart the run, and do not run the smoke test.",
                "Every restart of a run is a new submission (ncbi.resubmit_after_minutes), so"
                " restarting both deepens the throttle and discards the queued RID.",
                "Set ncbi.resubmit_after_minutes and ncbi.max_wait_minutes high (e.g. 2000) in"
                " work/config.yaml so a restart resumes the RID instead of replacing it.",
                "Then run once off-peak: weekends, or 21:00-05:00 US Eastern on weekdays.",
                "An NCBI API key does not raise these BLAST limits; it raises E-utilities limits.",
            ]
            return
        time.sleep(interval)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--rid", action="append", default=[], help="A running RID to report on.")
    ap.add_argument("--days", type=int, default=20, help="Control: records published in N days.")
    ap.add_argument("--max-wait-minutes", type=float, default=20.0, help="Stop waiting after N.")
    ap.add_argument("--status-only", action="store_true", help="Submit nothing; only --rid.")
    ap.add_argument("-v", "--verbose", action="count", default=0, help="More logging.")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

    report = Report(started_at=datetime.now(UTC).isoformat())
    try:
        creds = credentials_from_env()
    except QpcrAssayCheckError as exc:
        log.error("%s", exc)
        return 2

    cfg = load_config(None)
    http = NcbiHttp(cfg.ncbi, creds)
    api = BlastApi(http, cfg.ncbi.blast_url)
    eutils = Eutils(http, cfg.ncbi.eutils_url)

    try:
        if args.rid:
            _poll_running(api, args.rid, report)
        if args.status_only:
            report.verdict = "inconclusive"
            report.verdict_reason = "--status-only: no control search was submitted."
        else:
            _run_control(api, cfg, eutils, args.days, args.max_wait_minutes, report, creds.redact)
    except KeyboardInterrupt:
        report.errors.append("interrupted by the user")
        log.warning("Interrupted; writing the report as it stands")
    except (NcbiError, QpcrAssayCheckError) as exc:
        report.errors.append(str(exc))
        log.error("%s", exc)

    report.finished_at = datetime.now(UTC).isoformat()
    report.write(creds.redact)
    log.info("Verdict: %s", report.verdict)
    if report.verdict_reason:
        log.info("%s", report.verdict_reason)
    for line in report.guidance:
        log.info("  - %s", line)
    log.info("Paste back: %s", REPORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
