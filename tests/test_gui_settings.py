"""GUI phase G5: the Settings page (password, configuration, NCBI environment, storage)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from qpcr_assay_check.config import default_config_text  # noqa: E402
from qpcr_assay_check.gui.app import GuiSettings, create_app  # noqa: E402
from qpcr_assay_check.gui.auth import AuthStore  # noqa: E402
from qpcr_assay_check.gui.settings_routes import check_config_text, folder_size  # noqa: E402

PASSWORD = "correct horse battery"
NEW = "a much newer password"


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    AuthStore(tmp_path).set_password(PASSWORD)
    return tmp_path


def _client(work: Path, password: str = PASSWORD) -> TestClient:
    c = TestClient(create_app(GuiSettings(work_dir=work, start_runner=False)),
                   follow_redirects=False)  # fmt: skip
    c.post("/login", data={"password": password, "csrf": _csrf(c.get("/login").text)})
    return c


def _csrf(html: str) -> str:
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def test_page_reports_ncbi_environment_without_values(
    work: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NCBI_EMAIL", "someone@example.org")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    page = _client(work).get("/settings").text
    assert "someone@example.org" not in page
    assert "set in the environment" in page and "not set: slower request rate" in page
    assert "the packaged defaults are shown" in page


def test_password_change_ends_other_sessions_at_once(work: Path) -> None:
    me, other = _client(work), _client(work)
    assert other.get("/").status_code == 200
    token = _csrf(me.get("/settings").text)
    r = me.post("/settings/password", data={"csrf": token, "current": "wrong one!",
                                            "new": NEW, "again": NEW})  # fmt: skip
    assert r.status_code == 401
    r = me.post("/settings/password", data={"csrf": token, "current": PASSWORD,
                                            "new": NEW, "again": NEW + "x"})  # fmt: skip
    assert r.status_code == 400 and "differ" in r.text
    r = me.post("/settings/password", data={"csrf": token, "current": PASSWORD,
                                            "new": "short", "again": "short"})  # fmt: skip
    assert r.status_code == 400 and "10 characters" in r.text
    r = me.post("/settings/password", data={"csrf": token, "current": PASSWORD,
                                            "new": NEW, "again": NEW})  # fmt: skip
    assert r.status_code == 303
    assert me.get("/").status_code == 200  # this session stays
    assert other.get("/").status_code == 303  # every other one ends, without a restart
    assert AuthStore(work).verify(NEW) and not AuthStore(work).verify(PASSWORD)
    assert _client(work, NEW).get("/").status_code == 200


def test_password_set_from_the_command_line_ends_sessions(work: Path) -> None:
    c = _client(work)
    assert c.get("/").status_code == 200
    AuthStore(work).set_password(NEW)  # as `gui set-password` while the GUI runs
    assert c.get("/").status_code == 303


def test_config_is_checked_before_it_is_saved(work: Path) -> None:
    c = _client(work)
    token = _csrf(c.get("/settings").text)
    r = c.post("/settings/config", data={"csrf": token, "text": "reaction: [unclosed"})
    assert r.status_code == 400 and "Not saved" in r.text and "reaction: [unclosed" in r.text
    r = c.post(
        "/settings/config", data={"csrf": token, "text": "reaction:\n  annealing_temp_C: hot\n"}
    )
    assert r.status_code == 400 and "annealing_temp_C" in r.text
    assert not (work / "config.yaml").exists()
    good = "reaction:\n  annealing_temp_C: 58\n"
    assert c.post("/settings/config", data={"csrf": token, "text": good}).status_code == 303
    assert (work / "config.yaml").read_text() == good
    assert "58 °C" in c.get("/settings").text
    newer = "reaction:\n  annealing_temp_C: 59\n"
    c.post("/settings/config", data={"csrf": token, "text": newer})
    [kept] = list((work / "gui" / "history").iterdir())
    assert kept.read_text() == good
    assert c.post("/settings/config", data={"csrf": "x", "text": good}).status_code == 400
    assert (work / "config.yaml").read_text() == newer


def test_check_config_text() -> None:
    cfg, problem = check_config_text(default_config_text())
    assert cfg is not None and problem == ""
    assert check_config_text("")[0] is not None  # empty: the defaults
    assert "mapping" in check_config_text("- a\n- b\n")[1]


def test_storage_measures_and_stops(work: Path, tmp_path: Path) -> None:
    (work / "results" / "a").mkdir(parents=True)
    (work / "results" / "a" / "x.json").write_bytes(b"0" * 2048)
    size, files, complete = folder_size(work / "results", deadline=float("inf"))
    assert (size, files, complete) == (2048, 1, True)
    assert folder_size(work / "results", deadline=0.0)[2] is False
    frag = _client(work).get("/settings/storage")
    assert frag.status_code == 200 and "Evaluation records" in frag.text and "2 kB" in frag.text
