"""Review status (flag level) and process exit codes.

The tool re-checks an assay that is in use; it does not pass or fail the assay (user decision
2026-09-27, advisor subagent). Each section gets a flag level, shown in the report and workbook as
a review status: no flags, review (a warning limit you configured was crossed), exceeds limit (a
FAIL limit was crossed), or incomplete. The laboratory decides what to do.

The rule that matters most: **evidence that is missing never counts as "no flags".** A required
analysis that was not run yields INCOMPLETE. Precedence: FAIL > INCOMPLETE > WARN > PASS. The
internal codes (PASS/WARN/FAIL/INCOMPLETE) stay in ``results.json`` so that earlier records can
still be compared.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum

from .models import Status


class Verdict(StrEnum):
    """Flag level of a section or of the whole evaluation (see the module docstring)."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    INCOMPLETE = "INCOMPLETE"


EXIT_CODES: dict[Verdict, int] = {
    Verdict.PASS: 0,
    Verdict.WARN: 10,
    Verdict.FAIL: 20,
    Verdict.INCOMPLETE: 30,
}
EXIT_INPUT_ERROR = 64

# How a flag level is named for people (report, workbook) and in results.json's review_status.
STATUS_LABEL: dict[Verdict, str] = {
    Verdict.PASS: "No flags",
    Verdict.WARN: "Review",
    Verdict.FAIL: "Exceeds limit",
    Verdict.INCOMPLETE: "Incomplete",
}
REVIEW_STATUS: dict[Verdict, str] = {
    Verdict.PASS: "no_flags",
    Verdict.WARN: "review",
    Verdict.FAIL: "exceeds_limit",
    Verdict.INCOMPLETE: "incomplete_evidence",
}
EXIT_NCBI_ERROR = 70  # reserved for the NCBI client (v0.2.0): the run can be resumed

_FROM_STATUS = {
    Status.PASS: Verdict.PASS,
    Status.INFO: Verdict.PASS,
    Status.WARN: Verdict.WARN,
    Status.FAIL: Verdict.FAIL,
}


def verdict_from_status(status: Status) -> Verdict:
    """Map a check status to a section verdict."""
    return _FROM_STATUS[status]


def combine(sections: Mapping[str, Verdict | None], required: Iterable[str]) -> Verdict:
    """Combine section verdicts.

    ``sections`` maps a section key to its verdict, or ``None`` if it was not evaluated.
    ``required`` lists the keys that must be evaluated for the result to be conclusive.
    """
    verdicts = [sections.get(key) for key in required]
    if any(v is Verdict.FAIL for v in verdicts):
        return Verdict.FAIL
    if any(v is None or v is Verdict.INCOMPLETE for v in verdicts):
        return Verdict.INCOMPLETE
    if any(v is Verdict.WARN for v in verdicts):
        return Verdict.WARN
    return Verdict.PASS


def exit_code(verdict: Verdict) -> int:
    """Process exit code for a verdict."""
    return EXIT_CODES[verdict]
