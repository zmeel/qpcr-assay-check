"""Excel workbook output (openpyxl)."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..history.models import HistoryResult
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


def _history_rows(hist: HistoryResult) -> list[list[object]]:
    rows: list[list[object]] = [
        ["run", "", "Previous run", "", hist.previous_run_id or ""],
        ["run", "", "Previous generated (UTC)", "", hist.previous_generated_at or ""],
        ["run", "", "Assay/config changed since then", "", "yes" if hist.inputs_changed else "no"],
    ]
    for sc in hist.section_changes:
        if sc.changed:
            before = sc.verdict_before.value if sc.verdict_before else ""
            after = sc.verdict_after.value if sc.verdict_after else ""
            rows.append(["section", sc.title, "", before, after])
    for s in hist.new_sites:
        where = f"{s.role} {s.accession}:{s.subject_start}-{s.subject_end}"
        rows.append(["site: new", s.tier, where, "", s.level_after])
    for s in hist.resolved_sites:
        where = f"{s.role} {s.accession}:{s.subject_start}-{s.subject_end}"
        rows.append(["site: resolved", s.tier, where, s.level_before, ""])
    for s in hist.changed_sites:
        where = f"{s.role} {s.accession}:{s.subject_start}-{s.subject_end}"
        before = f"{s.level_before}, {s.n_mismatch_before} mm"
        after = f"{s.level_after}, {s.n_mismatch_after} mm"
        rows.append(["site: changed", s.tier, where, before, after])
    for a in hist.new_amplicons:
        where = f"{a.accession}:{a.start}-{a.end} ({a.roles})"
        rows.append(["amplicon: new", a.tier, where, "", a.classification or ""])
    for a in hist.resolved_amplicons:
        where = f"{a.accession}:{a.start}-{a.end} ({a.roles})"
        rows.append(["amplicon: resolved", a.tier, where, a.classification or "", ""])
    for c in hist.inclusivity_changes:
        before = (
            f"{c.percent_before:.0f}% of {c.sample_size_before}"
            if c.percent_before is not None
            else ""
        )
        after = (
            f"{c.percent_after:.0f}% of {c.sample_size_after}"
            if c.percent_after is not None
            else ""
        )
        rows.append(["inclusivity", c.role, f"year {c.year}", before, after])
    return rows


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
    spec = result.specificity
    if spec is not None:
        _sheet(
            wb,
            "Off-target sites",
            ["Tier", "Query", "Accession", "Organism", "Strand", "Start", "End", "Level", "Source",
             "Mismatches", "Gaps", "Clean 3' nt", "Duplex Tm (°C)", "ΔTm (°C)", "Oligo", "Subject"],
            [
                [s.tier, s.query, s.accession, s.organism or "", s.orientation, s.subject_start,
                 s.subject_end, s.level, s.source, s.n_mismatch, s.n_gap, s.clean_3prime_nt,
                 None if s.tm_c is None else round(s.tm_c, 1),
                 None if s.delta_tm_c is None else round(s.delta_tm_c, 1), s.q_aln, s.s_aln]
                for s in spec.sites
            ],
            None,
        )  # fmt: skip
        _sheet(
            wb,
            "Predicted products",
            ["ID", "Tier", "Accession", "Organism", "Start", "End", "Length (bp)", "Primers",
             "Class", "Probe site", "Record", "Note"],
            [
                [a.id, a.tier, a.accession, a.organism or "", a.start, a.end, a.length, a.roles,
                 a.classification, a.probe_site or "", a.record_type, a.note]
                for a in spec.amplicons
            ],
            None,
        )  # fmt: skip
        _sheet(
            wb,
            "Searches",
            ["Tier", "Search", "Taxa", "RID", "Hits (per query)", "Perfect full-length hits"],
            [
                [r["tier"], r["label"], ", ".join(map(str, r["taxids"])), r.get("rid") or "",
                 str(r["n_hits"]), str(r.get("perfect_full_length", ""))]
                for r in spec.searches
            ],
            None,
        )  # fmt: skip
        _sheet(
            wb,
            "Findings",
            ["Severity", "Topic", "Message"],
            [[f.severity, f.topic, f.message] for f in spec.findings],
            0,
        )
    excl = result.exclusivity
    if excl is not None:
        _sheet(
            wb,
            "Exclusivity",
            ["Organism", "Resolution", "Taxonomy ID", "Sites", "Best site", "Best level",
             "Predicted product"],
            [
                [row.organism, row.resolution, row.taxid or "", row.n_sites,
                 row.best_site_id or "", row.best_site_level or "",
                 row.amplicon_classification or ("no" if not row.amplicon_predicted else "")]
                for row in excl.rows
            ],
            5,
        )  # fmt: skip
    if result.taxonomy_breakdown:
        _sheet(
            wb,
            "Taxonomy breakdown",
            ["Taxonomy ID", "Scientific name", "Species", "Genus", "Family", "Sites"],
            [
                [t.taxid, t.scientific_name, t.species or "", t.genus or "", t.family or "",
                 t.n_sites]
                for t in result.taxonomy_breakdown
            ],
            None,
        )  # fmt: skip
    incl = result.inclusivity
    if incl is not None and incl.oligos:
        _sheet(
            wb,
            "Inclusivity",
            ["Oligo", "Year", "Population", "Sample size", "Perfect", "1 mismatch",
             "2+ mismatch/gap", "3' mismatch", "Fetch failed"],
            [
                [o.role, w.year, w.population_size if w.population_size is not None else "",
                 w.sample_size, w.n_perfect, w.n_one_mismatch, w.n_two_plus_mismatch,
                 w.n_three_prime_mismatch, w.n_fetch_failed]
                for o in incl.oligos
                for w in o.windows
            ],
            None,
        )  # fmt: skip
    hist = result.history
    if hist is not None and hist.has_previous:
        _sheet(
            wb, "History", ["Kind", "Tier/Role", "Description", "Before", "After"],
            _history_rows(hist), None,
        )  # fmt: skip
    _sheet(
        wb,
        "Sections",
        ["Section", "State", "Verdict", "Note"],
        [[s.title, s.state, s.verdict.value if s.verdict else "", s.note] for s in result.sections],
        None,
    )
    wb.save(path)
