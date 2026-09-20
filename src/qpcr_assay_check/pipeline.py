"""Orchestration: turn an assay + configuration into a complete, versioned evaluation record."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
from datetime import UTC, datetime
from pathlib import Path

import primer3

from . import __version__
from .config import Config
from .models import Assay, Status
from .oligo.qc import run_oligo_qc
from .results import OverallResult, RunResult, SectionResult
from .verdict import Verdict, combine, exit_code, verdict_from_status

log = logging.getLogger(__name__)

#: (key, title, version in which the section becomes available)
PLANNED_SECTIONS: list[tuple[str, str, str]] = [
    ("specificity", "Remote specificity search (NCBI BLAST, tiered)", "0.2.0"),
    ("amplicon_prediction", "Off-target amplicon prediction", "0.3.0"),
    ("exclusivity", "Exclusivity against the clinical organism list", "0.4.0"),
    ("inclusivity", "Inclusivity across the intended target (sampled)", "0.4.0"),
    ("history", "Comparison with the previous run", "1.0.0"),
]


def inputs_hash(assay: Assay, cfg: Config) -> str:
    """SHA-256 over the canonical JSON of the assay definition and the effective config."""
    payload = {"assay": assay.model_dump(mode="json"), "config": cfg.model_dump(mode="json")}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _rationale(qc_findings: list[str], not_evaluated: list[str]) -> list[str]:
    lines = list(qc_findings)
    if not_evaluated:
        lines.append("Not evaluated: " + "; ".join(not_evaluated) + ".")
    return lines


def evaluate(
    assay: Assay,
    cfg: Config,
    *,
    qc_only: bool = False,
    now: datetime | None = None,
) -> RunResult:
    """Run every analysis that exists in this version and assemble the evaluation record."""
    now = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    digest = inputs_hash(assay, cfg)
    qc = run_oligo_qc(assay, cfg)

    findings = [
        f"{c.name}: {c.message}"
        for c in qc.checks
        if c.status in (Status.FAIL, Status.WARN) and c.message
    ]
    findings += [
        f"{s.label}: structure with Tm {s.tm_c:.1f} °C at {s.temp_c:g} °C ({s.status.value})."
        for s in qc.structures
        if s.status in (Status.FAIL, Status.WARN) and s.tm_c is not None
    ]

    sections = [
        SectionResult(
            key="oligo_qc",
            title="Oligo quality control",
            state="evaluated",
            verdict=verdict_from_status(qc.status),
            note=(
                f"{sum(c.status is Status.FAIL for c in qc.checks)} FAIL, "
                f"{sum(c.status is Status.WARN for c in qc.checks)} WARN among "
                f"{len(qc.checks)} checks; "
                f"{sum(s.status in (Status.WARN, Status.FAIL) for s in qc.structures)} of "
                f"{len(qc.structures)} structure calculations flagged."
            ),
        )
    ]
    for key, title, since in PLANNED_SECTIONS:
        sections.append(
            SectionResult(
                key=key,
                title=title,
                state="skipped" if qc_only else "not_implemented",
                verdict=None,
                note=(
                    "Skipped (--qc-only)."
                    if qc_only
                    else f"Not available in v{__version__}; planned for v{since}."
                ),
                available_from=since,
            )
        )

    required = ["oligo_qc"] if qc_only else [s.key for s in sections]
    by_key: dict[str, Verdict | None] = {s.key: s.verdict for s in sections}
    verdict = combine(by_key, required)
    not_evaluated = [s.title for s in sections if s.key in required and s.verdict is None]

    if not findings and verdict is Verdict.PASS:
        findings = ["No oligo QC check raised a WARN or FAIL."]
    overall = OverallResult(
        verdict=verdict,
        exit_code=exit_code(verdict),
        rationale=_rationale(findings, not_evaluated),
        required_sections=required,
    )

    return RunResult(
        tool={"name": "qpcr-assay-check", "version": __version__},
        run_id=f"{assay.slug}-{now:%Y%m%dT%H%M%SZ}-{digest[:8]}",
        generated_at=now.isoformat().replace("+00:00", "Z"),
        inputs_hash=digest,
        mode="qc-only" if qc_only else "full",
        network_used=False,
        environment={
            "python": platform.python_version(),
            "platform": platform.platform(),
            "primer3-py": getattr(primer3, "__version__", "unknown"),
        },
        assay=assay,
        config=cfg.model_dump(mode="json"),
        oligo_qc=qc,
        sections=sections,
        overall=overall,
    )


def write_outputs(result: RunResult, base_dir: Path, cfg: Config) -> Path:
    """Write results.json, report.html and results.xlsx; return the run directory."""
    from .report.html import render_report
    from .report.xlsx import write_workbook

    parent = base_dir / result.assay.slug
    parent.mkdir(parents=True, exist_ok=True)
    run_dir = parent / result.run_id
    for attempt in range(2, 100):  # never overwrite an existing evaluation record
        try:
            run_dir.mkdir()
            break
        except FileExistsError:
            run_dir = parent / f"{result.run_id}-{attempt}"
    else:  # pragma: no cover - would need ~100 runs in one second
        raise RuntimeError(f"could not create a unique run directory under {parent}")
    (run_dir / "results.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
    (run_dir / "report.html").write_text(render_report(result, cfg), encoding="utf-8")
    write_workbook(result, run_dir / "results.xlsx")
    log.info("Wrote evaluation record to %s", run_dir)
    return run_dir
