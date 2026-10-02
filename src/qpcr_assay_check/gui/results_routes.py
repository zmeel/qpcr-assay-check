"""Routes of the Results pages (phase G4): every record per assay, one record with its report
shown in the page, and the record's files to download.

The report is the record's own ``report.html``, unchanged on disk. The GUI serves it with a
policy of its own: it may only be framed by the GUI, may run no script and load nothing from
elsewhere (it needs none: the report is self-contained), and its links (to NCBI) open in a new
tab. The frame is sandboxed as well, so the report cannot reach the GUI's session.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from .records import RecordIndex

# the files a record holds that the GUI hands out (nothing else in the folder is served)
RECORD_FILES = {
    "report.html": "text/html; charset=utf-8",
    "results.json": "application/json",
    "results.xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "hits.tsv": "text/tab-separated-values; charset=utf-8",
}
REPORT_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src data:; frame-ancestors 'self'; "
    "form-action 'none'"
)


class _NoRecord(Exception):
    """A record (or file) that does not exist, or a path the GUI refuses."""


def register_results_routes(
    app: FastAPI,
    *,
    records: RecordIndex,
    page: Callable[..., Response],
    require_login: Callable[[Request], str],
) -> None:
    """Add the Results pages to ``app``."""

    @app.exception_handler(_NoRecord)
    async def no_record(request: Request, exc: _NoRecord) -> Response:
        return page(request, "not_found.html", 404, active="results")

    def _record(slug: str, run: str) -> Any:
        try:
            return records.get(slug, run)
        except KeyError as exc:
            raise _NoRecord() from exc

    @app.get("/results", response_class=HTMLResponse)
    def results(request: Request, user: str = Depends(require_login)) -> Response:
        every = records.all()
        groups: dict[str, list[Any]] = {}
        for r in every:
            groups.setdefault(r.assay_slug, []).append(r)
        return page(request, "results.html", active="results", groups=groups,
                    results_dir=records.results_dir)  # fmt: skip

    @app.get("/results/{slug}", response_class=HTMLResponse)
    def results_of(request: Request, slug: str, user: str = Depends(require_login)) -> Response:
        runs = records.of_assay(slug)
        if not runs:
            raise _NoRecord()
        return page(request, "results_assay.html", active="results", slug=slug, runs=runs)

    @app.get("/results/{slug}/{run}", response_class=HTMLResponse)
    def result(
        request: Request, slug: str, run: str, user: str = Depends(require_login)
    ) -> Response:
        rec = _record(slug, run)
        folder = records.record_dir(slug, run)
        files = [(n, (folder / n).stat().st_size) for n in RECORD_FILES if (folder / n).is_file()]
        others = [r for r in records.of_assay(slug) if r.run != run][:8]
        return page(request, "result.html", active="results", rec=rec, files=files,
                    others=others, has_report=(folder / "report.html").is_file())  # fmt: skip

    @app.get("/records/{slug}/{run}/{name}")
    def record_file(
        slug: str, run: str, name: str, download: int = 0, user: str = Depends(require_login)
    ) -> Response:
        if name not in RECORD_FILES:
            raise _NoRecord()
        try:
            path = records.record_dir(slug, run) / name
        except KeyError as exc:
            raise _NoRecord() from exc
        if not path.is_file():
            raise _NoRecord()
        if name == "report.html" and not download:
            html = path.read_text(encoding="utf-8")
            # links open in a new tab; the file on disk stays as written
            html = html.replace("<head>", '<head><base target="_blank">', 1)
            return HTMLResponse(html, headers={
                "Content-Security-Policy": REPORT_CSP, "X-Frame-Options": "SAMEORIGIN",
            })  # fmt: skip
        inline = name == "report.html" and not download
        return FileResponse(
            path, media_type=RECORD_FILES[name], filename=f"{run}-{name}",
            content_disposition_type="inline" if inline else "attachment",
        )  # fmt: skip
