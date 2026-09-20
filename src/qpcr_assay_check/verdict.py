"""Overall verdict and process exit codes.

The rule that matters most: **evidence that is missing never counts as a PASS.** A required
analysis that was not run yields INCOMPLETE, not PASS. Precedence: FAIL > INCOMPLETE > WARN > PASS.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from enum import StrEnum

from .models import Status


class Verdict(StrEnum):
    """Verdict of a section or of the whole evaluation."""

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
