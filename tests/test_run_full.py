"""The full `run` command end to end, against the constructed NCBI world."""

import json
import re
import time

import pytest
from openpyxl import load_workbook
from typer.testing import CliRunner

from qpcr_assay_check.cli import app

from .conftest import CDC_N1_F as F
from .conftest import CDC_N1_P as P
from .conftest import CDC_N1_R as R
from .conftest import ROOT_EXAMPLE
from .test_assess import F_START, HUMAN, P_START, R_START, add_target_hits, offtarget_genome
from .world import WorldFake

runner = CliRunner()
HUMAN_ACC = "NC_000007.14"


@pytest.fixture
def env(tmp_path, monkeypatch):
    conf = tmp_path / "config.yaml"
    conf.write_text(f"ncbi:\n  cache_dir: {tmp_path / 'cache'}\n")
    monkeypatch.setenv("NCBI_EMAIL", "lab@example.org")
    monkeypatch.delenv("NCBI_API_KEY", raising=False)
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def install(world):
        fake = WorldFake(world)
        monkeypatch.setattr("qpcr_assay_check.ncbi.http.requests.Session", lambda: fake)
        return fake

    return type("E", (), {"conf": conf, "out": tmp_path / "out", "install": staticmethod(install)})


def world_with(f=(), r=(), p=(), hits="full"):
    w = offtarget_genome(
        f=f, r=r, p=p, acc=HUMAN_ACC, taxid=HUMAN, name="Homo sapiens",
        title="Homo sapiens chromosome 7, GRCh38 reference",
    )  # fmt: skip
    if hits == "full":
        w.hit(HUMAN, "forward", F, HUMAN_ACC, F_START, "+")
        w.hit(HUMAN, "reverse", R, HUMAN_ACC, R_START, "-")
        w.hit(HUMAN, "probe", P, HUMAN_ACC, P_START, "+")
    add_target_hits(w)
    return w


def invoke(env, *extra, **kw):
    return runner.invoke(
        app,
        ["run", str(ROOT_EXAMPLE), "--config", str(env.conf), "-o", str(env.out), *extra],
        **kw,
    )


def run_dir(env):
    (path,) = env.out.rglob("results.json")
    return path.parent


def test_an_off_target_product_in_the_background_fails_the_run_and_is_documented(env):
    env.install(world_with(f=[10], r=[5], p=[8]))
    r = invoke(env, "--yes")
    assert r.exit_code == 20, r.output
    assert "Verdict: FAIL" in r.output and "predicted off-target product" in r.output
    d = run_dir(env)
    data = json.loads((d / "results.json").read_text())
    spec = data["specificity"]
    assert spec["verdict"] == "FAIL" and spec["amplicons"][0]["classification"] == "likely_detected"
    assert spec["amplicons"][0]["organism"] == "Homo sapiens" and data["network_used"] is True
    assert data["search"]["searches"][0]["rid"]  # RIDs are part of the record

    rows = (d / "hits.tsv").read_text().splitlines()
    assert rows[0].startswith("tier\tquery\trole") and len(rows) == 4  # header + three sites
    assert any("\tcritical\t" in row for row in rows[1:])

    html = (d / "report.html").read_text()
    for needle in (
        "Predicted off-target products", "Closest off-target sites", "likely_detected",
        "Homo sapiens", "In silico analysis does not replace experimental validation",
        "sent the oligo sequences to NCBI", "Taxon restriction check",
    ):  # fmt: skip
        assert needle in html, needle
    assert 'class="aln"' in html and 'class="mm' in html  # alignment with highlighted mismatches
    # self-contained: no tag loads a remote script, stylesheet, image or font
    assert not re.search(r"<(script|link|img|iframe)\b[^>]*\b(src|href)=[\"']?(https?:)?//", html)

    wb = load_workbook(d / "results.xlsx")
    assert {"Off-target sites", "Predicted products", "Searches", "Findings"} <= set(wb.sheetnames)


def test_a_clean_assay_gives_a_passing_specificity_but_an_incomplete_overall_verdict(env):
    env.install(world_with(hits="none"))
    r = invoke(env, "--yes")
    assert r.exit_code == 30, r.output  # exclusivity/inclusivity/history are not available yet
    data = json.loads((run_dir(env) / "results.json").read_text())
    assert data["specificity"]["verdict"] == "PASS"
    states = {s["key"]: s["state"] for s in data["sections"]}
    assert states["specificity"] == states["amplicon_prediction"] == "evaluated"
    assert states["exclusivity"] == states["inclusivity"] == "not_implemented"
    assert "Not yet evaluated" in (run_dir(env) / "report.html").read_text()


def test_dry_run_sends_nothing(env):
    fake = env.install(world_with())
    r = invoke(env, "--dry-run")
    assert r.exit_code == 0 and "Dry run" in r.output
    assert fake.calls == [] and fake.efetch_calls == []


def test_declining_the_confirmation_sends_nothing(env):
    fake = env.install(world_with())
    r = invoke(env, input="n\n")
    assert r.exit_code == 64 and "Nothing was sent to NCBI" in r.output
    assert fake.calls == []


def test_a_second_run_reuses_the_cache_and_sends_no_new_searches(env):
    fake = env.install(world_with(f=[10, 16, 17], hits="partial"))
    w = fake.world
    w.hit(HUMAN, "forward", F, HUMAN_ACC, F_START, "+", trim3=5)
    first = invoke(env, "--yes")
    assert first.exit_code in (20, 30)
    puts, fetches = fake.n_put, len(fake.efetch_calls)
    assert puts == 2 and fetches == 1
    second = invoke(env, "--yes")
    assert second.exit_code == first.exit_code
    assert (
        fake.n_put == puts and len(fake.efetch_calls) == fetches
    )  # everything came from the cache


def test_the_email_never_appears_in_the_record(env):
    env.install(world_with(f=[10], r=[5], p=[8]))
    invoke(env, "--yes")
    for path in env.out.rglob("*"):
        if path.is_file() and path.suffix in {".json", ".tsv", ".html", ".log"}:
            text = path.read_text(errors="ignore")
            assert "lab@example.org" not in text and "lab%40example.org" not in text, path
