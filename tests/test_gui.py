"""GUI phase G1: password store, login brake, sessions, dashboard (no network)."""

from __future__ import annotations

import json
import re
import stat
from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402
from typer.testing import CliRunner  # noqa: E402

from qpcr_assay_check.cli import app as cli_app  # noqa: E402
from qpcr_assay_check.gui import app as gui_app_module  # noqa: E402
from qpcr_assay_check.gui.app import GuiSettings, create_app  # noqa: E402
from qpcr_assay_check.gui.auth import (  # noqa: E402
    AuthStore,
    LoginThrottle,
    check_new_password,
    hash_password,
    verify_password,
)
from qpcr_assay_check.gui.records import RecordIndex  # noqa: E402

PASSWORD = "correct horse battery"


def test_hash_round_trip_and_salt() -> None:
    a, b = hash_password(PASSWORD), hash_password(PASSWORD)
    assert a != b  # fresh salt each time
    assert a.startswith("scrypt$")
    assert verify_password(PASSWORD, a)
    assert not verify_password("wrong password", a)
    assert not verify_password(PASSWORD, "not-a-hash")
    assert not verify_password(PASSWORD, "bcrypt$1$2$3$4$5")


def test_new_password_rules() -> None:
    assert check_new_password("short") is not None
    assert check_new_password(" leading space ok?") is not None
    assert check_new_password(PASSWORD) is None


def test_store_file_is_private_and_reset_changes_the_key(tmp_path: Path) -> None:
    store = AuthStore(tmp_path)
    assert not store.is_set
    store.set_password(PASSWORD)
    assert store.is_set and store.verify(PASSWORD) and not store.verify("other password")
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    key = store.secret_key
    store.set_password(PASSWORD + "!")
    assert store.secret_key != key  # every session ends
    with pytest.raises(ValueError):
        store.set_password("short")


def test_throttle_waits_after_the_free_attempts() -> None:
    t = LoginThrottle(free=3, max_wait=10)
    for _ in range(3):
        assert t.wait("c", 100.0) == 0
        t.failed("c", 100.0)
    assert t.wait("c", 100.0) == pytest.approx(2.0)
    assert t.wait("other", 100.0) == 0
    t.failed("c", 100.0)
    assert t.wait("c", 100.0) == pytest.approx(4.0)
    for _ in range(10):
        t.failed("c", 100.0)
    assert t.wait("c", 100.0) == pytest.approx(10.0)  # capped
    t.succeeded("c")
    assert t.wait("c", 100.0) == 0


def test_app_refuses_to_start_without_a_password(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="set-password"):
        create_app(GuiSettings(work_dir=tmp_path))


def _record(work: Path, slug: str, run_id: str, when: str, verdict: str = "WARN") -> Path:
    run_dir = work / "results" / slug / run_id
    run_dir.mkdir(parents=True)
    data = {
        "run_id": run_id,
        "generated_at": when,
        "mode": "full",
        "tool": {"version": "2.0.0"},
        "assay": {"assay_name": f"Assay {slug}"},
        "overall": {"verdict": verdict},
        "sections": [
            {"key": "oligo_qc", "title": "Oligo QC", "state": "evaluated", "verdict": "PASS"},
            {"key": "structure", "title": "Structure", "state": "skipped", "verdict": None},
        ],
        "inclusivity": {"rationale": ["Whole fragment: 91.6% detectable."]},
    }
    path = run_dir / "results.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    AuthStore(tmp_path).set_password(PASSWORD)
    return tmp_path


@pytest.fixture()
def client(work: Path) -> TestClient:
    return TestClient(create_app(GuiSettings(work_dir=work)), follow_redirects=False)


def _csrf(html: str) -> str:
    m = re.search(r'name="csrf" value="([^"]+)"', html)
    assert m, "no form token in the page"
    return m.group(1)


def _login(client: TestClient, password: str = PASSWORD) -> object:
    token = _csrf(client.get("/login").text)
    return client.post("/login", data={"password": password, "csrf": token})


def test_pages_need_a_login(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/healthz").json() == {"status": "ok"}


def test_login_page_headers_and_no_external_requests(client: TestClient) -> None:
    r = client.get("/login")
    assert r.status_code == 200
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert "http://" not in r.text and "https://" not in r.text
    assert "does not replace experimental validation" in r.text
    css = client.get("/static/app.css")
    assert css.status_code == 200 and "https://" not in css.text
    assert client.get("/static/fonts/ibm-plex-sans-latin-400-normal.woff2").status_code == 200


def test_login_without_the_form_token_is_refused(client: TestClient) -> None:
    client.get("/login")
    r = client.post("/login", data={"password": PASSWORD, "csrf": "forged"})
    assert r.status_code == 400
    assert client.get("/").status_code == 303


def test_wrong_password_then_brake(client: TestClient) -> None:
    for _ in range(3):
        assert _login(client, "wrong password!").status_code == 401
    r = _login(client, PASSWORD)  # even the right password waits now
    assert r.status_code == 429
    assert "Too many failed attempts" in r.text


def test_login_dashboard_and_logout(client: TestClient, work: Path) -> None:
    r = _login(client)
    assert r.status_code == 303 and r.headers["location"] == "/"
    page = client.get("/")
    assert page.status_code == 200
    assert "No evaluation records yet" in page.text
    assert client.get("/login").status_code == 303  # already signed in
    r = client.post("/logout", data={"csrf": _csrf(page.text)})
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert client.get("/").status_code == 303


def test_logout_needs_the_form_token(client: TestClient) -> None:
    _login(client)
    client.post("/logout", data={"csrf": "forged"})
    assert client.get("/").status_code == 200


def test_session_ends_after_the_idle_time(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _login(client)
    assert client.get("/").status_code == 200
    real = gui_app_module.time.time

    class Later:
        @staticmethod
        def time() -> float:
            return real() + 8 * 3600 + 5

    monkeypatch.setattr(gui_app_module, "time", Later)
    r = client.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/login?expired=1"
    monkeypatch.undo()
    assert client.get("/").status_code == 303  # the session was cleared
    assert "Signed out after inactivity" in client.get("/login?expired=1").text


def test_a_new_password_ends_open_sessions(work: Path) -> None:
    c = TestClient(create_app(GuiSettings(work_dir=work)), follow_redirects=False)
    _login(c)
    assert c.get("/").status_code == 200
    AuthStore(work).set_password("a brand new password")
    restarted = TestClient(create_app(GuiSettings(work_dir=work)), follow_redirects=False)
    restarted.cookies.update(c.cookies)
    assert restarted.get("/").status_code == 303


def test_dashboard_lists_the_latest_record_per_assay(client: TestClient, work: Path) -> None:
    _record(work, "assay-a", "run-1", "2026-09-30T10:00:00Z", "INCOMPLETE")
    _record(work, "assay-a", "run-2", "2026-10-01T10:00:00Z", "WARN")
    _record(work, "assay-b", "run-3", "2026-09-29T10:00:00Z", "PASS")
    bad = work / "results" / "assay-c" / "run-4"
    bad.mkdir(parents=True)
    (bad / "results.json").write_text("{not json", encoding="utf-8")
    _login(client)
    text = client.get("/").text
    assert "Assay assay-a" in text and "Assay assay-b" in text
    assert "Last run 2026-10-01" in text and "Last run 2026-09-30" not in text
    assert "chip-review" in text and "chip-ok" in text
    assert "Structure" not in text  # skipped sections are not shown
    assert "91.6% detectable" in text
    assert "(3 of 3)" in text


def test_record_index_rereads_changed_files(tmp_path: Path) -> None:
    path = _record(tmp_path, "a", "r1", "2026-10-01T00:00:00Z", "WARN")
    index = RecordIndex(tmp_path / "results")
    assert index.all()[0].status == "Review"
    data = json.loads(path.read_text())
    data["overall"]["verdict"] = "FAIL"
    path.write_text(json.dumps(data))
    import os

    os.utime(path, (1, 1))
    assert index.all()[0].status == "Exceeds limit"
    path.unlink()
    assert index.all() == []


def test_cli_set_password(tmp_path: Path) -> None:
    runner = CliRunner()
    r = runner.invoke(cli_app, ["gui", "set-password", "--work", str(tmp_path)],
                      input=f"{PASSWORD}\n{PASSWORD}\n")  # fmt: skip
    assert r.exit_code == 0, r.output
    assert AuthStore(tmp_path).verify(PASSWORD)
    r = runner.invoke(cli_app, ["gui", "set-password", "--work", str(tmp_path)],
                      input="short\nshort\n")  # fmt: skip
    assert r.exit_code != 0
    assert AuthStore(tmp_path).verify(PASSWORD)


def test_cli_serve_refuses_without_password(tmp_path: Path) -> None:
    r = CliRunner().invoke(cli_app, ["gui", "serve", "--work", str(tmp_path)])
    assert r.exit_code != 0
    assert "set-password" in r.output
