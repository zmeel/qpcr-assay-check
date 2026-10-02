"""Routes of the Settings page (phase G5): the password, the configuration file, what the NCBI
environment provides, and how much room the work folder takes.

The configuration editor edits the file runs and validation use (``--config``, by default
``<work>/config.yaml``). It is checked exactly as a run loads it (the packaged defaults, then
this file) before it is saved; every save keeps the previous version in ``<work>/gui/history/``.
The NCBI email and API key are only reported as set or not set: they come from the environment
and the GUI neither shows nor stores them.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from ..config import default_config_text, load_config
from ..errors import QpcrAssayCheckError
from .auth import AuthStore, LoginThrottle, check_new_password
from .records import RecordIndex
from .runs import Runner

if TYPE_CHECKING:
    from .app import GuiSettings

SIZE_TIME_LIMIT_S = 5.0


def folder_size(path: Path, deadline: float) -> tuple[int, int, bool]:
    """Bytes and files under ``path``; stops at ``deadline`` (monotonic) and says so."""
    total = files = 0
    stack = [path]
    while stack:
        if time.monotonic() > deadline:
            return total, files, False
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    stack.append(Path(e.path))
                elif e.is_file(follow_symlinks=False):
                    total += e.stat(follow_symlinks=False).st_size
                    files += 1
            except OSError:
                continue
    return total, files, True


def check_config_text(text: str) -> tuple[Any, str]:
    """The configuration a run would load from this text (defaults, then the text), or the
    problem."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return None, f"not valid YAML: {exc}"
    if data is not None and not isinstance(data, dict):
        return None, "the file must be a YAML mapping (section: settings)"
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as fh:
        fh.write(text)
        tmp = Path(fh.name)
    try:
        return load_config(tmp), ""
    except QpcrAssayCheckError as exc:
        return None, str(exc).replace(str(tmp), "this file")
    finally:
        tmp.unlink(missing_ok=True)


def register_settings_routes(
    app: FastAPI,
    *,
    settings: GuiSettings,
    store: AuthStore,
    throttle: LoginThrottle,
    records: RecordIndex,
    runner: Runner,
    page: Callable[..., Response],
    require_login: Callable[[Request], str],
    csrf_ok: Callable[[Request, str], bool],
) -> None:
    """Add the Settings page to ``app``."""
    work = Path(settings.work_dir)

    def config_path() -> Path:
        return Path(settings.config_path) if settings.config_path else work / "config.yaml"

    def settings_page(request: Request, status_code: int = 200, **ctx: Any) -> Response:
        path = config_path()
        exists = path.is_file()
        text = ctx.pop("config_text", None)
        if text is None:
            text = path.read_text(encoding="utf-8") if exists else default_config_text()
        cfg, problem = check_config_text(text)
        ctx.setdefault("config_error", problem)
        return page(
            request, "settings.html", status_code, active="settings", config_file=path,
            config_exists=exists, config_text=text, cfg=cfg, idle_hours=settings.idle_hours,
            secure_cookie=settings.secure_cookie,
            ncbi_email=bool(os.environ.get("NCBI_EMAIL")),
            ncbi_key=bool(os.environ.get("NCBI_API_KEY")),
            work_dir=work, **ctx,
        )  # fmt: skip

    @app.get("/settings", response_class=HTMLResponse)
    def settings_view(
        request: Request, saved: str = "", user: str = Depends(require_login)
    ) -> Response:
        return settings_page(request, saved=saved)

    @app.get("/settings/storage", response_class=HTMLResponse)
    def storage(request: Request, user: str = Depends(require_login)) -> Response:
        cfg, _ = check_config_text(
            config_path().read_text(encoding="utf-8") if config_path().is_file() else ""
        )
        from ..ncbi.cache import default_cache_dir

        cache = Path(cfg.ncbi.cache_dir) if cfg and cfg.ncbi.cache_dir else default_cache_dir()
        deadline = time.monotonic() + SIZE_TIME_LIMIT_S
        rows = []
        for label, path in (
            ("NCBI cache and genome stores", cache),
            ("Evaluation records", records.results_dir),
            ("Run logs", runner.store.logs),
            ("Assay files", work / "assays"),
        ):
            size, files, complete = folder_size(path, deadline) if path.exists() else (0, 0, True)
            rows.append({"label": label, "path": path, "size": size, "files": files,
                         "complete": complete, "exists": path.exists()})  # fmt: skip
        try:
            free = shutil.disk_usage(work).free
        except OSError:
            free = None
        return page(request, "_storage.html", rows=rows, free=free)

    @app.post("/settings/password")
    async def change_password(request: Request, user: str = Depends(require_login)) -> Response:
        form = await request.form()
        if not csrf_ok(request, str(form.get("csrf", ""))):
            return settings_page(request, 400, password_error="The form expired. Try again.")
        client = request.client.host if request.client else "unknown"
        now = time.time()
        wait = throttle.wait(client, now)
        if wait > 0:
            return settings_page(request, 429, password_error=(
                f"Too many wrong attempts. Try again in {int(wait) + 1} seconds."))  # fmt: skip
        if not store.verify(str(form.get("current", ""))):
            throttle.failed(client, now)
            return settings_page(request, 401, password_error="The current password is wrong.")
        throttle.succeeded(client)
        new, again = str(form.get("new", "")), str(form.get("again", ""))
        if new != again:
            return settings_page(request, 400, password_error="The two new passwords differ.")
        problem = check_new_password(new)
        if problem:
            return settings_page(request, 400, password_error=f"Not changed: {problem}.")
        store.set_password(new)
        request.session["gen"] = store.generation  # this session stays; every other one ends
        return RedirectResponse("/settings?saved=password", status_code=303)

    @app.post("/settings/config")
    async def save_config(request: Request, user: str = Depends(require_login)) -> Response:
        form = await request.form()
        text = str(form.get("text", "")).replace("\r\n", "\n")
        if not csrf_ok(request, str(form.get("csrf", ""))):
            expired = "The form expired; your text is below. Save again."
            return settings_page(request, 400, config_text=text, config_error=expired)
        cfg, problem = check_config_text(text)
        if cfg is None:
            return settings_page(request, 400, config_text=text,
                                 config_error=f"Not saved: {problem}")  # fmt: skip
        path = config_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            if path.read_text(encoding="utf-8") == text:
                return RedirectResponse("/settings?saved=config", status_code=303)
            keep = work / "gui" / "history"
            keep.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
            shutil.copy2(path, keep / f"{stamp}-{path.name}")
        tmp = path.with_name(f".{path.name}.tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        return RedirectResponse("/settings?saved=config", status_code=303)
