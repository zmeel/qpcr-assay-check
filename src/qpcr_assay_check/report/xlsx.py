"""Excel workbook output (openpyxl)."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..results import RunResult

_FILL = {
    "PASS": "D7EFE3",
    "WARN": "FBE7C0",
    "FAIL": "F4CFCF",
    "INFO": "E6EAEE",
    "INCOMPLETE": "D9DFE8",
}


def _sheet(
    wb: Workbook, title: str, header: list[str], rows: list[list[object]], status_col: int | None
) -> None:
    ws = wb.create_sheet(title)
    ws.append(header)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    if status_col is not None:
        for r in ws.iter_rows(min_row=2):
            cell = r[status_col]
            colour = _FILL.get(str(cell.value))
            if colour:
                cell.fill = PatternFill("solid", fgColor=colour)
    for i, col in enumerate(ws.columns, start=1):
        width = min(80, max(len(str(c.value)) if c.value is not None else 0 for c in col) + 2)
        ws.column_dimensions[get_column_letter(i)].width = max(10, width)
    for r in ws.iter_rows(min_row=2):
        for cell in r:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws.freeze_panes = "A2"


def write_workbook(result: RunResult, path: Path) -> None:
    """Write summary, inputs, QC checks, structures, and section states."""
    wb = Workbook()
    wb.remove(wb.active)
    a = result.assay
    _sheet(
        wb,
        "Summary",
        ["Item", "Value"],
        [
            ["Assay", a.assay_name],
            ["Overall verdict", result.overall.verdict.value],
            ["Mode", result.mode],
            ["Run ID", result.run_id],
            ["Generated (UTC)", result.generated_at],
            ["Tool version", result.tool["version"]],
            ["Inputs hash (SHA-256)", result.inputs_hash],
            ["Data sent to NCBI", "yes" if result.network_used else "no"],
            *[["Rationale", line] for line in result.overall.rationale],
        ],
        None,
    )
    _sheet(
        wb,
        "Inputs",
        ["Field", "Value"],
        [
            ["forward (5'-3')", a.forward],
            ["reverse (5'-3')", a.reverse],
            ["probe (5'-3')", a.probe],
            ["probe reporter", a.probe_reporter or ""],
            ["probe quencher", a.probe_quencher or ""],
            ["probe modifications", ", ".join(a.probe_modifications)],
            ["template type", a.template_type.value],
            ["target taxid", a.target.taxid or ""],
            ["target accession", a.target.accession or ""],
            ["target gene", a.target.gene or ""],
            ["oligo source", a.oligo_source or ""],
        ],
        None,
    )
    _sheet(
        wb,
        "Oligo QC",
        ["Subject", "Check", "Value", "Unit", "Status", "Message", "Rule"],
        [
            [c.subject, c.name, c.display, c.unit, c.status.value, c.message, c.rule]
            for c in result.oligo_qc.checks
        ],
        4,
    )
    _sheet(
        wb,
        "Structures",
        [
            "Structure",
            "Kind",
            "Found",
            "Tm (°C)",
            "ΔG (kcal/mol)",
            "At (°C)",
            "Status",
            "Combinations evaluated",
        ],
        [
            [
                s.label,
                s.kind,
                "yes" if s.found else "no",
                None if s.tm_c is None else round(s.tm_c, 1),
                None if s.dg_kcal is None else round(s.dg_kcal, 2),
                s.temp_c,
                s.status.value,
                f"{s.n_evaluated}/{s.n_total}",
            ]
            for s in result.oligo_qc.structures
        ],
        6,
    )
    _sheet(
        wb,
        "Sections",
        ["Section", "State", "Verdict", "Note"],
        [[s.title, s.state, s.verdict.value if s.verdict else "", s.note] for s in result.sections],
        None,
    )
    wb.save(path)
