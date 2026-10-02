"""Runs started from the GUI (phase G3): a queue, one run at a time.

Each run is the command line itself, ``qpcr-assay-check run <assay> -o <work>/results --yes``,
in its own process, so a GUI run and a run from ``scripts/run_assay.sh`` behave the same and
write the same records. ``--yes`` stands for the confirmation given in the browser, after the
search plan was shown. Only one run goes at a time, so NCBI never sees two of this tool's runs
in parallel from the GUI (runs started outside the GUI are not known here).

A job is a folder ``<work>/gui/jobs/<id>/`` with ``job.json`` and ``assay.yaml``, a copy of the
assay file as confirmed, so a later edit does not change a queued run. The log goes to
``<work>/runs/<id>.log``, next to the logs of ``scripts/run_assay.sh``. Jobs survive a restart
of the GUI; a run that was going when the GUI stopped is marked interrupted and can be started
again (stored genomes and finished searches are reused, unfinished searches resume).
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

log = logging.getLogger(__name__)

JOB_ID = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9-]{1,60}$")
STATES = ("queued", "running", "done", "failed", "cancelled", "interrupted")
FINISHED = ("done", "failed", "cancelled", "interrupted")
REVIEW_EXIT_CODES = {0: "No flags", 10: "Review", 20: "Exceeds limit", 30: "Incomplete"}
TERM_AFTER_S = 30.0  # after Ctrl-C (SIGINT), then SIGTERM
KILL_AFTER_S = 60.0  # then SIGKILL


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _created() -> str:
    """Queue order: microseconds, so jobs queued in the same second keep their order."""
    return datetime.now(UTC).isoformat(timespec="microseconds")


@dataclass
class Job:
    """One run: what was confirmed, and what became of it."""

    id: str
    assay: str  # the assay file name in <work>/assays at confirmation
    assay_name: str
    qc_only: bool = False
    resubmit: bool = False
    state: str = "queued"
    created: str = field(default_factory=_created)
    started: str = ""
    ended: str = ""
    pid: int | None = None
    exit_code: int | None = None
    record: str = ""  # the record folder the run wrote (absolute, as the CLI printed it)
    message: str = ""
    cancel_requested: bool = False

    @property
    def finished(self) -> bool:
        return self.state in FINISHED

    @property
    def review_status(self) -> str:
        return REVIEW_EXIT_CODES.get(self.exit_code, "") if self.exit_code is not None else ""


def new_job_id(assay_file: str) -> str:
    stem = re.sub(r"[^a-z0-9-]+", "-", Path(assay_file).stem.lower()).strip("-")[:40] or "run"
    return f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{stem}"


class JobStore:
    """``<work>/gui/jobs/<id>/job.json`` and its assay copy."""

    def __init__(self, work_dir: Path) -> None:
        self.work = Path(work_dir)
        self.dir = self.work / "gui" / "jobs"
        self.logs = self.work / "runs"
        self._lock = threading.Lock()

    def folder(self, job_id: str) -> Path:
        if not JOB_ID.match(job_id):
            raise KeyError(job_id)
        return self.dir / job_id

    def log_path(self, job_id: str) -> Path:
        self.folder(job_id)  # checks the id
        return self.logs / f"{job_id}.log"

    def assay_path(self, job_id: str) -> Path:
        return self.folder(job_id) / "assay.yaml"

    def create(self, job: Job, assay_text: str) -> Job:
        with self._lock:
            base, n = job.id, 2
            while self.folder(job.id).exists():
                job.id = f"{base}-{n}"
                n += 1
            folder = self.folder(job.id)
            folder.mkdir(parents=True)
            (folder / "assay.yaml").write_text(assay_text, encoding="utf-8")
            self._write(job)
        log.info("GUI: run %s queued (%s)", job.id, job.assay)
        return job

    def _write(self, job: Job) -> None:
        path = self.folder(job.id) / "job.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(job), indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def save(self, job: Job) -> None:
        with self._lock:
            self._write(job)

    def get(self, job_id: str) -> Job:
        path = self.folder(job_id) / "job.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise KeyError(job_id) from exc
        known = {k: v for k, v in data.items() if k in Job.__dataclass_fields__}
        return Job(**known)

    def all(self) -> list[Job]:
        if not self.dir.is_dir():
            return []
        out = []
        for folder in self.dir.iterdir():
            if folder.is_dir() and JOB_ID.match(folder.name):
                try:
                    out.append(self.get(folder.name))
                except (KeyError, ValueError, TypeError):
                    log.warning("GUI: unreadable job %s", folder)
        return sorted(out, key=lambda j: j.created, reverse=True)


def cli_command(job: Job, store: JobStore, config: Path | None) -> list[str]:
    """The command line a job runs: exactly what scripts/run_assay.sh runs."""
    cmd = [sys.executable, "-m", "qpcr_assay_check", "run", str(store.assay_path(job.id)),
           "-o", str(store.work / "results"), "--yes", "-v"]  # fmt: skip
    if config:
        cmd += ["-c", str(config)]
    if job.qc_only:
        cmd.append("--qc-only")
    if job.resubmit:
        cmd.append("--resubmit")
    return cmd


_RECORD = re.compile(r"^Record written to (.+)$", re.MULTILINE)


class Runner:
    """Starts queued jobs one at a time and follows the running one."""

    def __init__(
        self,
        store: JobStore,
        config: Callable[[], Path | None] = lambda: None,
        command: Callable[[Job, JobStore, Path | None], list[str]] = cli_command,
    ) -> None:
        self.store = store
        self.config = config
        self.command = command
        self.proc: subprocess.Popen[bytes] | None = None
        self.job_id: str | None = None
        self._term_sent: float | None = None
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._recover()

    def _recover(self) -> None:
        """Jobs left 'running' by an earlier GUI process cannot be followed any more."""
        for job in self.store.all():
            if job.state == "running":
                job.state, job.ended = "interrupted", _now()
                job.message = (
                    "The GUI stopped while this run was going. Start it again to continue: "
                    "stored genomes and finished searches are reused, unfinished ones resume."
                )
                self.store.save(job)

    # --- the queue ---------------------------------------------------------------------

    def current(self) -> Job | None:
        with self._lock:
            return self.store.get(self.job_id) if self.job_id else None

    def queued(self) -> list[Job]:
        return sorted(
            (j for j in self.store.all() if j.state == "queued"), key=lambda j: (j.created, j.id)
        )

    def cancel(self, job_id: str) -> Job:
        with self._lock:
            job = self.store.get(job_id)
            if job.state == "queued":
                job.state, job.ended, job.message = (
                    "cancelled",
                    _now(),
                    "Cancelled before it started.",
                )
                self.store.save(job)
            elif job.state == "running" and job_id == self.job_id and self.proc is not None:
                job.cancel_requested = True
                self.store.save(job)
                # Ctrl-C first, as in a terminal: the run stops between steps and what it
                # stored stays usable for the next run
                self._signal(signal.SIGINT)
                self._term_sent = time.monotonic()
                log.info("GUI: run %s: cancel requested", job_id)
            return job

    def _signal(self, sig: int) -> None:
        if self.proc is None:
            return
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(self.proc.pid, sig)

    def tick(self) -> None:
        """Follow the running job; start the next one when none runs."""
        with self._lock:
            if self.proc is not None:
                code = self.proc.poll()
                if code is None:
                    if self._term_sent:
                        waited = time.monotonic() - self._term_sent
                        if waited > KILL_AFTER_S:
                            self._signal(signal.SIGKILL)
                        elif waited > TERM_AFTER_S:
                            self._signal(signal.SIGTERM)
                    return
                self._finish(code)
            nxt = self.queued()
            if nxt:
                self._start(nxt[0])

    def _start(self, job: Job) -> None:
        log_path = self.store.log_path(job.id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = self.command(job, self.store, self.config())
        env = dict(os.environ, PYTHONUNBUFFERED="1")
        with open(log_path, "ab") as out:
            out.write(f"# {_now()} started from the GUI: {' '.join(cmd[2:])}\n".encode())
            out.flush()
            try:
                self.proc = subprocess.Popen(
                    cmd, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    cwd=self.store.work, env=env, start_new_session=True,
                )  # fmt: skip
            except OSError as exc:
                job.state, job.ended, job.message = "failed", _now(), f"Could not start: {exc}"
                self.store.save(job)
                self.proc = None
                return
        self.job_id, self._term_sent = job.id, None
        job.state, job.started, job.pid = "running", _now(), self.proc.pid
        self.store.save(job)
        log.info("GUI: run %s started (pid %d)", job.id, self.proc.pid)

    def _finish(self, code: int) -> None:
        job = self.store.get(self.job_id or "")
        text = read_tail(self.store.log_path(job.id), 200_000)
        found = _RECORD.findall(text)
        job.exit_code, job.ended, job.pid = code, _now(), None
        job.record = found[-1].strip() if found else ""
        if job.cancel_requested:
            job.state, job.message = "cancelled", "Cancelled while running."
        elif code in REVIEW_EXIT_CODES:
            job.state, job.message = "done", ""
        else:
            job.state = "failed"
            job.message = {
                64: "The assay or configuration was refused (see the log).",
                70: "NCBI could not be reached or refused a request (see the log). Starting "
                    "the run again resumes it.",
            }.get(code, f"The run ended with exit code {code} (see the log).")  # fmt: skip
        self.store.save(job)
        log.info("GUI: run %s ended: %s (exit %s)", job.id, job.state, code)
        self.proc, self.job_id, self._term_sent = None, None, None

    # --- background thread ---------------------------------------------------------------

    def start(self, interval: float = 2.0) -> None:
        def loop() -> None:
            while not self._stop.wait(interval):
                try:
                    self.tick()
                except Exception:  # keep following the queue whatever one job does
                    log.exception("GUI: run queue")

        self._thread = threading.Thread(target=loop, name="qac-runner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop following (the GUI is shutting down); a running job is left running."""
        self._stop.set()


def read_tail(path: Path, limit: int) -> str:
    """The last ``limit`` bytes of a log (from a line start), as text."""
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            fh.seek(max(0, size - limit))
            data = fh.read()
    except OSError:
        return ""
    if size > limit:
        data = data.split(b"\n", 1)[-1]
    return data.decode("utf-8", errors="replace")


def read_from(path: Path, offset: int, limit: int = 64_000) -> tuple[str, int]:
    """Log text from ``offset`` (at most ``limit`` bytes, ending at a line end) and the next
    offset."""
    try:
        with open(path, "rb") as fh:
            fh.seek(max(0, offset))
            data = fh.read(limit)
    except OSError:
        return "", offset
    if len(data) == limit and b"\n" in data:
        data = data[: data.rindex(b"\n") + 1]
    return data.decode("utf-8", errors="replace"), offset + len(data)


# --- what the log says about progress ----------------------------------------------------

STAGES = ("Oligo QC", "Specificity searches", "Re-alignment and partner scan",
          "Genome listing and scan", "Report")  # fmt: skip
_STAGE_MARKS = [
    (0, re.compile(r"Oligo QC for")),
    (1, re.compile(r"Job .+: (served from cache|submitted|resuming|RID .+ is )")),
    (2, re.compile(r"Re-aligning \d+ partial hits|Partner scan next to|partner scan: \d+")),
    (3, re.compile(r"assemblies listed|Variant analysis|records? listed")),
    (4, re.compile(r"Wrote evaluation record|Record written to")),
]
_SCANNED = re.compile(r"(\d+) / (\d+) assemblies scanned in this run")
_YEAR = re.compile(r"^.*?(\d{4}): (\d+) assemblies listed, (\d+) already stored, (\d+) to scan",
                   re.MULTILINE)  # fmt: skip


@dataclass
class Progress:
    """The stage a run has reached and its latest count, read from the log."""

    stage: int = -1
    detail: str = ""
    done: int | None = None
    total: int | None = None

    @property
    def percent(self) -> int | None:
        if self.done is None or not self.total:
            return None
        return max(0, min(100, round(100 * self.done / self.total)))


def progress_of(text: str) -> Progress:
    p = Progress()
    for line in text.splitlines():
        for stage, pattern in _STAGE_MARKS:
            if pattern.search(line) and stage >= p.stage:
                p.stage = stage
        m = _SCANNED.search(line)
        if m:
            p.done, p.total = int(m.group(1)), int(m.group(2))
            p.detail = f"{p.done:,} / {p.total:,} genomes of this year's batch"
        y = _YEAR.search(line)
        if y:
            p.detail = (f"{y.group(1)}: {int(y.group(2)):,} listed, {int(y.group(3)):,} stored, "
                        f"{int(y.group(4)):,} to scan")  # fmt: skip
            p.done, p.total = 0, int(y.group(4)) or None
    return p
