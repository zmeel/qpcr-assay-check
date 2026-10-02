"""The evaluation records under ``<work>/results`` as the dashboard shows them.

Each run directory holds a ``results.json`` (see :mod:`qpcr_assay_check.pipeline`). Only a few
top-level fields are read; files are cached by modification time, since a record of a large
genome analysis can be tens of megabytes.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..verdict import STATUS_LABEL, Verdict

log = logging.getLogger(__name__)

SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")
STATUS_CLASS = {
    Verdict.PASS: "ok",
    Verdict.WARN: "review",
    Verdict.FAIL: "exceeds",
    Verdict.INCOMPLETE: "incomplete",
}


@dataclass
class Check:
    """One evaluated section of a record."""

    title: str
    status: str
    css: str


@dataclass
class RunRecord:
    """The headline of one evaluation record."""

    path: Path
    run_id: str
    assay_name: str
    assay_slug: str
    generated_at: str
    mode: str
    tool_version: str
    status: str
    css: str
    checks: list[Check] = field(default_factory=list)
    inclusivity_line: str = ""
    inclusivity_status: str = ""
    inclusivity_css: str = ""
    assessed: int | None = None  # genomes or records assessed so far (exhaustive analysis)
    listed: int | None = None

    @property
    def date(self) -> str:
        return self.generated_at[:10]

    @property
    def run(self) -> str:
        """The record's folder name (``<work>/results/<assay_slug>/<run>``)."""
        return self.path.parent.name


def _status(verdict: str | None) -> tuple[str, str]:
    try:
        v = Verdict(verdict)
    except ValueError:
        return "Not assessed", "incomplete"
    return STATUS_LABEL[v], STATUS_CLASS[v]


def read_record(path: Path) -> RunRecord | None:
    """The headline of one ``results.json``; None when it cannot be read."""
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        assay = data.get("assay") or {}
        overall = data.get("overall") or {}
        status, css = _status(overall.get("verdict"))
        checks = [
            Check(s.get("title") or s.get("key", ""), *_status(s.get("verdict")))
            for s in data.get("sections") or []
            if s.get("state") == "evaluated"
        ]
        inc = data.get("inclusivity") or {}
        rationale = inc.get("rationale") or []
        coverage = (data.get("variant_summary") or {}).get("coverage") or {}
        inc_status, inc_css = _status(inc.get("verdict")) if inc else ("", "")
        return RunRecord(
            path=path,
            run_id=str(data["run_id"]),
            assay_name=str(assay.get("assay_name") or "unnamed assay"),
            assay_slug=path.parent.parent.name,
            generated_at=str(data.get("generated_at") or ""),
            mode=str(data.get("mode") or ""),
            tool_version=str((data.get("tool") or {}).get("version") or ""),
            status=status,
            css=css,
            checks=checks,
            inclusivity_line=str(rationale[0]) if rationale else "",
            inclusivity_status=inc_status,
            inclusivity_css=inc_css,
            assessed=coverage.get("assessed_total"),
            listed=coverage.get("listed_total"),
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        log.warning("GUI: cannot read %s: %s", path, exc)
        return None


class RecordIndex:
    """Every record under ``<work>/results/<assay>/<run>/results.json``, newest first."""

    def __init__(self, results_dir: Path) -> None:
        self.results_dir = Path(results_dir)
        self._cache: dict[Path, tuple[float, RunRecord | None]] = {}

    def all(self) -> list[RunRecord]:
        out: list[RunRecord] = []
        seen: set[Path] = set()
        for path in self.results_dir.glob("*/*/results.json"):
            seen.add(path)
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            cached = self._cache.get(path)
            if cached is None or cached[0] != mtime:
                cached = (mtime, read_record(path))
                self._cache[path] = cached
            if cached[1] is not None:
                out.append(cached[1])
        for gone in set(self._cache) - seen:
            del self._cache[gone]
        return sorted(out, key=lambda r: r.generated_at, reverse=True)

    def record_dir(self, slug: str, run: str) -> Path:
        """The folder of one record, checked to lie inside the results folder."""
        if not (SEGMENT.match(slug) and SEGMENT.match(run)):
            raise KeyError(f"{slug}/{run}")
        folder = (self.results_dir / slug / run).resolve()
        if folder.parent.parent != self.results_dir.resolve() or not folder.is_dir():
            raise KeyError(f"{slug}/{run}")
        return folder

    def get(self, slug: str, run: str) -> RunRecord:
        path = self.record_dir(slug, run) / "results.json"
        found = next((r for r in self.all() if r.path.resolve() == path), None)
        if found is None:
            raise KeyError(f"{slug}/{run}")
        return found

    def of_assay(self, slug: str) -> list[RunRecord]:
        return [r for r in self.all() if r.assay_slug == slug]

    def latest_per_assay(self) -> list[RunRecord]:
        """The newest record of each assay (newest assay first)."""
        latest: dict[str, RunRecord] = {}
        for r in self.all():
            latest.setdefault(r.assay_slug, r)
        return list(latest.values())
