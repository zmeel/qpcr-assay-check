"""Which code made a record: the package version, a fingerprint of the package's own files and,
when it can be read, the git commit.

The version string alone does not identify the code: unreleased changes on ``main`` carry the
last release's version, and ``scripts/run_assay.sh`` runs the checkout's ``src/`` while the GUI
runs the code installed in its image (whole-project review, 2026-11-17, P1). The fingerprint is a
SHA-256 over every file of the installed package (code, report templates, the default
configuration with its limits), so two records with the same fingerprint were made by the same
code and rules, wherever they ran. The commit comes from ``QAC_GIT_COMMIT`` /
``QAC_GIT_DIRTY`` (set by ``scripts/run_assay.sh``) or from git itself when the package runs from
a checkout; otherwise it is "unknown".
"""

from __future__ import annotations

import hashlib
import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path

from . import __version__

log = logging.getLogger(__name__)

PACKAGE_DIR = Path(__file__).resolve().parent
_SKIP_DIRS = {"__pycache__"}
_SKIP_SUFFIXES = {".pyc", ".pyo"}
UNKNOWN = "unknown"


@lru_cache(maxsize=1)
def code_fingerprint() -> str:
    """SHA-256 over the relative path and content of every file of the package."""
    digest = hashlib.sha256()
    files = sorted(
        p
        for p in PACKAGE_DIR.rglob("*")
        if p.is_file()
        and not _SKIP_DIRS.intersection(p.relative_to(PACKAGE_DIR).parts)
        and p.suffix not in _SKIP_SUFFIXES
    )
    for p in files:
        digest.update(p.relative_to(PACKAGE_DIR).as_posix().encode("utf-8") + b"\0")
        digest.update(p.read_bytes() + b"\0")
    return digest.hexdigest()


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(PACKAGE_DIR), *args],
            capture_output=True, text=True, timeout=10, check=True,
        )  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip()


@lru_cache(maxsize=1)
def git_revision() -> tuple[str, str]:
    """``(commit, dirty)``: the commit the code comes from and whether the package's files had
    local changes ("yes", "no"); "unknown" for either when it cannot be read."""
    commit = os.environ.get("QAC_GIT_COMMIT", "").strip()
    if commit:
        dirty = os.environ.get("QAC_GIT_DIRTY", "").strip().lower()
        return commit, dirty if dirty in ("yes", "no") else UNKNOWN
    head = _git("rev-parse", "HEAD")
    if not head:
        return UNKNOWN, UNKNOWN
    status = _git("status", "--porcelain", "--untracked-files=no", "--", ".")
    return head, UNKNOWN if status is None else ("yes" if status else "no")


def tool_info() -> dict[str, str]:
    """The ``tool`` block of every record."""
    commit, dirty = git_revision()
    return {
        "name": "qpcr-assay-check",
        "version": __version__,
        "code_fingerprint": code_fingerprint(),
        "git_commit": commit,
        "git_dirty": dirty,
    }
