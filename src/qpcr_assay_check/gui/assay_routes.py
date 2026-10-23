"""Routes of the Assays pages (phase G2): list, new, upload, editor (form and YAML), live
validation, QC-only runs and deletion. Every POST checks the session's form token."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from starlette.datastructures import UploadFile

from ..errors import QpcrAssayCheckError
from .assays import (
    MAX_BYTES,
    TOO_LARGE,
    AssayFileError,
    AssayFiles,
    check_name,
    parse_mapping,
    validate_text,
)
from .form import ROLES, TEMPLATE_TYPES, FormValues, OligoRow, apply, values_of

if TYPE_CHECKING:
    from .app import GuiSettings

log = logging.getLogger(__name__)

QC_LABEL = {"PASS": "within", "WARN": "outside preferred", "FAIL": "outside limit", "INFO": "info"}
QC_CSS = {"PASS": "ok", "WARN": "review", "FAIL": "exceeds", "INFO": "incomplete"}
UPLOAD_FORM_OVERHEAD = 64_000  # bytes of multipart framing and the form's other fields
_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$")


def _template_text() -> str:
    """The blank, fully commented assay template the command line's ``init`` writes."""
    return (resources.files("qpcr_assay_check") / "data" / "assay_template.yaml").read_text(
        encoding="utf-8"
    )


def _upload_name(given: str, filename: str) -> str:
    """The name to save an upload as: the one typed in, else the uploaded file's own name.

    Browsers send a bare file name, but some old ones send a client path; only its last part is
    kept. ``.yaml`` is added when there is no extension, as for a new assay.
    """
    name = given.strip() or re.split(r"[/\\]", filename or "")[-1].strip()
    if not name:
        raise AssayFileError("the uploaded file has no name; type one under 'Save as'")
    if not name.endswith((".yaml", ".yml")):
        name += ".yaml"
    return check_name(name)


def _upload_text(data: bytes) -> str:
    """The uploaded bytes as assay text: UTF-8 (a byte-order mark is dropped), a YAML mapping."""
    if len(data) > MAX_BYTES:
        raise AssayFileError(TOO_LARGE)
    try:
        text = data.decode("utf-8-sig").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise AssayFileError(
            "the file is not UTF-8 text; save it as UTF-8 and upload again"
        ) from exc
    if not text.strip():
        raise AssayFileError("the file is empty")
    parse_mapping(text)
    return text


def _rows_from_form(form: Any) -> list[OligoRow]:
    get = form.getlist
    fields = [get(k) for k in ("o_role", "o_original", "o_name", "o_sequence", "o_reporter",
                               "o_quencher", "o_mods")]  # fmt: skip
    removed = set(get("o_remove"))
    rows: list[OligoRow] = []
    for i, (role, original, name, seq, rep, qu, mods) in enumerate(zip(*fields, strict=False)):
        if role not in ROLES:
            continue
        if not original and not name.strip() and not seq.strip():
            continue  # the empty "add" row
        rows.append(OligoRow(role, name, seq, rep, qu, mods, original, str(i) in removed))
    return rows


def register_assay_routes(
    app: FastAPI,
    *,
    settings: GuiSettings,
    page: Callable[..., Response],
    require_login: Callable[[Request], str],
    csrf_ok: Callable[[Request, str], bool],
) -> None:
    """Add the Assays pages to ``app``."""
    work = Path(settings.work_dir)
    files = AssayFiles(work / "assays", settings.examples_dir)
    results_dir = work / "results"

    def editor(
        request: Request, name: str, *, tab: str, text: str | None = None,
        values: FormValues | None = None, error: str = "", saved: bool = False,
        status_code: int = 200,
    ) -> Response:  # fmt: skip
        text = files.read(name) if text is None else text
        check = validate_text(text, settings.config())
        if values is None:
            try:
                values = values_of(text)
            except AssayFileError as exc:
                values, tab = None, "yaml"
                error = error or f"The form cannot read this file ({exc}); edit it as YAML."
        return page(
            request, "assay_edit.html", status_code, active="assays", name=name, tab=tab,
            text=text, values=values, check=check, error=error, saved=saved, roles=ROLES,
            template_types=TEMPLATE_TYPES, qc_label=QC_LABEL, qc_css=QC_CSS,
        )  # fmt: skip

    def _known(name: str) -> str:
        try:
            check_name(name)
        except AssayFileError as exc:
            raise _NotFound() from exc
        if not files.exists(name):
            raise _NotFound()
        return name

    @app.exception_handler(_NotFound)
    async def not_found(request: Request, exc: _NotFound) -> Response:
        return page(request, "not_found.html", 404, active="assays")

    @app.get("/assays", response_class=HTMLResponse)
    def assay_list(
        request: Request, user: str = Depends(require_login), error: str = ""
    ) -> Response:
        return page(
            request, "assays.html", active="assays", assays=files.list(),
            examples=files.examples(), error=error, assays_dir=files.dir,
        )  # fmt: skip

    @app.post("/assays/new")
    async def assay_new(request: Request, user: str = Depends(require_login)) -> Response:
        form = await request.form()
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return RedirectResponse("/assays", status_code=303)
        name = str(form.get("name", "")).strip()
        source = str(form.get("source", "template"))
        if name and not name.endswith((".yaml", ".yml")):
            name += ".yaml"
        try:
            text = files.example_text(source[8:]) if source.startswith("example:") else (
                _template_text()
            )  # fmt: skip
            files.create(check_name(name), text)
        except (AssayFileError, OSError) as exc:
            return page(
                request, "assays.html", 400, active="assays", assays=files.list(),
                examples=files.examples(), error=str(exc), assays_dir=files.dir,
            )  # fmt: skip
        return RedirectResponse(f"/assays/{name}", status_code=303)

    @app.post("/assays/upload")
    async def assay_upload(request: Request, user: str = Depends(require_login)) -> Response:
        """Save an uploaded assay file as it is and open it in the editor; never overwrite."""

        def refused(problem: str) -> Response:
            return page(
                request, "assays.html", 400, active="assays", assays=files.list(),
                examples=files.examples(), error=f"Not uploaded: {problem}", assays_dir=files.dir,
            )  # fmt: skip

        # a friendlier answer than the app-wide 413 (gui/limits.py) for a file just over the
        # limit, before Starlette spools it; the check after reading stays as well
        length = request.headers.get("content-length", "")
        if length.isdigit() and int(length) > MAX_BYTES + UPLOAD_FORM_OVERHEAD:
            return refused(TOO_LARGE)
        form = await request.form()
        try:
            if not csrf_ok(request, str(form.get("csrf", ""))):
                return RedirectResponse("/assays", status_code=303)
            upload = form.get("file")
            if not isinstance(upload, UploadFile) or not (upload.filename or "").strip():
                raise AssayFileError("choose a file to upload")
            name = _upload_name(str(form.get("name", "")), upload.filename or "")
            text = _upload_text(await upload.read(MAX_BYTES + 1))
            if files.exists(name):
                raise AssayFileError(
                    f"an assay file named {name} already exists, so the upload was not saved: "
                    "give it another name under 'Save as', or delete the existing one first"
                )
            files.create(name, text)
        except (AssayFileError, OSError) as exc:
            return refused(str(exc))
        finally:
            await form.close()  # releases the spooled temporary file
        log.info("GUI: assay file %s uploaded by %s", name, user)
        return RedirectResponse(f"/assays/{name}", status_code=303)

    @app.get("/assays/{name}", response_class=HTMLResponse)
    def assay_edit(
        request: Request, name: str, tab: str = "form", saved: int = 0, error: str = "",
        user: str = Depends(require_login),
    ) -> Response:  # fmt: skip
        _known(name)
        return editor(request, name, tab="yaml" if tab == "yaml" else "form",
                      saved=bool(saved), error=error)  # fmt: skip

    @app.post("/assays/{name}/yaml")
    async def assay_save_yaml(
        request: Request, name: str, user: str = Depends(require_login)
    ) -> Response:
        _known(name)
        form = await request.form()
        text = str(form.get("text", "")).replace("\r\n", "\n")
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return editor(request, name, tab="yaml", text=text, status_code=400,
                          error="The form expired; your text is below. Save again.")  # fmt: skip
        try:
            parse_mapping(text)
            files.save(name, text)
        except AssayFileError as exc:
            return editor(request, name, tab="yaml", text=text, status_code=400,
                          error=f"Not saved: {exc}")  # fmt: skip
        return RedirectResponse(f"/assays/{name}?tab=yaml&saved=1", status_code=303)

    @app.post("/assays/{name}/form")
    async def assay_save_form(
        request: Request, name: str, user: str = Depends(require_login)
    ) -> Response:
        _known(name)
        form = await request.form()
        values = FormValues(
            assay_name=str(form.get("assay_name", "")),
            template_type=str(form.get("template_type", "DNA")),
            taxid=str(form.get("taxid", "")),
            annealing=str(form.get("annealing", "")),
            exclusivity=str(form.get("exclusivity", "")),
            oligos=_rows_from_form(form),
        )
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return editor(
                request,
                name,
                tab="form",
                values=values,
                status_code=400,
                error="The form expired; your entries are below. Save again.",
            )
        try:
            text = apply(files.read(name), values)
            files.save(name, text)
        except AssayFileError as exc:
            return editor(request, name, tab="form", values=values, status_code=400,
                          error=f"Not saved: {exc}")  # fmt: skip
        return RedirectResponse(f"/assays/{name}?tab=form&saved=1", status_code=303)

    @app.post("/assays/{name}/validate", response_class=HTMLResponse)
    async def assay_validate(
        request: Request, name: str, user: str = Depends(require_login)
    ) -> Response:
        form = await request.form()
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return HTMLResponse("", status_code=400)
        check = validate_text(str(form.get("text", "")), settings.config())
        return page(request, "_validation.html", check=check, qc_label=QC_LABEL, qc_css=QC_CSS)

    @app.post("/assays/{name}/delete")
    async def assay_delete(
        request: Request, name: str, user: str = Depends(require_login)
    ) -> Response:
        _known(name)
        form = await request.form()
        if csrf_ok(request, str(form.get("csrf", ""))):
            files.delete(name)
        return RedirectResponse("/assays", status_code=303)

    @app.post("/assays/{name}/qc")
    async def assay_qc(request: Request, name: str, user: str = Depends(require_login)) -> Response:
        _known(name)
        form = await request.form()
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return RedirectResponse(f"/assays/{name}", status_code=303)
        check = validate_text(files.read(name), settings.config())
        if not check.ok or check.assay is None or check.cfg is None:
            return RedirectResponse(
                f"/assays/{name}?error=Fix+the+problems+listed+first", status_code=303
            )
        from ..pipeline import evaluate, write_outputs

        try:
            result = evaluate(check.assay, check.cfg, qc_only=True)
            run_dir = write_outputs(result, results_dir, check.cfg)
        except (QpcrAssayCheckError, OSError) as exc:
            log.warning("GUI: QC-only run of %s failed: %s", name, exc)
            return editor(request, name, tab="form", status_code=500,
                          error=f"The QC-only run failed: {exc}")  # fmt: skip
        log.info("GUI: QC-only record %s", run_dir)
        return RedirectResponse(
            f"/assays/{name}/qc/{run_dir.parent.name}/{run_dir.name}", status_code=303
        )

    @app.get("/assays/{name}/qc/{slug}/{run}", response_class=HTMLResponse)
    def assay_qc_result(
        request: Request, name: str, slug: str, run: str, user: str = Depends(require_login)
    ) -> Response:
        _known(name)
        if not (_SEGMENT.match(slug) and _SEGMENT.match(run)):
            raise _NotFound()
        path = (results_dir / slug / run / "results.json").resolve()
        if results_dir.resolve() not in path.parents or not path.is_file():
            raise _NotFound()
        data = json.loads(path.read_text(encoding="utf-8"))
        return page(
            request, "assay_qc.html", active="assays", name=name, record=data,
            run_dir=path.parent, qc_label=QC_LABEL, qc_css=QC_CSS,
        )  # fmt: skip


class _NotFound(Exception):
    """An assay file or record that does not exist (or a name the GUI refuses)."""
