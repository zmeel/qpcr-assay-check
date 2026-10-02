"""Routes of the run pages (phase G3): new run with the search plan to confirm, the queue,
a run's live log and progress, cancel, and start again."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from ..errors import QpcrAssayCheckError
from .assays import AssayFileError, AssayFiles, check_name, validate_text
from .runs import STAGES, Job, JobStore, Runner, new_job_id, progress_of, read_from, read_tail

if TYPE_CHECKING:
    from .app import GuiSettings

LOG_LINES_SHOWN = 400


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def plan_view(assay: Any, cfg: Any) -> dict[str, Any]:
    """What would be sent to NCBI, as the command line's --dry-run lists it."""
    from ..search.planner import plan_searches

    plan = plan_searches(assay, cfg)
    tiers: dict[str, int] = {}
    for ps in plan.searches:
        tiers[ps.tier] = tiers.get(ps.tier, 0) + 1
    return {
        "queries": plan.queries,
        "searches": [
            {
                "tier": ps.tier,
                "title": ps.title,
                "where": ps.entrez_query or "no taxon restriction",
                "n_queries": len(ps.labels),
            }
            for ps in plan.searches
        ],  # fmt: skip
        "tiers": tiers,
        "notes": plan.notes,
        "warnings": plan.warnings,
    }


def register_run_routes(
    app: FastAPI,
    *,
    settings: GuiSettings,
    runner: Runner,
    page: Callable[..., Response],
    require_login: Callable[[Request], str],
    csrf_ok: Callable[[Request, str], bool],
) -> None:
    """Add the run pages to ``app``."""
    work = Path(settings.work_dir)
    files = AssayFiles(work / "assays", settings.examples_dir)
    store: JobStore = runner.store

    def _job(job_id: str) -> Job:
        try:
            return store.get(job_id)
        except KeyError as exc:
            raise _NoJob() from exc

    @app.exception_handler(_NoJob)
    async def no_job(request: Request, exc: _NoJob) -> Response:
        return page(request, "not_found.html", 404, active="run")

    def new_page(request: Request, status_code: int = 200, **ctx: Any) -> Response:
        ctx.setdefault("chosen", "")
        ctx.setdefault("error", "")
        return page(request, "run_new.html", status_code, active="newrun",
                    assays=files.list(), current=runner.current(),
                    queued=runner.queued(), **ctx)  # fmt: skip

    @app.get("/runs/new", response_class=HTMLResponse)
    def run_new(request: Request, assay: str = "", user: str = Depends(require_login)) -> Response:
        return new_page(request, chosen=assay)

    @app.post("/runs/plan", response_class=HTMLResponse)
    async def run_plan(request: Request, user: str = Depends(require_login)) -> Response:
        form = await request.form()
        name = str(form.get("assay", ""))
        qc_only = form.get("qc_only") == "1"
        resubmit = form.get("resubmit") == "1"
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return new_page(request, 400, chosen=name, error="The form expired. Try again.")
        try:
            text = files.read(check_name(name))
        except (AssayFileError, FileNotFoundError):
            return new_page(request, 400, error="Choose one of your assay files.")
        check = validate_text(text, settings.config())
        if not check.ok:
            problem = "This assay file has problems; fix them on the Assays page first."
            return new_page(request, 400, chosen=name, error=problem)
        plan = None
        if not qc_only:
            try:
                plan = plan_view(check.assay, check.cfg)
            except QpcrAssayCheckError as exc:
                return new_page(request, 400, chosen=name, error=str(exc))
            if not plan["searches"]:
                return new_page(request, 400, chosen=name, error=(
                    "Nothing to search: give the assay a target taxid or configure background "
                    "taxa."))  # fmt: skip
        return page(request, "run_plan.html", active="newrun", name=name, check=check,
                    plan=plan, qc_only=qc_only, resubmit=resubmit, digest=digest(text),
                    current=runner.current(), queued=runner.queued())  # fmt: skip

    @app.post("/runs")
    async def run_queue(request: Request, user: str = Depends(require_login)) -> Response:
        form = await request.form()
        name = str(form.get("assay", ""))
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return new_page(request, 400, chosen=name, error="The form expired. Plan again.")
        try:
            text = files.read(check_name(name))
        except (AssayFileError, FileNotFoundError):
            return new_page(request, 400, error="Choose one of your assay files.")
        if digest(text) != form.get("digest"):
            return new_page(request, 409, chosen=name, error=(
                "The assay file changed after the plan was shown. Plan again, so that what you "
                "confirm is what runs."))  # fmt: skip
        check = validate_text(text, settings.config())
        if not check.ok or check.assay is None:
            return new_page(request, 400, chosen=name, error="The assay file has problems.")
        job = store.create(
            Job(id=new_job_id(name), assay=name, assay_name=check.assay.assay_name,
                qc_only=form.get("qc_only") == "1", resubmit=form.get("resubmit") == "1"),
            text,
        )  # fmt: skip
        return RedirectResponse(f"/runs/{job.id}", status_code=303)

    @app.get("/runs", response_class=HTMLResponse)
    def run_list(request: Request, user: str = Depends(require_login)) -> Response:
        jobs = store.all()
        current = runner.current()
        prog = progress_of(read_tail(store.log_path(current.id), 400_000)) if current else None
        return page(request, "runs.html", active="run", current=current, progress=prog,
                    queued=runner.queued(), finished=[j for j in jobs if j.finished][:50],
                    stages=STAGES)  # fmt: skip

    @app.get("/runs/{job_id}", response_class=HTMLResponse)
    def run_detail(request: Request, job_id: str, user: str = Depends(require_login)) -> Response:
        job = _job(job_id)
        path = store.log_path(job.id)
        text = read_tail(path, 400_000)
        lines = text.splitlines()[-LOG_LINES_SHOWN:]
        try:
            offset = path.stat().st_size
        except OSError:
            offset = 0
        record_link = ""
        if job.record:
            rec = Path(job.record)
            record_link = f"/results/{rec.parent.name}/{rec.name}"
        return page(request, "run_detail.html", active="run", job=job, log_text="\n".join(lines),
                    record_link=record_link,
                    offset=offset, progress=progress_of(text), stages=STAGES,
                    queue_position=_position(job))  # fmt: skip

    def _position(job: Job) -> int | None:
        ids = [j.id for j in runner.queued()]
        return ids.index(job.id) + 1 if job.id in ids else None

    @app.get("/runs/{job_id}/status")
    def run_status(
        request: Request, job_id: str, offset: int = 0, user: str = Depends(require_login)
    ) -> JSONResponse:
        job = _job(job_id)
        path = store.log_path(job.id)
        text, next_offset = read_from(path, offset)
        prog = progress_of(read_tail(path, 400_000))
        return JSONResponse({
            "state": job.state, "text": text, "offset": next_offset, "stage": prog.stage,
            "detail": prog.detail, "percent": prog.percent, "message": job.message,
            "review_status": job.review_status, "queue_position": _position(job),
            "finished": job.finished,
        })  # fmt: skip

    @app.post("/runs/{job_id}/cancel")
    async def run_cancel(
        request: Request, job_id: str, user: str = Depends(require_login)
    ) -> Response:
        job = _job(job_id)
        form = await request.form()
        if csrf_ok(request, str(form.get("csrf", ""))):
            runner.cancel(job.id)
        return RedirectResponse(f"/runs/{job.id}", status_code=303)

    @app.post("/runs/{job_id}/again")
    async def run_again(
        request: Request, job_id: str, user: str = Depends(require_login)
    ) -> Response:
        old = _job(job_id)
        form = await request.form()
        if not csrf_ok(request, str(form.get("csrf", ""))) or not old.finished:
            return RedirectResponse(f"/runs/{old.id}", status_code=303)
        text = store.assay_path(old.id).read_text(encoding="utf-8")
        job = store.create(
            Job(id=new_job_id(old.assay), assay=old.assay, assay_name=old.assay_name,
                qc_only=old.qc_only, resubmit=form.get("resubmit") == "1"),
            text,
        )  # fmt: skip
        return RedirectResponse(f"/runs/{job.id}", status_code=303)


class _NoJob(Exception):
    """A run id that does not exist (or is not a run id)."""
