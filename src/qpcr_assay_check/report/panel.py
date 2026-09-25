"""Write the panel escape check: panel.html, panel.xlsx and panel.json."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

from .. import __version__
from ..panel import PanelClass, PanelResult, slug
from .html import _environment
from .xlsx import _sheet

SHOWN = 200  # genomes per list in the HTML page (the workbook lists them all)


def _pct(n: int, total: int) -> str:
    return f"{100.0 * n / total:.1f}%" if total else "–"


def render_panel(result: PanelResult) -> str:
    template = _environment().get_template("panel.html.j2")
    none_rows = result.of_class(PanelClass.NONE)
    return template.render(
        p=result, version=__version__, pct=_pct, n_none=len(none_rows), none_rows=none_rows,
        some_rows=result.of_class(PanelClass.SOME), shown=SHOWN,
    )  # fmt: skip


def write_panel_workbook(result: PanelResult, path: Path) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    names = [m.assay_name for m in result.members]
    _sheet(
        wb, "Summary", ["Item", "Value"],
        [["Panel", result.panel_name], ["Target taxid", result.target_taxid],
         ["Excluded taxids", ", ".join(map(str, result.exclude_taxids))],
         ["Generated (UTC)", result.generated_at],
         ["Genomes processed by every assay", result.in_all],
         ["Genomes processed by only some assays", result.not_in_all],
         *[[f"Genomes {c}", n] for c, n in result.counts.items()],
         *[[f"Assay {i + 1}", f"{m.assay_name} ({m.file}): {m.processed} genomes"]
           for i, m in enumerate(result.members)],
         ["Statement", "In silico analysis does not replace experimental validation; the "
          "laboratory must verify this software within its own quality system."]],
        None,
    )  # fmt: skip
    classes = [c.value for c in PanelClass]
    _sheet(
        wb, "Per year", ["Year", "Genomes", *classes],
        [[y.year, y.genomes, *[y.counts.get(c, 0) for c in classes]] for y in result.years],
        None,
    )  # fmt: skip
    header = ["Accession", "Released", "Organism", "Panel outcome", *names]

    def rows(gs: list) -> list[list[object]]:
        return [[g.accession, g.release_date, g.organism, g.panel_class, *g.states] for g in gs]

    _sheet(wb, "Detected by no target", header, rows(result.of_class(PanelClass.NONE)), None)
    _sheet(wb, "Per genome", header, rows(result.genomes), None)
    wb.save(path)


def write_panel_outputs(result: PanelResult, base_dir: Path) -> Path:
    stamp = result.generated_at.replace("-", "").replace(":", "").replace("+0000", "Z")
    out = base_dir / f"panel-{slug(result.panel_name)}" / f"panel-{stamp[:15]}Z"
    out.mkdir(parents=True, exist_ok=True)
    (out / "panel.html").write_text(render_panel(result), encoding="utf-8")
    (out / "panel.json").write_text(result.model_dump_json(indent=1), encoding="utf-8")
    write_panel_workbook(result, out / "panel.xlsx")
    return out
