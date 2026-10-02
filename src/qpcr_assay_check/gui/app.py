"""The FastAPI application: login, logout, dashboard.

Sessions are signed cookies (Starlette's SessionMiddleware, itsdangerous) that scripts cannot
read and browsers do not send from other sites; they end after ``idle_hours`` without a request.
Every form carries a per-session token that is checked on POST. Pages are rendered on the server
from the package's templates; CSS, fonts and the small script ship in the package, so the GUI
makes no requests outside itself.
"""

from __future__ import annotations

import hmac
import logging
import secrets
import time
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from .. import __version__
from .assay_routes import register_assay_routes
from .auth import AuthStore, LoginThrottle
from .records import RecordIndex

log = logging.getLogger(__name__)

SESSION_COOKIE = "qac_session"
USER = "admin"  # one user: the session only records that the password was given
_CSP = (
    "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
    "font-src 'self'; frame-ancestors 'none'; form-action 'self'; base-uri 'none'"
)
VALIDATION_NOTE = (
    "In silico analysis does not replace experimental validation; the laboratory verifies "
    "this software within its own quality system."
)


@dataclass
class GuiSettings:
    """How the GUI runs. ``work_dir`` holds ``results/``, ``runs/`` and ``gui/``."""

    work_dir: Path
    idle_hours: float = 8.0
    secure_cookie: bool = False  # True when served over HTTPS (reverse proxy)
    examples_dir: Path | None = None  # read-only assay files offered for copying
    config_path: Path | None = None  # default: <work>/config.yaml when it exists

    def config(self) -> Path | None:
        """The configuration file runs and validation use (as scripts/run_assay.sh)."""
        if self.config_path:
            return self.config_path
        default = Path(self.work_dir) / "config.yaml"
        return default if default.is_file() else None


class LoginRequired(Exception):
    """Raised by :func:`_require_login`; answered with a redirect to the login page."""

    def __init__(self, expired: bool = False) -> None:
        self.expired = expired


def _package_dir(name: str) -> Path:
    return Path(str(resources.files("qpcr_assay_check.gui") / name))


def csrf_token(request: Request) -> str:
    """The session's form token (made on first use)."""
    token = request.session.get("csrf")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf"] = token
    return str(token)


def _csrf_ok(request: Request, token: str) -> bool:
    expected = request.session.get("csrf")
    return bool(expected) and hmac.compare_digest(str(expected), token)


def create_app(settings: GuiSettings) -> FastAPI:
    """The GUI for ``settings.work_dir``; refuses to start without a password."""
    store = AuthStore(settings.work_dir)
    if not store.is_set:
        raise RuntimeError("no GUI password set: run 'qpcr-assay-check gui set-password' first")
    idle_seconds = int(settings.idle_hours * 3600)
    throttle = LoginThrottle()
    records = RecordIndex(Path(settings.work_dir) / "results")
    templates = Jinja2Templates(directory=str(_package_dir("templates")))
    templates.env.globals.update(version=__version__, validation_note=VALIDATION_NOTE)

    app = FastAPI(title="qpcr-assay-check", docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(
        SessionMiddleware,
        secret_key=store.secret_key,
        session_cookie=SESSION_COOKIE,
        max_age=idle_seconds,
        same_site="strict",
        https_only=settings.secure_cookie,
    )
    app.mount("/static", StaticFiles(directory=str(_package_dir("static"))), name="static")

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = _CSP
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if not request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(LoginRequired)
    async def to_login(request: Request, exc: LoginRequired) -> RedirectResponse:
        return RedirectResponse("/login?expired=1" if exc.expired else "/login", status_code=303)

    def _require_login(request: Request) -> str:
        if request.session.get("user") != USER:
            raise LoginRequired()
        now = time.time()
        if now - float(request.session.get("last_seen", 0)) > idle_seconds:
            request.session.clear()
            raise LoginRequired(expired=True)
        request.session["last_seen"] = now
        return USER

    def _page(request: Request, template: str, status_code: int = 200, **context: Any) -> Response:
        context.setdefault("csrf", csrf_token(request))
        return templates.TemplateResponse(request, template, context, status_code=status_code)

    @app.get("/healthz", include_in_schema=False)
    def healthz() -> JSONResponse:
        return JSONResponse({"status": "ok"})

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, expired: int = 0) -> Response:
        if request.session.get("user") == USER:
            return RedirectResponse("/", status_code=303)
        message = "Signed out after inactivity. Sign in again." if expired else ""
        return _page(request, "login.html", message=message, idle_hours=settings.idle_hours)

    @app.post("/login", response_class=HTMLResponse)
    def login(
        request: Request,
        password: Annotated[str, Form()] = "",
        csrf: Annotated[str, Form()] = "",
    ) -> Response:
        client = request.client.host if request.client else "unknown"
        page = {"idle_hours": settings.idle_hours}
        if not _csrf_ok(request, csrf):
            return _page(request, "login.html", 400, error="The form expired. Try again.", **page)
        now = time.time()
        wait = throttle.wait(client, now)
        if wait > 0:
            return _page(
                request, "login.html", 429,
                error=f"Too many failed attempts. Try again in {int(wait) + 1} seconds.", **page,
            )  # fmt: skip
        if not store.verify(password):
            throttle.failed(client, now)
            return _page(request, "login.html", 401, error="Wrong password.", **page)
        throttle.succeeded(client)
        request.session.clear()
        request.session.update(user=USER, last_seen=now, csrf=secrets.token_urlsafe(32))
        log.info("GUI: signed in from %s", client)
        return RedirectResponse("/", status_code=303)

    @app.post("/logout")
    def logout(request: Request, csrf: Annotated[str, Form()] = "") -> Response:
        if _csrf_ok(request, csrf):
            request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request, user: str = Depends(_require_login)) -> Response:
        every = records.all()
        return _page(
            request, "dashboard.html", active="dashboard",
            latest=records.latest_per_assay(), recent=every[:20], n_records=len(every),
            results_dir=records.results_dir,
        )  # fmt: skip

    register_assay_routes(
        app, settings=settings, page=_page, require_login=_require_login, csrf_ok=_csrf_ok
    )
    return app
