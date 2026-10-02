"""GUI phase G4: records per assay, the report in the page, downloads (no network)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

from qpcr_assay_check.cli import build_assay  # noqa: E402
from qpcr_assay_check.config import load_config  # noqa: E402
from qpcr_assay_check.gui.app import GuiSettings, create_app  # noqa: E402
from qpcr_assay_check.gui.auth import AuthStore  # noqa: E402
from qpcr_assay_check.pipeline import evaluate, write_outputs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
NEISSERIA = ROOT / "docs" / "examples" / "neisseria_gonorrhoeae_two_probes.yaml"
PASSWORD = "correct horse battery"


def _qc_record(work: Path) -> Path:
    assay = build_assay(NEISSERIA, {})
    cfg = load_config(None, assay.settings)
    return write_outputs(evaluate(assay, cfg, qc_only=True), work / "results", cfg)


@pytest.fixture()
def work(tmp_path: Path) -> Path:
    AuthStore(tmp_path).set_password(PASSWORD)
    return tmp_path


@pytest.fixture()
def client(work: Path) -> TestClient:
    c = TestClient(create_app(GuiSettings(work_dir=work, start_runner=False)),
                   follow_redirects=False)  # fmt: skip
    token = re.search(r'name="csrf" value="([^"]+)"', c.get("/login").text).group(1)
    c.post("/login", data={"password": PASSWORD, "csrf": token})
    return c


def test_results_pages_list_every_record(client: TestClient, work: Path) -> None:
    assert "No evaluation records yet" in client.get("/results").text
    first, second = _qc_record(work), _qc_record(work)
    slug = first.parent.name
    page = client.get("/results").text
    assert "Neisseria gonorrhoeae (two probes)" in page and "2 record(s)" in page
    runs = client.get(f"/results/{slug}").text
    assert first.name in runs and second.name in runs
    detail = client.get(f"/results/{slug}/{first.name}")
    assert detail.status_code == 200
    assert f'src="/records/{slug}/{first.name}/report.html"' in detail.text
    assert 'sandbox="allow-popups allow-popups-to-escape-sandbox"' in detail.text
    assert "results.xlsx" in detail.text and "Other runs of this assay" in detail.text
    assert f"/results/{slug}/" in client.get("/").text  # dashboard links to the record


def test_report_is_served_locked_down(client: TestClient, work: Path) -> None:
    rec = _qc_record(work)
    base = f"/records/{rec.parent.name}/{rec.name}"
    r = client.get(f"{base}/report.html")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    csp = r.headers["content-security-policy"]
    assert "script-src" not in csp and "default-src 'none'" in csp
    assert "frame-ancestors 'self'" in csp and r.headers["x-frame-options"] == "SAMEORIGIN"
    assert '<base target="_blank">' in r.text
    assert '<base target="_blank">' not in (rec / "report.html").read_text()  # file unchanged
    assert "does not replace experimental validation" in r.text
    # the GUI's own pages keep their stricter policy
    assert client.get("/results").headers["x-frame-options"] == "DENY"


def test_downloads(client: TestClient, work: Path) -> None:
    rec = _qc_record(work)
    base = f"/records/{rec.parent.name}/{rec.name}"
    for name in ("results.json", "results.xlsx", "report.html"):
        r = client.get(f"{base}/{name}?download=1")
        assert r.status_code == 200
        assert r.headers["content-disposition"].startswith("attachment")
        assert r.content == (rec / name).read_bytes()
    assert client.get(f"{base}/hits.tsv").status_code == 404  # a QC-only record has none


@pytest.mark.parametrize("path", [
    "/records/x/y/report.html",
    "/records/{slug}/{run}/job.json",
    "/records/{slug}/{run}/..%2F..%2F..%2Fgui%2Fauth.json",
    "/records/..%2F..%2Fgui/{run}/report.html",
    "/results/{slug}/nope",
    "/results/nope",
])  # fmt: skip
def test_unknown_or_unsafe_paths_are_not_found(client: TestClient, work: Path, path: str) -> None:
    rec = _qc_record(work)
    url = path.format(slug=rec.parent.name, run=rec.name)
    assert client.get(url).status_code == 404


def test_files_need_a_login(work: Path) -> None:
    rec = _qc_record(work)
    c = TestClient(create_app(GuiSettings(work_dir=work, start_runner=False)),
                   follow_redirects=False)  # fmt: skip
    r = c.get(f"/records/{rec.parent.name}/{rec.name}/results.json")
    assert r.status_code == 303 and r.headers["location"] == "/login"
