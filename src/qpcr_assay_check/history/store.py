"""Locate the most recent previous run for an assay, from the results directory layout.

No separate index or database: every run already writes ``results.json`` under
``<base_dir>/<assay.slug>/<run_id>/``, and ``run_id`` embeds the generation timestamp -- exactly
the "history as files" design in docs/ARCHITECTURE.md. The previous run is simply the most
recently *generated* one already on disk for this assay's slug, found by reading each
``results.json``'s own ``generated_at`` field (not by parsing directory names).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from ..results import RunResult

log = logging.getLogger(__name__)


def find_previous_run(base_dir: Path, assay_slug: str) -> RunResult | None:
    """The most recently generated run for ``assay_slug``, or ``None`` if none exists yet.

    A run directory whose ``results.json`` is missing, unreadable, or fails to validate against
    the current schema is skipped with a warning rather than raising: a corrupt or foreign-version
    record must not abort the current evaluation, only be left out of the comparison.
    """
    parent = base_dir / assay_slug
    if not parent.is_dir():
        return None
    latest: RunResult | None = None
    for run_dir in parent.iterdir():
        results_file = run_dir / "results.json"
        if not results_file.is_file():
            continue
        try:
            data = json.loads(results_file.read_text(encoding="utf-8"))
            result = RunResult.model_validate(data)
        except (OSError, ValueError, ValidationError) as exc:
            log.warning("Skipping unreadable previous run at %s: %s", results_file, exc)
            continue
        if latest is None or result.generated_at > latest.generated_at:
            latest = result
    return latest
