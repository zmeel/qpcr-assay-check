"""GUI phase G3: the run queue, the plan to confirm, live status, cancel (no network)."""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from qpcr_assay_check.gui.app import GuiSettings, create_app  # noqa: E402
from qpcr_assay_check.gui.auth import AuthStore  # noqa: E402
from qpcr_assay_check.gui.runs import (  # noqa: E402
    Job,
    JobStore,
    Runner,
    new_job_id,
    progress_of,
    read_from,
)

ROOT = Path(__file__).resolve().parent.parent
NEISSERIA = (ROOT / "docs" / "examples" / "neisseria_gonorrhoeae_two_probes.yaml").read_text()
PASSWORD = "correct horse battery"


def _fake(script: str):  # noqa: ANN202
    def command(job: Job, store: JobStore, config: Path | None) -> list[str]:
        return [sys.executable, "-c", script]

    return command


def _wait(runner: Runner, timeout: float = 20.0) -> None:
    """Tick until nothing runs and nothing is queued."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        runner.tick()
        if runner.proc is None and not runner.queued():
            return
        time.sleep(0.05)
    raise AssertionError("the queue did not drain")


def _job(store: JobStore, name: str = "ng.yaml", **kw: object) -> Job:
    return store.create(Job(id=new_job_id(name), assay=name, assay_name="NG", **kw), NEISSERIA)


def test_progress_is_read_from_the_log() -> None:
    log = "\n".join([
        "INFO qpcr_assay_check.oligo.qc: Oligo QC for 'NG': {}",
        "INFO qpcr_assay_check.ncbi.runner: Job exclusivity: served from cache",
        "INFO x: Partner scan next to 43 unpaired off-target primer sites",
        "INFO x: 2024: 41117 assemblies listed, 11517 already stored, 20000 to scan in this run",
        "INFO x:   12400 / 20000 assemblies scanned in this run",
    ])  # fmt: skip
    p = progress_of(log)
    assert p.stage == 3 and p.percent == 62 and "12,400 / 20,000" in p.detail
    assert progress_of(log + "\nRecord written to /x").stage == 4
    assert progress_of("").stage == -1 and progress_of("").percent is None


def test_job_ids_and_store(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    a, b = _job(store), _job(store)
    assert a.id != b.id and b.id.startswith(a.id)
    assert (store.assay_path(a.id)).read_text() == NEISSERIA
    assert store.get(a.id).assay_name == "NG"
    assert {j.id for j in store.all()} == {a.id, b.id}
    for bad in ("../x", "x", "20261002T000000Z-../../gui"):
        with pytest.raises(KeyError):
            store.get(bad)


def test_runner_runs_one_at_a_time_and_reads_the_result(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    script = ("import sys,time; print('Oligo QC for x', flush=True); time.sleep(0.3); "
              "print('Record written to /work/results/ng/run1'); sys.exit(10)")  # fmt: skip
    runner = Runner(store, command=_fake(script))
    first, second = _job(store), _job(store)
    runner.tick()
    assert store.get(first.id).state == "running" and store.get(second.id).state == "queued"
    assert runner.current().id == first.id
    _wait(runner)
    for j in (first, second):
        done = store.get(j.id)
        assert done.state == "done" and done.exit_code == 10 and done.review_status == "Review"
        assert done.record == "/work/results/ng/run1"
    assert store.get(first.id).ended <= store.get(second.id).started
    text = store.log_path(first.id).read_text()
    assert text.startswith("# ") and "Oligo QC for x" in text


def test_failure_and_cancel(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    runner = Runner(store, command=_fake("import sys; sys.exit(70)"))
    failed = _job(store)
    _wait(runner)
    assert store.get(failed.id).state == "failed"
    assert "NCBI" in store.get(failed.id).message
    runner = Runner(store, command=_fake("import time; time.sleep(60)"))
    running, waiting = _job(store), _job(store)
    runner.tick()
    runner.cancel(waiting.id)
    assert store.get(waiting.id).state == "cancelled"
    runner.cancel(running.id)
    _wait(runner)
    assert store.get(running.id).state == "cancelled"


def test_a_run_left_running_is_marked_interrupted(tmp_path: Path) -> None:
    store = JobStore(tmp_path)
    job = _job(store)
    job.state = "running"
    store.save(job)
    Runner(store)
    again = store.get(job.id)
    assert again.state == "interrupted" and "Start it again" in again.message


def test_read_from_ends_at_a_line(tmp_path: Path) -> None:
    path = tmp_path / "x.log"
    path.write_text("a\nbb\nccc\n")
    text, off = read_from(path, 0, limit=5)
    assert text == "a\nbb\n" and off == 5
    assert read_from(path, off) == ("ccc\n", 9)
    assert read_from(tmp_path / "missing.log", 3) == ("", 3)


# --- pages ---------------------------------------------------------------------------


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    AuthStore(tmp_path).set_password(PASSWORD)
    (tmp_path / "assays").mkdir()
    (tmp_path / "assays" / "ng.yaml").write_text(NEISSERIA)
    (tmp_path / "assays" / "broken.yaml").write_text("assay_name: x\n")
    return tmp_path


@pytest.fixture()
def client(work: Path) -> TestClient:
    c = TestClient(create_app(GuiSettings(work_dir=work, start_runner=False)),
                   follow_redirects=False)  # fmt: skip
    token = _csrf(c.get("/login").text)
    c.post("/login", data={"password": PASSWORD, "csrf": token})
    return c


def _csrf(html: str) -> str:
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    assert m
    return m.group(1)


def _digest(html: str) -> str:
    m = re.search(r'name="digest" value="([0-9a-f]{64})"', html)
    assert m
    return m.group(1)


def test_plan_shows_what_goes_to_ncbi_before_anything_runs(client: TestClient, work: Path) -> None:
    page = client.get("/runs/new").text
    assert "ng.yaml" in page and "broken.yaml" in page  # broken: listed as not offered
    assert 'value="broken.yaml"' not in page
    token = _csrf(page)
    plan = client.post("/runs/plan", data={"csrf": token, "assay": "ng.yaml"})
    assert plan.status_code == 200
    assert "GTTGAAACACCGCCCGG" in plan.text  # NG-F, as it would be sent
    assert "Planned searches" in plan.text and "Confirm and queue" in plan.text
    assert not (work / "gui" / "jobs").exists()  # nothing queued yet
    r = client.post("/runs/plan", data={"csrf": token, "assay": "broken.yaml"})
    assert r.status_code == 400 and "problems" in r.text


def test_confirm_queues_the_confirmed_file_only(client: TestClient, work: Path) -> None:
    token = _csrf(client.get("/runs/new").text)
    plan = client.post("/runs/plan", data={"csrf": token, "assay": "ng.yaml"}).text
    digest = _digest(plan)
    (work / "assays" / "ng.yaml").write_text(
        NEISSERIA.replace("Neisseria gonorrhoeae (two", "NG (two")
    )
    r = client.post("/runs", data={"csrf": token, "assay": "ng.yaml", "digest": digest})
    assert r.status_code == 409 and "Plan again" in r.text
    (work / "assays" / "ng.yaml").write_text(NEISSERIA)
    r = client.post("/runs", data={"csrf": token, "assay": "ng.yaml", "digest": digest})
    assert r.status_code == 303
    job_id = r.headers["location"].rsplit("/", 1)[1]
    job = json.loads((work / "gui" / "jobs" / job_id / "job.json").read_text())
    assert job["state"] == "queued" and not job["qc_only"]
    assert (work / "gui" / "jobs" / job_id / "assay.yaml").read_text() == NEISSERIA
    detail = client.get(f"/runs/{job_id}").text
    assert "Waiting in the queue: number 1" in detail and "Remove from queue" in detail
    status = client.get(f"/runs/{job_id}/status").json()
    assert status["state"] == "queued" and status["queue_position"] == 1
    assert "Neisseria" in client.get("/").text and "Queued next" in client.get("/").text
    client.post(f"/runs/{job_id}/cancel", data={"csrf": token})
    assert client.get(f"/runs/{job_id}/status").json()["state"] == "cancelled"
    r = client.post(f"/runs/{job_id}/again", data={"csrf": token})
    assert r.status_code == 303 and r.headers["location"] != f"/runs/{job_id}"


def test_a_real_qc_only_run_through_the_queue(client: TestClient, work: Path) -> None:
    token = _csrf(client.get("/runs/new").text)
    plan = client.post("/runs/plan", data={"csrf": token, "assay": "ng.yaml", "qc_only": "1"})
    assert "Queue the QC run" in plan.text and "Planned searches" not in plan.text
    r = client.post("/runs", data={"csrf": token, "assay": "ng.yaml", "qc_only": "1",
                                   "digest": _digest(plan.text)})  # fmt: skip
    job_id = r.headers["location"].rsplit("/", 1)[1]
    runner: Runner = client.app.state.runner
    _wait(runner, timeout=120)
    job = runner.store.get(job_id)
    assert job.state == "done", (job, runner.store.log_path(job_id).read_text())
    assert job.exit_code in (0, 10, 20) and job.record
    assert (Path(job.record) / "results.json").is_file()
    detail = client.get(f"/runs/{job_id}").text
    assert "Finished" in detail and "Start again" in detail
    assert "Neisseria" in client.get("/runs").text


def test_unknown_runs_are_not_found(client: TestClient) -> None:
    assert client.get("/runs/nope").status_code == 404
    assert client.get("/runs/20261002T000000Z-x/status").status_code == 404
